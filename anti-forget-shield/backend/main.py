from datetime import datetime, timedelta
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Anti-Forget Shield", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# 艾宾浩斯复习间隔：1/2/4/7/15 天
INTERVALS = [timedelta(days=1), timedelta(days=2), timedelta(days=4),
             timedelta(days=7), timedelta(days=15)]


class LearnRequest(BaseModel):
    content: str
    difficulty: int = 3


class Item(BaseModel):
    item_id: int
    content: str
    difficulty: int
    next_review_date: datetime
    review_count: int = 0
    status: str = "待复习"


items_db: List[Item] = []
_next_id = 1


@app.post("/api/learn")
async def learn(req: LearnRequest):
    """录入学习内容，按艾宾浩斯间隔生成复习计划"""
    global _next_id
    if not req.content.strip():
        raise HTTPException(400, "内容不能为空")
    # 天团评审修复：难度 >=4 复习间隔减半（难内容复习更勤）
    intervals = [timedelta(days=iv.days / 2) for iv in INTERVALS] if req.difficulty >= 4 else INTERVALS
    item = Item(
        item_id=_next_id,
        content=req.content,
        difficulty=req.difficulty,
        next_review_date=datetime.utcnow() + intervals[0],
    )
    _next_id += 1
    items_db.append(item)
    now = datetime.utcnow()
    plan = [(now + iv).strftime("%Y-%m-%d") for iv in intervals]
    return {"item_id": item.item_id, "plan": plan}


@app.post("/api/checkin")
async def checkin(req: dict):
    """打卡复习：推进到下一间隔，5 次后完成"""
    item_id = req.get("item_id")
    item = next((i for i in items_db if i.item_id == item_id), None)
    if not item:
        raise HTTPException(404, "未找到该学习内容")
    # 天团评审修复：未到复习时间不允许打卡
    if datetime.utcnow() < item.next_review_date:
        raise HTTPException(400, "未到复习时间")
    item.review_count += 1
    if item.review_count >= len(INTERVALS):
        item.status = "已完成"
    else:
        intervals = [timedelta(days=iv.days / 2) for iv in INTERVALS] if item.difficulty >= 4 else INTERVALS
        item.next_review_date = datetime.utcnow() + intervals[item.review_count]
    return {"message": "复习打卡成功", "review_count": item.review_count, "status": item.status}


@app.get("/api/items")
async def get_items():
    return [
        {
            "item_id": i.item_id,
            "content": i.content,
            "difficulty": i.difficulty,
            "next_review_date": i.next_review_date.strftime("%Y-%m-%d %H:%M"),
            "review_count": i.review_count,
            "status": i.status,
        }
        for i in items_db
    ]


@app.get("/api/risk")
async def get_risk():
    """遗忘风险预测：按逾期天数分级"""
    now = datetime.utcnow()
    out = []
    for i in items_db:
        if i.status == "已完成":
            continue
        overdue = (now - i.next_review_date).days
        overdue = max(0, overdue)  # 处理未来日期情况
        if overdue > 7:
            risk = "高"
        elif overdue > 2:
            risk = "中"
        elif overdue >= 0:
            risk = "低"
        else:
            risk = "未到期"
        out.append({"item_id": i.item_id, "content": i.content,
                    "overdue_days": overdue, "risk": risk})
    return out


@app.get("/api/health")
async def health():
    return {"status": "ok", "items": len(items_db)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8691)