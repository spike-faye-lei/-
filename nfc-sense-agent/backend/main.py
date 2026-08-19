"""NFC 智能感知 Agent — FastAPI 后端
流程: NFC 刷卡事件 → 模式分析（连续加班/异常频次）→ Agent 推理 → 政策检索 → 提醒
创新点: 从 NFC 交互元数据（时间/频次/设备）提取隐含语义，驱动 RAG + Agent 响应
"""
import datetime
import os
from typing import List

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE", "https://api.deepseek.com/anthropic/v1/messages")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro")

app = FastAPI(title="NFC Sense Agent", version="0.1.0")
allowed_origins = ["https://example.com"]  # 替换为实际允许的域名列表
app.add_middleware(
    CORSMiddleware, allow_origins=allowed_origins, allow_methods=["*"], allow_headers=["*"]
)

# 内存事件存储
events: List[dict] = []

# 内置政策库（演示用简单关键词 RAG）
POLICIES = {
    "加班": "公司政策：连续加班超过 3 天建议安排调休，长时间加班请关注身体健康。",
    "出勤": "公司政策：工作日 9:00-18:00 为正常出勤时段，请按时打卡。",
    "安全": "公司政策：进入实验室区域需佩戴工牌，设备使用需登记。",
}


class NFCEvent(BaseModel):
    user: str
    device: str
    time: datetime.datetime


class Pattern(BaseModel):
    pattern: str
    level: str
    detail: str


# ---- 接口 ----
@app.post("/api/nfc_event")
async def post_nfc_event(event: NFCEvent):
    """接收 NFC 刷卡事件"""
    events.append(event.model_dump())
    return event


@app.get("/api/events")
async def get_events():
    return {"events": events, "count": len(events)}


@app.post("/api/analyze", response_model=List[Pattern])
async def post_analyze():
    """模式分析：连续加班 + 异常频次"""
    results = []
    if not events:
        return results

    # 1. 连续加班：按用户分组，日期去重，找连续日期段（每天 >= 18:00 算加班打卡）
    by_user = {}
    for e in events:
        by_user.setdefault(e["user"], []).append(e)
    for user, evs in by_user.items():
        days = {}
        for e in evs:
            d = e["time"].date()
            if e["time"].hour >= 18:
                days.setdefault(d, []).append(e)
        if not days:
            continue
        sorted_days = sorted(days.keys())
        # 找最长连续日期段
        streak, best = 1, 1
        for i in range(1, len(sorted_days)):
            if (sorted_days[i] - sorted_days[i - 1]).days == 1:
                streak += 1
                best = max(best, streak)
            else:
                streak = 1
        if best >= 3:
            results.append(Pattern(
                pattern="连续加班", level="高",
                detail=f"用户 {user} 连续加班 {best} 天（每天 18:00 后刷卡）",
            ))

    # 2. 异常频次：同一设备相邻两次事件间隔 < 300 秒
    by_device = {}
    for e in events:
        by_device.setdefault(e["device"], []).append(e)
    for device, evs in by_device.items():
        evs.sort(key=lambda x: x["time"])
        for i in range(1, len(evs)):
            gap = (evs[i]["time"] - evs[i - 1]["time"]).total_seconds()
            if 0 < gap < 300:
                results.append(Pattern(
                    pattern="异常频次", level="中",
                    detail=f"设备 {device} 在 {(evs[i]['time'] - evs[i-1]['time']).total_seconds():.0f} 秒内重复刷卡（{evs[i-1]['user']} → {evs[i]['user']}）",
                ))
                break  # 每设备一条即可
    return results


async def llm_remind(patterns: List[dict]) -> str:
    """LLM 生成个性化提醒（天团评审修复：Agent 接入真模型；失败回退关键词）"""
    if not DEEPSEEK_KEY:
        raise HTTPException(status_code=400, detail="DEEPSEEK_API_KEY is missing")
    
    try:
        payload = {
            "model": DEEPSEEK_MODEL,
            "max_tokens": 500,
            "system": "你是企业安全提醒助手。根据模式分析结果生成一段个性化提醒文本（中文，简短，结合工作健康），只输出提醒文本。",
            "messages": [{"role": "user",
                          "content": "模式分析结果：\n" + "\n".join(f"- {p['pattern']}({p['level']}): {p['detail']}" for p in patterns)}],
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                DEEPSEEK_BASE,
                headers={"x-api-key": DEEPSEEK_KEY, "anthropic-version": "2023-06-01"},
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
        return next((b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"), "")
    except Exception:
        return ""


@app.post("/api/remind")
async def post_remind():
    """Agent 推理：模式 → LLM 生成提醒（失败回退关键词匹配）"""
    patterns = await post_analyze()
    if not patterns:
        return {"patterns": [], "reminders": []}
    llm_text = await llm_remind(patterns)
    reminders = []
    if llm_text:
        reminders = [{"pattern": p.pattern, "level": p.level,
                      "detail": p.detail, "policy": llm_text} for p in patterns]
    else:
        for p in patterns:
            matched = next((v for k, v in POLICIES.items() if k == p.pattern), None)
            reminders.append({"pattern": p.pattern, "level": p.level,
                              "detail": p.detail,
                              "policy": matched if matched else "未检索到相关政策"})
    return {"patterns": patterns, "reminders": reminders}


@app.get("/api/health")
async def health():
    return {"status": "ok", "events_count": len(events)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8690)