"""
食材分类器 — CLIP + 分类头 / MobileNetV3 蒸馏版
"""
import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import torch, torch.nn as nn
from torchvision import transforms, models
from PIL import Image
from pathlib import Path

MODEL_DIR = Path(__file__).parent

class FoodClassifier:
    def __init__(self):
        self.model = None
        self.class_names = []
        self.model_type = ""
        self._clip_model = None  # lazy load

        # CLIP 预处理 (给 CLIP 模型用)
        self.clip_transform = None
        # 标准预处理 (给 MobileNetV3 用)
        self.std_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        self.load()

    def load(self):
        class_path = MODEL_DIR / "class_names.json"
        if not class_path.exists():
            print("[!] class_names.json 不存在")
            return
        with open(class_path) as f:
            self.class_names = json.load(f)

        # 优先尝试 CLIP 模型 (92.69%)
        clip_head = MODEL_DIR / "clip_classifier.pth"
        clip_weights = MODEL_DIR / "clip_vit_b32.pth"
        if clip_head.exists() and clip_weights.exists():
            try:
                self._load_clip(clip_head, clip_weights)
                print(f"[✓] CLIP 模型加载: {len(self.class_names)} 类")
                return
            except Exception as e:
                print(f"[!] CLIP 加载失败: {e}, 尝试 MobileNetV3...")

        # 其次尝试 MobileNetV3 蒸馏模型 (90.83%, 6MB)
        student_path = MODEL_DIR / "student_mobilenetv3.pth"
        if student_path.exists():
            try:
                self._load_mobilenet(student_path)
                print(f"[✓] MobileNetV3 蒸馏模型: {len(self.class_names)} 类 (6MB)")
                return
            except Exception as e:
                print(f"[!] MobileNetV3 加载失败: {e}")

        # 最后尝试旧模型
        old_path = MODEL_DIR / "food_model_best.pth"
        if old_path.exists():
            print(f"[!] 使用旧模型 (准确率低)")
            self.model = None
            return

        print("[!] 无可用模型")

    def _load_clip(self, head_path, weights_path):
        import clip
        os.environ["CUDA_VISIBLE_DEVICES"] = ""  # CPU
        self._clip_model, self.clip_transform = clip.load("ViT-B/32", device="cpu")
        self._clip_model.load_state_dict(torch.load(weights_path, map_location="cpu", weights_only=True))
        self._clip_model.eval()

        self.model = nn.Sequential(
            nn.Linear(512, 256), nn.ReLU(), nn.Dropout(0.3), nn.Linear(256, len(self.class_names)),
        )
        self.model.load_state_dict(torch.load(head_path, map_location="cpu", weights_only=True))
        self.model.eval()
        self.model_type = "clip"

    def _load_mobilenet(self, path):
        self.model = models.mobilenet_v3_small(weights=None)
        self.model.classifier[-1] = nn.Linear(self.model.classifier[-1].in_features, len(self.class_names))
        self.model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        self.model.eval()
        self.model_type = "mobilenet"

    def predict(self, image: Image.Image) -> dict:
        if self.model is None:
            return {"name": "模型未加载", "confidence": 0.0, "class_index": -1}

        if self.model_type == "clip":
            img = self.clip_transform(image).unsqueeze(0)
            with torch.no_grad():
                feat = self._clip_model.encode_image(img).float()
                outputs = self.model(feat)
        else:
            img = self.std_transform(image).unsqueeze(0)
            with torch.no_grad():
                outputs = self.model(img)

        probs = torch.nn.functional.softmax(outputs[0], dim=0)
        conf, idx = torch.max(probs, 0)
        return {"name": self.class_names[idx.item()], "confidence": round(conf.item(), 4), "class_index": idx.item()}

    def predict_topk(self, image: Image.Image, k: int = 3) -> list:
        if self.model is None: return []
        if self.model_type == "clip":
            img = self.clip_transform(image).unsqueeze(0)
            with torch.no_grad():
                feat = self._clip_model.encode_image(img).float()
                outputs = self.model(feat)
        else:
            img = self.std_transform(image).unsqueeze(0)
            with torch.no_grad():
                outputs = self.model(img)
        probs = torch.nn.functional.softmax(outputs[0], dim=0)
        vals, indices = torch.topk(probs, k)
        return [{"name": self.class_names[idx.item()], "confidence": round(vals[i].item(), 4)} for i, idx in enumerate(indices)]

classifier = FoodClassifier()
