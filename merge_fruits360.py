"""融合 Fruits 360 → 训练集，每类取 500 张保持平衡"""
from pathlib import Path
import shutil, random

FRUITS_DIR = Path.home() / ".cache/kagglehub/datasets/moltean/fruits/versions/100/fruits-360_100x100/fruits-360/Training"
TRAIN_DIR = Path("D:/SmartKitchen/data_train_new")
MAX_PER_CLASS = 500
SEED = 42

# Fruits 360 → 我们的类名映射
CLASS_MAP = {
    "apple": "Apple",
    "banana": "Banana",
    "carrot": "Carrot",
    "cucumber": "Cucumber",
    "orange": "Orange",
    "potato": "Potato",
    "tomato": "Tomato",
}

random.seed(SEED)
total_merged = 0

for our_name, fruits_name in CLASS_MAP.items():
    # 找 Fruits 360 中匹配的目录
    matching = sorted([d for d in FRUITS_DIR.iterdir()
                       if d.is_dir() and d.name.lower().startswith(fruits_name.lower())])
    if not matching:
        print(f"  {our_name}: 未找到匹配目录")
        continue

    # 收集所有图片
    all_images = []
    for d in matching:
        all_images.extend(list(d.glob("*.jpg")) + list(d.glob("*.png")))
    
    print(f"  {our_name}: 找到 {len(all_images)} 张 ({len(matching)} 个子类)")

    # 随机选取
    selected = random.sample(all_images, min(MAX_PER_CLASS, len(all_images)))
    
    # 复制到训练集
    dst_dir = TRAIN_DIR / our_name
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    existing = len(list(dst_dir.glob("*.jpg"))) + len(list(dst_dir.glob("*.png")))
    for img in selected:
        new_name = f"fruits360_{img.parent.name}_{img.name}"
        shutil.copy(img, dst_dir / new_name)
    
    new_total = len(list(dst_dir.glob("*.jpg"))) + len(list(dst_dir.glob("*.png")))
    added = new_total - existing
    total_merged += added
    print(f"    → 加入 {added} 张, 总计 {new_total} 张")

print(f"\n总计融合: {total_merged} 张")
print(f"\n全部类别:")
for d in sorted(TRAIN_DIR.iterdir()):
    if d.is_dir():
        n = len(list(d.glob("*.jpg"))) + len(list(d.glob("*.png")))
        print(f"  {d.name}: {n} 张")
