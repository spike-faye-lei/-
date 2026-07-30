"""
膳食指南 & 营养素推荐值 API
数据来源：中国居民膳食指南(2022)、中国食物成分表
"""
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api", tags=["guidelines"])

# 每日营养目标（基于膳食指南2022 + WHO/FAO推荐）
TARGETS = {
    "maintain": {"calories": 2000, "protein_g": 60, "fat_g": 55, "carbs_g": 300, "fiber_g": 25},
    "lose":    {"calories": 1500, "protein_g": 70, "fat_g": 40, "carbs_g": 200, "fiber_g": 30},
    "gain":    {"calories": 2500, "protein_g": 90, "fat_g": 70, "carbs_g": 375, "fiber_g": 30},
}

# 三餐热量分配: 早餐30% 午餐40% 晚餐30%
MEAL_RATIOS = {"breakfast": 0.30, "lunch": 0.40, "dinner": 0.30}

# 膳食宝塔每日推荐摄入量 (g/day)
DIETARY_PAGODA = {
    "主食": {"min": 250, "max": 400, "unit": "g"},
    "蔬菜": {"min": 300, "max": 500, "unit": "g"},
    "水果": {"min": 200, "max": 350, "unit": "g"},
    "肉类": {"min": 40,  "max": 75,  "unit": "g"},
    "蛋类": {"min": 40,  "max": 50,  "unit": "g"},
    "乳制品": {"min": 300, "max": 300, "unit": "g"},
    "豆制品": {"min": 25,  "max": 25,  "unit": "g"},
}

@router.get("/guidelines")
async def get_guidelines(goal: str = Query("maintain")):
    """返回基于健康目标的每日营养推荐值"""
    target = TARGETS.get(goal, TARGETS["maintain"])
    meals = {}
    for meal, ratio in MEAL_RATIOS.items():
        meals[meal] = {k: round(v * ratio, 1) for k, v in target.items()}
    return {
        "goal": goal,
        "daily": target,
        "meals": meals,
        "pagoda": DIETARY_PAGODA,
        "macro_ratio": {
            "protein_pct": round(target["protein_g"] * 4 / target["calories"] * 100, 1),
            "fat_pct": round(target["fat_g"] * 9 / target["calories"] * 100, 1),
            "carbs_pct": round(target["carbs_g"] * 4 / target["calories"] * 100, 1),
        },
        "source": "中国居民膳食指南2022 / WHO-FAO NRV"
    }
