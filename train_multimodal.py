"""
多模态融合 v2: 预计算 CLIP 特征，离线训练分类头（无需加载 CLIP）
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import torch, torch.nn as nn, torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path
from tqdm import tqdm

TRAIN_DIR = Path(__file__).parent / "data_train_final"
VAL_DIR = Path(__file__).parent / "data_val_final"
MODEL_DIR = Path(__file__).parent / "backend" / "models"
CLIP_PATH = MODEL_DIR / "clip_vit_b32.pth"
CACHE_DIR = Path(__file__).parent / "backend" / "cache"

BATCH_SIZE = 64
EPOCHS = 40
LR = 0.001
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
CLIP_DEVICE = "cpu"  # CLIP JIT 在 GPU 上 SIGSEGV, 强制 CPU
CACHE_DIR.mkdir(parents=True, exist_ok=True)

with open(MODEL_DIR / "class_names.json") as f:
    class_names = json.load(f)
NUM_CLASSES = len(class_names)

# 营养文本
NUTRITION_PROMPTS = {
    "apple": "A fresh red apple, fruit, sweet, 52 calories",
    "banana": "A yellow banana, fruit, sweet, 89 calories",
    "orange": "A fresh orange citrus fruit, 47 calories, vitamin C",
    "tomato": "A red tomato vegetable, 18 calories",
    "cucumber": "A green cucumber vegetable, 15 calories",
    "carrot": "An orange carrot vegetable, 41 calories",
    "potato": "A raw potato tuber, 77 calories, starch",
    "chicken_breast": "Raw chicken breast meat, 165 calories, high protein",
    "egg": "A raw chicken egg, 155 calories, protein 13g",
    "milk": "A glass of milk dairy, 66 calories, calcium",
    "tofu": "A block of tofu soybean curd, 76 calories",
    "broccoli": "Fresh green broccoli vegetable, 34 calories",
    "rice": "White rice grain staple food, 116 calories",
    "noodles": "Raw noodles pasta staple food, 138 calories",
    "bread": "A loaf of bread bakery staple, 266 calories",
}

# ===== Step 1: 预计算特征 (只做一次) =====
def precompute():
    from torchvision import datasets
    import clip, os
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    print("加载 CLIP 解码文本特征...")
    model, preprocess = clip.load("ViT-B/32", device=CLIP_DEVICE)
    model.load_state_dict(torch.load(CLIP_PATH, map_location=CLIP_DEVICE, weights_only=True))
    model = model.to(CLIP_DEVICE)
    model.eval()

    # 文本特征
    text_inputs = torch.cat([clip.tokenize(NUTRITION_PROMPTS[c]) for c in class_names]).to(CLIP_DEVICE)
    with torch.no_grad():
        txt_feat = model.encode_text(text_inputs).float()
    torch.save(txt_feat.cpu(), CACHE_DIR / "txt_features.pt")
    print(f"文本特征: {txt_feat.shape}")

    for split, dir_path in [("train", TRAIN_DIR), ("val", VAL_DIR)]:
        cache_path = CACHE_DIR / f"{split}_img_features.pt"
        label_path = CACHE_DIR / f"{split}_labels.pt"
        if cache_path.exists():
            print(f"  {split}: 已缓存, 跳过")
            continue

        dataset = datasets.ImageFolder(str(dir_path), transform=preprocess)
        loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
        all_feat, all_labels = [], []
        with torch.no_grad():
            for images, labels in tqdm(loader, desc=f"编码 {split}"):
                images = images.to(CLIP_DEVICE)
                feat = model.encode_image(images).float()
                all_feat.append(feat.cpu())
                all_labels.append(labels)
        all_feat = torch.cat(all_feat)
        all_labels = torch.cat(all_labels)
        torch.save(all_feat, cache_path)
        torch.save(all_labels, label_path)
        print(f"  {split}: {len(all_feat)} 样本, shape {all_feat.shape}")

    del model
    # CLIP 在 CPU, 清 GPU 缓存给后续训练用
    if torch.cuda.is_available(): torch.cuda.empty_cache()

# ===== Step 2: 训练分类头 =====
class MultiModalClassifier(nn.Module):
    def __init__(self, img_dim=512, txt_dim=512, hidden=256, n_classes=15):
        super().__init__()
        self.img_proj = nn.Sequential(nn.Linear(img_dim, hidden), nn.ReLU(), nn.Dropout(0.3))
        self.txt_proj = nn.Sequential(nn.Linear(txt_dim, hidden), nn.ReLU(), nn.Dropout(0.3))
        self.fusion = nn.Sequential(
            nn.Linear(hidden * 2, hidden), nn.ReLU(), nn.Dropout(0.3), nn.Linear(hidden, n_classes),
        )
    def forward(self, img_feat, txt_feat):
        return self.fusion(torch.cat([self.img_proj(img_feat), self.txt_proj(txt_feat)], dim=-1))

def train():
    txt_features = torch.load(CACHE_DIR / "txt_features.pt", weights_only=True).to(DEVICE)

    # 训练集
    train_feat = torch.load(CACHE_DIR / "train_img_features.pt", weights_only=True)
    train_labels = torch.load(CACHE_DIR / "train_labels.pt", weights_only=True)
    train_dataset = TensorDataset(train_feat, train_labels)
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)

    # 验证集
    val_feat = torch.load(CACHE_DIR / "val_img_features.pt", weights_only=True)
    val_labels = torch.load(CACHE_DIR / "val_labels.pt", weights_only=True)
    val_dataset = TensorDataset(val_feat, val_labels)
    # 预计算平均文本特征 (CPU, 避免 GPU OOM)
    txt_avg = txt_features.mean(0).cpu()
    val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)

    classifier = MultiModalClassifier(n_classes=NUM_CLASSES).to(DEVICE)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = optim.AdamW(classifier.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_acc = 0.0
    for epoch in range(1, EPOCHS + 1):
        classifier.train()
        running_loss, correct, total = 0.0, 0, 0
        pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{EPOCHS}")
        for img_batch, labels in pbar:
            img_batch, labels = img_batch.to(DEVICE), labels.to(DEVICE)
            txt_batch = txt_features[labels]
            optimizer.zero_grad()
            outputs = classifier(img_batch, txt_batch)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
            _, pred = outputs.max(1)
            total += labels.size(0)
            correct += pred.eq(labels).sum().item()
            pbar.set_postfix({"loss": f"{loss.item():.3f}", "acc": f"{100.*correct/total:.2f}%"})
        train_loss = running_loss / len(train_loader)
        train_acc = 100.0 * correct / total

        classifier.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for img_batch, labels in val_loader:
                img_batch, labels = img_batch.to(DEVICE), labels.to(DEVICE)
                txt_batch = txt_avg.unsqueeze(0).expand(img_batch.size(0), -1).to(DEVICE)
                outputs = classifier(img_batch, txt_batch)
                _, pred = outputs.max(1)
                val_total += labels.size(0)
                val_correct += pred.eq(labels).sum().item()
        val_acc = 100.0 * val_correct / val_total
        scheduler.step()

        print(f"Epoch {epoch:3d} | Train: {train_loss:.3f} {train_acc:.2f}% | Val: {val_acc:.2f}%")
        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(classifier.state_dict(), MODEL_DIR / "multimodal_classifier.pth")
            print(f"  [★] {val_acc:.2f}%")

    print(f"\n多模态融合完成: {best_acc:.2f}%")

if __name__ == "__main__":
    precompute()
    train()
