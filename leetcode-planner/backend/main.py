from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="LeetCode Planner", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


class PlanItem(BaseModel):
    day: int
    count: int
    topic: str
    difficulty: str


class CreatePlanRequest(BaseModel):
    days: int
    target_count: int
    level: str  # 入门/进阶/冲刺
    topics: List[str]


class CheckinRequest(BaseModel):
    day: int
    solved_count: int


from threading import Lock

plan_cache_lock = Lock()
checkin_cache_lock = Lock()

plan_cache: List[PlanItem] = []
checkin_cache: Dict[int, int] = {}


def _difficulty_for(day: int, total_days: int, level: str) -> str:
    """难度分布：入门 前70%简单/后30%中等；进阶 前70%中等/后30%困难；冲刺 全困难"""
    if level == "冲刺":
        return "困难"
    ratio = (day - 1) / max(total_days, 1)
    if level == "入门":
        return "简单" if ratio < 0.7 else "中等"
    return "中等" if ratio < 0.7 else "困难"


@app.post("/api/plan")
async def create_plan(req: CreatePlanRequest):
    global plan_cache, checkin_cache
    with plan_cache_lock, checkin_cache_lock:
        checkin_cache = {}  # 天团评审修复：新计划清空旧打卡，避免污染进度
        if req.days <= 0 or req.target_count <= 0:
            raise HTTPException(400, "天数和题数必须为正")
        topics = req.topics or ["数组", "链表"]
        daily = req.target_count // req.days
        remainder = req.target_count % req.days
        plan_cache = []
        for day in range(1, req.days + 1):
            count = daily + (1 if day <= remainder else 0)  # 余数摊到前几天
            plan_cache.append(PlanItem(
                day=day,
                count=count,
                topic=topics[(day - 1) % len(topics)],
                difficulty=_difficulty_for(day, req.days, req.level),
            ))
    return {"plan": [p.model_dump() for p in plan_cache]}


@app.post("/api/checkin")
async def checkin(req: CheckinRequest):
    with checkin_cache_lock:
        if req.day < 1 or req.day > len(plan_cache):
            raise HTTPException(400, "打卡天数超出计划范围")
        if req.solved_count < 0:
            raise HTTPException(400, "题数不能为负")
        if req.day in checkin_cache:
            return {"message": "已打卡", "day": req.day, "solved": checkin_cache[req.day]}
        checkin_cache[req.day] = req.solved_count
    return {"message": "打卡成功", "day": req.day, "solved": checkin_cache[req.day]}


@app.get("/api/progress")
async def get_progress():
    with plan_cache_lock, checkin_cache_lock:
        total_planned = sum(p.count for p in plan_cache)
        total_solved = sum(checkin_cache.values())
        by_topic: Dict[str, int] = {}
        for p in plan_cache:
            by_topic[p.topic] = by_topic.get(p.topic, 0) + checkin_cache.get(p.day, 0)
    return {
        "total_planned": total_planned,
        "total_solved": total_solved,
        "days_done": len(checkin_cache),
        "percent": round(total_solved / total_planned * 100, 1) if total_planned else 0,
        "by_topic": by_topic,
    }


@app.get("/api/health")
async def health():
    with plan_cache_lock:
        return {"status": "ok", "planned_days": len(plan_cache)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8692)