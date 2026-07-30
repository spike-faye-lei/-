"""
CLIP 食材分类训练 — 冻结 CLIP + 训练分类头
"""
import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import torch, torch.nn as nn, torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import transforms, datasets
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

TRAIN_DIR = Path(__file__).parent / "data_train_final"
VAL_DIR = Path(__file__).parent / "data_val_final"
MODEL_DIR = Path(__file__).parent / "backend" / "models"
CLIP_PATH = MODEL_DIR / "clip_vit_b32.pth"
IMG_SIZE = 224
BATCH_SIZE = 64
EPOCHS = 30
LR = 0.001
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"设备: {DEVICE}")

# 加载类别
with open(MODEL_DIR / "class_names.json") as f:
    class_names = json.load(f)
NUM_CLASSES = len(class_names)

# 加载 CLIP
import clip
model, preprocess = clip.load("ViT-B/32", device=DEVICE)
model.load_state_dict(torch.load(CLIP_PATH, map_location=DEVICE, weights_only=True))

# 冻结 CLIP
for p in model.parameters():
    p.requires_grad = False

# 简单分类头
classifier = nn.Sequential(
    nn.Linear(512, 256),
    nn.ReLU(),
    nn.Dropout(0.3),
    nn.Linear(256, NUM_CLASSES),
).to(DEVICE)

criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
optimizer = optim.AdamW(classifier.parameters(), lr=LR, weight_decay=1e-4)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

# 数据集（用 CLIP 的 preprocess）
train_dataset = datasets.ImageFolder(str(TRAIN_DIR), transform=preprocess)
val_dataset = datasets.ImageFolder(str(VAL_DIR), transform=preprocess)
train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
print(f"训练: {len(train_dataset)}, 验证: {len(val_dataset)}")

best_acc = 0.0
model.eval()  # CLIP 始终 eval

for epoch in range(1, EPOCHS + 1):
    # 训练分类头
    classifier.train()
    running_loss, correct, total = 0.0, 0, 0
    pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{EPOCHS}")
    for images, labels in pbar:
        images, labels = images.to(DEVICE), labels.to(DEVICE)
        with torch.no_grad():
            features = model.encode_image(images).float()
        optimizer.zero_grad()
        outputs = classifier(features)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()
        _, pred = outputs.max(1)
        total += labels.size(0)
        correct += pred.eq(labels).sum().item()
        pbar.set_postfix({"loss": f"{loss.item():.4f}", "acc": f"{100.*correct/total:.2f}%"})
    
    train_loss = running_loss / len(train_loader)
    train_acc = 100.0 * correct / total

    # 验证
    classifier.eval()
    val_loss, correct, total = 0.0, 0, 0
    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            features = model.encode_image(images).float()
            outputs = classifier(features)
            loss = criterion(outputs, labels)
            val_loss += loss.item()
            _, pred = outputs.max(1)
            total += labels.size(0)
            correct += pred.eq(labels).sum().item()
    val_loss /= len(val_loader)
    val_acc = 100.0 * correct / total
    scheduler.step()

    print(f"Epoch {epoch:3d} | Train: {train_loss:.4f} {train_acc:.2f}% | Val: {val_loss:.4f} {val_acc:.2f}%")

    if val_acc > best_acc:
        best_acc = val_acc
        torch.save(classifier.state_dict(), MODEL_DIR / "clip_classifier.pth")
        print(f"  [★] 最佳: {val_acc:.2f}%")

print(f"\n最佳验证准确率: {best_acc:.2f}%")
# 保存完整配置
torch.save({'classifier': classifier.state_dict(), 'classes': class_names}, MODEL_DIR / "clip_model.pth")
