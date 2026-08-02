"""
导出蒸馏模型为 ONNX（手机端部署用）
用法: python export_onnx.py
输出: backend/models/student_mobilenetv3.onnx (~6MB)
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pathlib import Path
import torch
import torch.nn as nn
from torchvision import transforms

MODEL_DIR = Path(__file__).parent / "backend" / "models"
CLASS_NAMES = ["apple", "banana", "orange", "tomato", "cucumber", "carrot",
               "potato", "chicken_breast", "egg", "milk", "tofu", "broccoli",
               "rice", "noodles", "bread"]

# 与 train_distill.py 中结构一致（直接 mobilenet_v3_small + 替换 classifier[-1]）
def create_student(num_classes=15):
    from torchvision.models import mobilenet_v3_small
    model = mobilenet_v3_small(weights=None)
    model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, num_classes)
    return model


def main():
    model = create_student(num_classes=len(CLASS_NAMES))
    ckpt = torch.load(MODEL_DIR / "student_mobilenetv3.pth",
                      map_location="cpu", weights_only=True)
    if isinstance(ckpt, dict) and "state_dict" in ckpt:
        state = ckpt["state_dict"]
    else:
        state = ckpt
    model.load_state_dict(state)
    model.eval()

    # 导出 ONNX（输入 3x224x224，与训练预处理一致）
    dummy = torch.randn(1, 3, 224, 224)
    onnx_path = MODEL_DIR / "student_mobilenetv3.onnx"
    torch.onnx.export(
        model, dummy, str(onnx_path),
        input_names=["input"], output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=11,
    )
    size_mb = onnx_path.stat().st_size / 1e6
    print(f"ONNX 导出成功: {onnx_path} ({size_mb:.1f}MB)")

    # 验证：ONNX 推理结果与 PyTorch 一致
    import onnxruntime as ort
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    with torch.no_grad():
        pt_out = model(dummy).numpy()
    onnx_out = sess.run(None, {"input": dummy.numpy()})[0]
    diff = float(abs(pt_out - onnx_out).max())
    print(f"PyTorch vs ONNX 最大误差: {diff:.6f}")
    assert diff < 1e-4, "ONNX 导出结果不一致!"
    print("验证通过: ONNX 与 PyTorch 输出一致")

    # 保存类别名
    import json
    (MODEL_DIR / "student_classes.json").write_text(
        json.dumps({"classes": CLASS_NAMES}, ensure_ascii=False), encoding="utf-8")
    print("类别映射已保存: student_classes.json")


if __name__ == "__main__":
    main()
