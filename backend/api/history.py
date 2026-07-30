"""
饮食记录接口
"""
from fastapi import APIRouter, Query, HTTPException
from backend.database import add_food_log, get_history, get_daily_summary
from datetime import date

router = APIRouter(prefix="/api", tags=["history"])

@router.post("/log")
async def log_food(
    food_name: str = Query(...),
    food_name_cn: str = Query(""),
    weight_g: float = Query(...),
    calories: float = Query(0),
    protein_g: float = Query(0),
    fat_g: float = Query(0),
    carbs_g: float = Query(0),
    confidence: float = Query(0),
    member: str = Query("default"),
):
    """记录一次饮食"""
    log_id = add_food_log(
        food_name, food_name_cn, weight_g, calories,
        protein_g, fat_g, carbs_g, confidence, member=member,
    )
    return {"success": True, "log_id": log_id}

@router.get("/history")
async def history(
    days: int = Query(7, description="查询最近几天的记录"),
    member: str = Query(None, description="按家庭成员筛选"),
    limit: int = Query(50),
):
    """获取饮食记录"""
    records = get_history(days=days, member=member, limit=limit)
    return {"records": records, "count": len(records)}

@router.get("/summary")
async def summary(today: bool = Query(False)):
    """获取每日营养汇总"""
    if today:
        d = date.today().isoformat()
        result = get_daily_summary(d)
        return {"date": d, **result}
    return get_daily_summary()
