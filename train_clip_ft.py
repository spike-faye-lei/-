"""CLIP 微调 — 5 轮快速验证"""
import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import torch, torch.nn as nn, torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets
from pathlib import Path
from tqdm import tqdm

TRAIN_DIR = Path(__file__).parent / "data_train_new"
VAL_DIR = Path(__file__).parent / "data_val_new"
MODEL_DIR = Path(__file__).parent / "backend" / "models"
CLIP_PATH = MODEL_DIR / "clip_vit_b32.pth"
BATCH_SIZE = 64
EPOCHS = 5
LR = 0.0001
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"设备: {DEVICE}")

with open(MODEL_DIR / "class_names.json") as f:
    class_names = json.load(f)
NUM_CLASSES = len(class_names)

import clip
model, preprocess = clip.load("ViT-B/32", device=DEVICE)
model.load_state_dict(torch.load(CLIP_PATH, map_location=DEVICE, weights_only=True))

# 冻结前面，只解冻最后 2 个 transformer block
for name, p in model.named_parameters():
    p.requires_grad = False
# 解冻最后 2 层
for name, p in model.visual.transformer.resblocks[-2:].named_parameters():
    p.requires_grad = True
unfrozen = sum(1 for p in model.parameters() if p.requires_grad)
print(f"解冻参数: {unfrozen}")

classifier = nn.Sequential(
    nn.Linear(512, 256), nn.ReLU(), nn.Dropout(0.3), nn.Linear(256, NUM_CLASSES),
).to(DEVICE)

criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
optimizer = optim.AdamW([
    {'params': classifier.parameters(), 'lr': LR * 10},
    {'params': [p for p in model.parameters() if p.requires_grad], 'lr': LR},
], weight_decay=1e-4)

train_dataset = datasets.ImageFolder(str(TRAIN_DIR), transform=preprocess)
val_dataset = datasets.ImageFolder(str(VAL_DIR), transform=preprocess)
train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
print(f"训练: {len(train_dataset)}, 验证: {len(val_dataset)}")

best_acc = 0.0
for epoch in range(1, EPOCHS + 1):
    model.train(); classifier.train()
    running_loss, correct, total = 0.0, 0, 0
    pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{EPOCHS}")
    for images, labels in pbar:
        images, labels = images.to(DEVICE), labels.to(DEVICE)
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

    model.eval(); classifier.eval()
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

    print(f"Epoch {epoch:3d} | Train: {train_loss:.4f} {train_acc:.2f}% | Val: {val_loss:.4f} {val_acc:.2f}%")
    if val_acc > best_acc:
        best_acc = val_acc
        torch.save({'model': model.state_dict(), 'classifier': classifier.state_dict()}, MODEL_DIR / "clip_finetuned.pth")
        print(f"  [★] {val_acc:.2f}%")

print(f"\n最佳验证: {best_acc:.2f}%")
