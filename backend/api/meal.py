"""
整餐多食材联合分析
POST /api/recognize/meal — 接收一张餐桌图片，切分为 3x3 网格，
对每个格子独立识别食材，汇总整餐营养构成。
"""
import io
import json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image
from backend.models.food_classifier import classifier

router = APIRouter(prefix="/api", tags=["meal"])

GRID = 3  # 3x3 网格

# 营养数据库（与 nutrition.py 共用）
DATA_DIR = Path(__file__).parent.parent / "data"
with open(DATA_DIR / "nutrition.json", encoding="utf-8") as f:
    NUTRITION_DB = json.load(f)

NAME_TO_KEY = {}
for key, info in NUTRITION_DB.items():
    NAME_TO_KEY[info["name"]] = key
    NAME_TO_KEY[key] = key


def get_nutrition(name: str):
    """按中文名或英文 key 查营养"""
    key = name.lower().replace(" ", "_")
    food_key = NAME_TO_KEY.get(name) or NAME_TO_KEY.get(key)
    if not food_key:
        return None
    return NUTRITION_DB.get(food_key)


def analyze_grid(image: Image.Image, x: int, y: int, w: int, h: int):
    """识别网格中的食材"""
    crop = image.crop((x, y, x + w, y + h))
    result = classifier.predict(crop)
    return result


@router.post("/recognize/meal")
async def recognize_meal(file: UploadFile = File(...)):
    """整餐分析：切 3x3 网格逐格识别，汇总营养"""
    if classifier.model is None:
        raise HTTPException(status_code=503, detail="模型未加载")

    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="无法解析图片")

    # 避免识别超大图
    image.thumbnail((900, 900))

    w, h = image.size
    gw, gh = w // GRID, h // GRID

    items = []
    seen = {}  # 食材 -> 累计置信度

    for gy in range(GRID):
        for gx in range(GRID):
            x, y = gx * gw, gy * gh
            try:
                result = analyze_grid(image, x, y, gw, gh)
                name = result["name"]
                conf = result["confidence"]
                if name in seen:
                    seen[name]["confidence"] += conf
                    seen[name]["count"] += 1
                else:
                    seen[name] = {"name": name, "confidence": conf, "count": 1}
            except Exception:
                continue

    # 过滤低置信度 + 排序
    items = [
        {"name": v["name"], "confidence": round(min(v["confidence"] / v["count"] + 0.1, 0.99), 4),
         "cells": v["count"]}
        for v in seen.values() if v["confidence"] / v["count"] >= 0.3
    ]
    items.sort(key=lambda x: -x["cells"])

    if not items:
        return {"success": True, "foods": [], "summary": None,
                "message": "未识别到明显食材，请靠近一点拍摄"}

    # 整餐营养汇总（假设每格 100g 估算）
    total = {"calories": 0.0, "protein_g": 0.0, "fat_g": 0.0, "carbs_g": 0.0}
    detail = []
    for it in items[:6]:
        nut = get_nutrition(it["name"])
        if nut:
            factor = min(it["cells"] * 0.8, 3.0)  # 每格约 80g，最多 3 份
            total["calories"] += nut.get("calories", 0) * factor
            total["protein_g"] += nut.get("protein_g", 0) * factor
            total["fat_g"] += nut.get("fat_g", 0) * factor
            total["carbs_g"] += nut.get("carbs_g", 0) * factor
            detail.append({**it, "nutrition": nut})
        else:
            detail.append(it)

    return {
        "success": True,
        "foods": items,
        "detail": detail,
        "summary": {k: round(v, 1) for k, v in total.items()},
        "message": f"识别到 {len(items)} 种食材",
    }
