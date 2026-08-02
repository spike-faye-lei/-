"""
模型权重下载脚本 — 一键获取训练好的模型
用法: python download_models.py [--all]

默认只下载核心推理所需:
  1. clip_vit_b32.pth     (CLIP ViT-B/32, 605MB) — 最高精度 92.69%
可选 --all 额外下载:
  2. student_mobilenetv3.pth (6MB) — 训练蒸馏得到, 也可本地运行 train_distill.py

手机端 ONNX 模型 (student_mobilenetv3.onnx, 6MB) 不提供下载,
由本地生成: python export_onnx.py（需先有 student_mobilenetv3.pth）
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
import urllib.request
import zipfile
from pathlib import Path

MODEL_DIR = Path(__file__).parent / "backend" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# 模型下载源（GitHub Releases 由项目维护者上传）
# 若未发布 Release，改为使用官方 CLIP 仓库下载:
#   https://openaipublic.azureedge.net/clip/models/40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af/ViT-B-32.pt
OPENAI_CLIP_URL = "https://openaipublic.azureedge.net/clip/models/40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af/ViT-B-32.pt"

CHUNK = 1024 * 256


def download(url: str, dest: Path, label: str):
    if dest.exists() and dest.stat().st_size > 100_000_000:
        print(f"[跳过] {label} 已存在 ({dest.stat().st_size/1e6:.0f}MB)")
        return
    print(f"[下载] {label} → {dest.name} ...")
    tmp = dest.with_suffix(".part")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as f:
        total = int(resp.headers.get("Content-Length", 0))
        done = 0
        while True:
            chunk = resp.read(CHUNK)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            pct = done * 100 // total if total else 0
            print(f"\r  {pct:3d}% ({done/1e6:.0f}/{total/1e6:.0f}MB)", end="", flush=True)
    print()
    tmp.rename(dest)
    print(f"[完成] {label}")


def main():
    all_models = "--all" in sys.argv

    # 1. CLIP 权重（OpenAI 官方）
    clip_pt = MODEL_DIR / "clip_vit_b32.pth"
    if not clip_pt.exists():
        download(OPENAI_CLIP_URL, clip_pt, "CLIP ViT-B/32 (605MB)")
    else:
        print(f"[跳过] CLIP 已存在")

    # 2. 分类头（很小, 训练后才有; 若无则提示训练）
    head = MODEL_DIR / "clip_classifier.pth"
    if not head.exists():
        print("[提示] clip_classifier.pth 不存在 — 请运行 `python train_clip.py` 训练分类头 (约10分钟)")
        print("       或从项目 Release 下载预训练权重")

    # 3. 蒸馏模型（可选）
    if all_models:
        student = MODEL_DIR / "student_mobilenetv3.pth"
        if not student.exists():
            print("[提示] student_mobilenetv3.pth 不存在 — 运行 `python train_distill.py` (需先有 CLIP 教师模型)")

    print("\n完成! 模型目录: " + str(MODEL_DIR))
    print("启动服务: python -m backend.app")


if __name__ == "__main__":
    main()
