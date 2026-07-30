"""
营养查询接口
GET /nutrition?name=xxx&weight=xxx
"""
import json
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException

router = APIRouter(prefix="/api", tags=["nutrition"])

DATA_DIR = Path(__file__).parent.parent / "data"
with open(DATA_DIR / "nutrition.json", encoding="utf-8") as f:
    NUTRITION_DB = json.load(f)

NAME_TO_KEY = {}
for key, info in NUTRITION_DB.items():
    NAME_TO_KEY[info["name"]] = key
    NAME_TO_KEY[key] = key

@router.get("/nutrition")
async def get_nutrition(
    name: str = Query(..., description="食材名称 (中文或英文key)"),
    weight: float = Query(100, description="重量(克), 默认100g"),
):
    """根据食材名称和重量查询营养信息"""
    key = name.lower().replace(" ", "_")

    food_key = NAME_TO_KEY.get(name)
    if not food_key:
        food_key = NAME_TO_KEY.get(key)
    if not food_key:
        food_key = name
    if food_key not in NUTRITION_DB:
        all_names = [v["name"] for v in NUTRITION_DB.values()]
        raise HTTPException(status_code=404, detail=f"未找到食材 '{name}', 可选: {all_names}")

    info = NUTRITION_DB[food_key]
    ratio = weight / 100.0

    return {
        "name": info["name"],
        "name_en": info["name_en"],
        "weight_g": weight,
        "calories": round(info["calories"] * ratio, 1),
        "protein_g": round(info["protein"] * ratio, 1),
        "fat_g": round(info["fat"] * ratio, 1),
        "carbs_g": round(info["carbs"] * ratio, 1),
        "fiber_g": round(info["fiber"] * ratio, 1),
        "category": info["category"],
    }

@router.get("/nutrition/list")
async def list_all_foods():
    """返回所有支持的食材列表"""
    return {
        "foods": [
            {"key": k, "name_cn": v["name"], "name_en": v["name_en"], "category": v["category"],
             "calories_per_100g": v["calories"], "serving_g": v.get("serving_g", 100)}
            for k, v in NUTRITION_DB.items()
        ],
        "count": len(NUTRITION_DB),
    }
