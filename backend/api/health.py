"""
健康评分 + 家庭排行榜
GET /api/health-score — 今日营养健康评分（0-100）
GET /api/leaderboard   — 家庭成员健康积分排行

评分维度（依据《中国居民膳食营养素参考摄入量2023版》）：
- 热量达标度 (40分): 摄入占目标 80%-120% 满分
- 蛋白质充足度 (25分): ≥ 目标 70% 满分
- 脂肪控制 (15分): 供能比 ≤ 30% 满分
- 碳水供能比 (10分): 50%-65% 满分
- 食材多样性 (10分): 当日 ≥ 8 种食材满分
"""
from fastapi import APIRouter, Query
from datetime import date
from backend.database import get_daily_summary_by_member, get_members

router = APIRouter(prefix="/api", tags=["health"])

# 每日参考摄入（成人，2000kcal 基准）
REF = {
    "calories": 2000,
    "protein_g": 65,
    "fat_g": 66,       # 供能 ≤30%
    "carbs_g": 275,    # 供能 50-65%
}


def _score_component(value, ref, full_marks, low_ratio=0.7, high_ratio=1.25):
    """达标区间 [ref*low_ratio, ref*high_ratio] 得满分，线性衰减"""
    if value <= 0:
        return 0
    ratio = value / ref
    if low_ratio <= ratio <= high_ratio:
        return full_marks
    if ratio < low_ratio:
        return round(full_marks * ratio / low_ratio, 1)
    # 超量衰减
    over = ratio - high_ratio
    return max(round(full_marks * (1 - over / high_ratio), 1), full_marks * 0.3)


@router.get("/health-score")
async def health_score(member: str = Query("default", description="家庭成员名")):
    """计算某成员今日健康评分"""
    summary = get_daily_summary_by_member(date=date.today().isoformat(), member=member)
    if not summary or not summary.get("total_cal"):
        return {"success": True, "score": None, "member": member,
                "message": "今日暂无记录，快去识别食材吧"}

    cal = summary["total_cal"] or 0
    protein = summary["total_protein"] or 0
    fat = summary["total_fat"] or 0
    carbs = summary["total_carbs"] or 0

    # 各维度得分
    s_cal = _score_component(cal, REF["calories"], 40, low_ratio=0.8, high_ratio=1.2)
    s_protein = _score_component(protein, REF["protein_g"], 25, low_ratio=0.7, high_ratio=1.4)
    s_fat = _score_component(fat, REF["fat_g"], 15, low_ratio=0.0, high_ratio=1.0)
    s_carbs = _score_component(carbs, REF["carbs_g"], 10, low_ratio=0.6, high_ratio=1.0)

    # 多样性：统计不同食材数
    conn = None
    try:
        from backend.database import get_connection
        conn = get_connection()
        row = conn.execute(
            "SELECT COUNT(DISTINCT food_name) as cnt FROM food_logs "
            "WHERE date(created_at) = ? AND member = ?",
            (date.today().isoformat(), member)).fetchone()
        diversity = row["cnt"] if row else 0
    finally:
        if conn:
            conn.close()

    s_div = min(diversity * 1.25, 10)  # 8 种满分

    total = round(s_cal + s_protein + s_fat + s_carbs + s_div, 1)

    # 评级
    if total >= 85:
        level = "优秀"
    elif total >= 70:
        level = "良好"
    elif total >= 55:
        level = "一般"
    else:
        level = "待改善"

    return {
        "success": True,
        "member": member,
        "score": total,
        "level": level,
        "dimensions": {
            "calories": {"score": s_cal, "value": round(cal, 1), "target": REF["calories"], "full": 40},
            "protein": {"score": s_protein, "value": round(protein, 1), "target": REF["protein_g"], "full": 25},
            "fat": {"score": s_fat, "value": round(fat, 1), "target": REF["fat_g"], "full": 15},
            "carbs": {"score": s_carbs, "value": round(carbs, 1), "target": REF["carbs_g"], "full": 10},
            "diversity": {"score": round(s_div, 1), "value": diversity, "target": 8, "full": 10},
        },
        "message": f"{member} 今日饮食评级：{level}",
    }


@router.get("/leaderboard")
async def leaderboard(days: int = Query(7, description="统计天数")):
    """家庭成员健康积分排行榜（近 N 天平均评分）"""
    members = get_members()
    result = []
    for m in members:
        name = m["name"]
        conn = None
        try:
            from backend.database import get_connection
            conn = get_connection()
            rows = conn.execute("""
                SELECT date(created_at) as day,
                       SUM(calories) as cal, SUM(protein_g) as pro,
                       SUM(fat_g) as fat, SUM(carbs_g) as carbs
                FROM food_logs
                WHERE member = ? AND created_at >= datetime('now', ?)
                GROUP BY date(created_at)
            """, (name, f"-{days} days")).fetchall()
        finally:
            if conn:
                conn.close()

        if not rows:
            result.append({"member": name, "score": 0, "days": 0, "rank": 0})
            continue

        # 每天算一个简化评分，取平均
        scores = []
        for r in rows:
            cal = r["cal"] or 0
            pro = r["pro"] or 0
            fat = r["fat"] or 0
            carbs = r["carbs"] or 0
            s_cal = _score_component(cal, REF["calories"], 40, 0.8, 1.2)
            s_pro = _score_component(pro, REF["protein_g"], 25, 0.7, 1.4)
            s_fat = _score_component(fat, REF["fat_g"], 15, 0.0, 1.0)
            s_car = _score_component(carbs, REF["carbs_g"], 10, 0.6, 1.0)
            scores.append(s_cal + s_pro + s_fat + s_car)
        avg = round(sum(scores) / len(scores), 1)
        result.append({"member": name, "score": avg, "days": len(rows), "rank": 0})

    result.sort(key=lambda x: -x["score"])
    for i, item in enumerate(result):
        item["rank"] = i + 1

    return {"success": True, "days": days, "ranking": result}
