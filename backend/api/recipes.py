"""
菜谱接口 — 多食材组合 + 营养自动计算
"""
import json, os
from pathlib import Path
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api", tags=["recipes"])

DATA = Path(__file__).parent.parent / "data"
with open(DATA / "recipes.json", encoding="utf-8") as f:
    RECIPES = json.load(f)
with open(DATA / "nutrition.json", encoding="utf-8") as f:
    NUTRITION = json.load(f)


def calc_recipe(r: dict) -> dict:
    """计算菜谱总营养"""
    total = {"calories": 0, "protein": 0, "fat": 0, "carbs": 0, "fiber": 0}
    for ing in r["ingredients"]:
        food = NUTRITION.get(ing["food"])
        if not food:
            continue
        ratio = ing["grams"] / 100.0
        total["calories"] += food["calories"] * ratio
        total["protein"] += food["protein"] * ratio
        total["fat"] += food["fat"] * ratio
        total["carbs"] += food["carbs"] * ratio
        total["fiber"] += food["fiber"] * ratio
    return {k: round(v, 1) for k, v in total.items()}


@router.get("/recipes")
async def list_recipes(meal_type: str = Query(None)):
    """菜谱列表，可按餐类筛选"""
    result = []
    for key, r in RECIPES.items():
        if meal_type and r.get("meal_type") != meal_type:
            continue
        item = {
            "key": key, "name": r["name"], "name_en": r["name_en"],
            "meal_type": r["meal_type"], "cook_time": r["cook_time"],
            "difficulty": r["difficulty"],
            "ingredients": r["ingredients"],
            "nutrition": calc_recipe(r),
        }
        result.append(item)
    return {"recipes": result}


@router.get("/recipes/recommend")
async def recommend_recipes(goal: str = Query("maintain"), meal_type: str = Query(None)):
    """根据健康目标推荐菜谱，按总热量排序"""
    target_cal = {"maintain": 600, "lose": 450, "gain": 750}.get(meal_type or "lunch",
                {"maintain": 2000, "lose": 1500, "gain": 2500}.get(goal, 2000))

    result = []
    for key, r in RECIPES.items():
        if meal_type and r.get("meal_type") != meal_type:
            continue
        nutrition = calc_recipe(r)
        score = 100 - abs(nutrition["calories"] - target_cal) / target_cal * 100
        item = {
            "key": key, "name": r["name"], "name_en": r["name_en"],
            "meal_type": r["meal_type"], "cook_time": r["cook_time"],
            "difficulty": r["difficulty"],
            "ingredients": r["ingredients"],
            "nutrition": nutrition,
            "score": round(max(0, score), 1),
        }
        result.append(item)

    result.sort(key=lambda x: -x["score"])
    return {"recipes": result, "target_cal": target_cal, "goal": goal}


@router.get("/recipes/{key}")
async def recipe_detail(key: str):
    """菜谱详情"""
    r = RECIPES.get(key)
    if not r:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"未找到菜谱 '{key}'")
    return {
        "key": key, "name": r["name"], "name_en": r["name_en"],
        "meal_type": r["meal_type"], "cook_time": r["cook_time"],
        "difficulty": r["difficulty"],
        "ingredients": r["ingredients"],
        "nutrition": calc_recipe(r),
    }
