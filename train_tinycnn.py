"""
训练 TinyCNN 粗分类模型 — 通晓开发板端侧用（256KB RAM）
4 大类: 水果 / 蔬菜 / 蛋白 / 主食
输入 32x32, INT8 量化后 <50KB, 激活 <50KB

用法: python train_tinycnn.py
输出:
  backend/models/tinycnn_int8.pt   — PyTorch INT8 模型
  backend/models/tinycnn_weights.h — C 头文件（开发板直接嵌入编译）
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import json
import struct
from pathlib import Path
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image

DATA_DIR = Path(__file__).parent  # 数据集在项目根目录
MODEL_DIR = Path(__file__).parent / "backend" / "models"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 15 类 → 4 大类映射
SUPER_CLASSES = ["fruit", "vegetable", "protein", "staple"]
CLASS_MAP = {
    "apple": 0, "banana": 0, "orange": 0, "tomato": 0,
    "cucumber": 1, "carrot": 1, "broccoli": 1, "potato": 1,
    "chicken_breast": 2, "egg": 2, "milk": 2, "tofu": 2,
    "rice": 3, "noodles": 3, "bread": 3,
}
SUPER_NAMES_CN = ["水果", "蔬菜", "蛋白质", "主食"]


class TinyCNN(nn.Module):
    """极简 CNN: 3x Conv + GAP + FC, ~6K 参数 (INT8 < 6KB)"""
    def __init__(self, num_classes=4):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 8, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),   # 32→16
            nn.Conv2d(8, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),  # 16→8
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2), # 8→4
        )
        self.head = nn.Linear(32, num_classes)

    def forward(self, x):
        x = self.features(x)
        x = x.mean(dim=(2, 3))  # GAP
        return self.head(x)


class FoodDataset(Dataset):
    def __init__(self, root: Path, transform):
        self.samples = []
        self.transform = transform
        for subdir in sorted(root.iterdir()):
            if not subdir.is_dir():
                continue
            super_cls = CLASS_MAP.get(subdir.name)
            if super_cls is None:
                continue
            for img_path in subdir.glob("*.jpg"):
                self.samples.append((str(img_path), super_cls))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB").resize((32, 32))
        return self.transform(img), label


def train():
    print(f"设备: {DEVICE}")
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize([0.5] * 3, [0.5] * 3),
    ])

    train_ds = FoodDataset(DATA_DIR / "data_train_final", transform)
    val_ds = FoodDataset(DATA_DIR / "data_val_final", transform)
    print(f"训练集: {len(train_ds)} 张, 验证集: {len(val_ds)} 张")

    train_loader = DataLoader(train_ds, batch_size=64, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=128, shuffle=False, num_workers=0)

    model = TinyCNN().to(DEVICE)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    best_acc = 0
    for epoch in range(20):
        model.train()
        total, correct, loss_sum = 0, 0, 0
        for x, y in train_loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            optimizer.step()
            loss_sum += loss.item() * len(x)
            total += len(x)
            correct += (out.argmax(1) == y).sum().item()

        # 验证
        model.eval()
        v_correct, v_total = 0, 0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(DEVICE), y.to(DEVICE)
                v_correct += (model(x).argmax(1) == y).sum().item()
                v_total += len(x)
        acc = v_correct / v_total
        print(f"Epoch {epoch+1:2d} | train {(correct/total*100):.1f}% | val {acc*100:.1f}%")
        if acc > best_acc:
            best_acc = acc
            torch.save(model.state_dict(), MODEL_DIR / "tinycnn_best.pt")

    print(f"\n最佳验证准确率: {best_acc*100:.1f}%")
    export_quantized(model)


def export_quantized(model):
    """INT8 量化 + 导出 C 头文件"""
    model.eval()
    # 伪量化（per-tensor, 简化 MCU 部署）
    state = model.state_dict()
    scales = {}
    for name, tensor in state.items():
        scale = float(tensor.abs().max()) / 127.0
        scales[name] = scale
        q = torch.clamp(torch.round(tensor / scale), -128, 127).to(torch.int8)
        state[name] = q

    torch.save({"state": state, "scales": scales}, MODEL_DIR / "tinycnn_int8.pt")
    size = sum(v.numel() for v in state.values())
    print(f"INT8 模型: {size} 参数 ≈ {size/1024:.1f}KB (输入 32x32x3)")

    # 导出 C 头文件（浮点权重 + 量化版注释）
    h_path = MODEL_DIR / "tinycnn_weights.h"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write("/* TinyCNN INT8 weights for TX-SMART-R (OpenHarmony Lite) */\n")
        f.write("/* 4 classes: fruit/vegetable/protein/staple */\n")
        f.write("#ifndef TINYCNN_WEIGHTS_H\n#define TINYCNN_WEIGHTS_H\n\n")
        for name, tensor in state.items():
            arr = tensor.flatten().tolist()
            f.write(f"static const signed char W_{name.replace('.', '_')}[] = {{\n")
            for i in range(0, len(arr), 24):
                f.write("  " + ", ".join(str(int(v)) for v in arr[i:i+24]) + ",\n")
            f.write("};\n")
            f.write(f"static const float S_{name.replace('.', '_')} = {scales[name]:.8f}f;\n\n")
        f.write("#endif\n")
    print(f"C 头文件: {h_path} ({h_path.stat().st_size/1024:.1f}KB)")


if __name__ == "__main__":
    train()
