"""
知识蒸馏 v2: 预计算 Teacher logits → 离线训练 MobileNetV3 Student
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import torch, torch.nn as nn, torch.optim as optim, torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset, Dataset
from torchvision import transforms, datasets, models
from pathlib import Path
from tqdm import tqdm
from PIL import Image

TRAIN_DIR = Path(__file__).parent / "data_train_final"
VAL_DIR = Path(__file__).parent / "data_val_final"
MODEL_DIR = Path(__file__).parent / "backend" / "models"
CLIP_PATH = MODEL_DIR / "clip_vit_b32.pth"
CLIP_HEAD = MODEL_DIR / "clip_classifier.pth"
CACHE_DIR = Path(__file__).parent / "backend" / "cache"

BATCH_SIZE = 16  # GPU OOM, smaller batches
EPOCHS = 30
LR = 0.001
T = 4.0
ALPHA = 0.7
IMG_SIZE = 224
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
CLIP_DEVICE = "cpu"  # CLIP JIT SIGSEGV on GPU
CACHE_DIR.mkdir(parents=True, exist_ok=True)

with open(MODEL_DIR / "class_names.json") as f:
    class_names = json.load(f)
NUM_CLASSES = len(class_names)

# ===== Step 1: 预计算 Teacher soft logits =====
def precompute_teacher():
    import clip
    print("加载 Teacher (CLIP) 计算软目标...")
    teacher, preprocess = clip.load("ViT-B/32", device=CLIP_DEVICE)
    teacher.load_state_dict(torch.load(CLIP_PATH, map_location=CLIP_DEVICE, weights_only=True))
    teacher_head = nn.Sequential(
        nn.Linear(512, 256), nn.ReLU(), nn.Dropout(0.3), nn.Linear(256, NUM_CLASSES),
    ).to(CLIP_DEVICE)
    teacher_head.load_state_dict(torch.load(CLIP_HEAD, map_location=CLIP_DEVICE, weights_only=True))
    teacher.eval()
    teacher_head.eval()

    for split, dir_path in [("train", TRAIN_DIR), ("val", VAL_DIR)]:
        cache_path = CACHE_DIR / f"{split}_teacher_logits.pt"
        if cache_path.exists():
            print(f"  {split}: 已缓存, 跳过")
            continue

        dataset = datasets.ImageFolder(str(dir_path), transform=preprocess)
        loader = DataLoader(dataset, batch_size=32, shuffle=False, num_workers=0)
        all_logits = []
        with torch.no_grad():
            for images, _ in tqdm(loader, desc=f"Teacher {split}"):
                images = images.to(CLIP_DEVICE)
                feat = teacher.encode_image(images).float()
                logits = teacher_head(feat)
                all_logits.append(logits.cpu())
        torch.save(torch.cat(all_logits), cache_path)
        print(f"  {split}: {len(torch.cat(all_logits))} 条")

    del teacher, teacher_head
    torch.cuda.empty_cache() if torch.cuda.is_available() else None

# ===== Step 2: 蒸馏训练 =====
class ImageDataset(Dataset):
    """加载原始图片 + 缓存的 teacher logits"""
    def __init__(self, dir_path, logits_path, img_size=224):
        self.dataset = datasets.ImageFolder(str(dir_path), transform=transforms.Compose([
            transforms.Resize((img_size, img_size)),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
        ]))
        self.logits = torch.load(logits_path, weights_only=True)

    def __len__(self): return len(self.dataset)
    def __getitem__(self, idx):
        img, label = self.dataset[idx]
        return img, label, self.logits[idx]

def train():
    print(f"\n设备: {DEVICE}, 温度: {T}, α: {ALPHA}")

    # Student
    student = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    student.classifier[-1] = nn.Linear(student.classifier[-1].in_features, NUM_CLASSES)
    student = student.to(DEVICE)
    n_params = sum(p.numel() for p in student.parameters()) / 1e6
    print(f"Student: MobileNetV3-Small ({n_params:.1f}M params)")

    train_dataset = ImageDataset(TRAIN_DIR, CACHE_DIR / "train_teacher_logits.pt")
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)

    # 验证集不放 teacher logits（只用硬标签评估）
    val_dataset = datasets.ImageFolder(str(VAL_DIR), transform=transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
    ]))
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    optimizer = optim.AdamW(student.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_acc = 0.0
    for epoch in range(1, EPOCHS + 1):
        student.train()
        running_loss, correct, total = 0.0, 0, 0
        pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{EPOCHS}")
        for images, labels, t_logits in pbar:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            t_logits = t_logits.to(DEVICE)
            soft_targets = F.softmax(t_logits / T, dim=1)

            s_logits = student(images)
            s_soft = F.log_softmax(s_logits / T, dim=1)

            distill_loss = F.kl_div(s_soft, soft_targets, reduction='batchmean') * (T * T)
            hard_loss = F.cross_entropy(s_logits, labels, label_smoothing=0.1)
            loss = ALPHA * distill_loss + (1 - ALPHA) * hard_loss

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
            _, pred = s_logits.max(1)
            total += labels.size(0)
            correct += pred.eq(labels).sum().item()
            pbar.set_postfix({"loss": f"{loss.item():.3f}", "acc": f"{100.*correct/total:.1f}%"})

        train_loss = running_loss / len(train_loader)
        train_acc = 100.0 * correct / total

        student.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(DEVICE), labels.to(DEVICE)
                _, pred = student(images).max(1)
                val_total += labels.size(0)
                val_correct += pred.eq(labels).sum().item()
        val_acc = 100.0 * val_correct / val_total
        scheduler.step()

        print(f"Epoch {epoch:3d} | Train: {train_loss:.3f} {train_acc:.2f}% | Val: {val_acc:.2f}%")
        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(student.state_dict(), MODEL_DIR / "student_mobilenetv3.pth")
            print(f"  [★] {val_acc:.2f}%")

    print(f"\n蒸馏完成: {best_acc:.2f}% (Teacher CLIP: 92.69%)")

if __name__ == "__main__":
    precompute_teacher()
    train()
