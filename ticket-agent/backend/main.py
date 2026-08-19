"""工单自动生成 Agent — FastAPI 后端
流程: 自然语言指令 → 意图识别 → 知识库检索 → 工单生成 → 展示/导出
"""
import json
import os
import uuid
from datetime import datetime
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()
app = FastAPI(title="Ticket Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# ---- 配置 ----
DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE", "https://api.deepseek.com/anthropic/v1/messages")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro")
KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge")

INTENTS = ["报销", "请假", "采购"]

# 工单历史存储（天团代码师交付：内存字典）
ticket_history = {}


# ---- 模型 ----
class TicketRequest(BaseModel):
    text: str


class TicketOut(BaseModel):
    ticket_id: str
    intent: str
    fields: dict
    policy_refs: list
    status: str = "draft"
    warnings: list = []  # 审核警告（天团评审修复）


# ---- 知识库 ----
def load_knowledge() -> dict:
    """加载知识库：knowledge/*.json 或 *.md"""
    docs = {}
    if os.path.isdir(KNOWLEDGE_DIR):
        for fn in os.listdir(KNOWLEDGE_DIR):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(KNOWLEDGE_DIR, fn), encoding="utf-8") as f:
                        docs[fn[:-5]] = json.load(f)
                except Exception:
                    pass
    return docs


def retrieve_policy(kb: dict, intent: str, text: str) -> list:
    """简单检索：按意图匹配知识文档，取政策要点。后续可升级为向量检索。"""
    refs = []
    for name, doc in kb.items():
        if intent in name or intent in doc.get("intent", ""):
            refs.append({"source": name, "points": doc.get("policy", [])})
    return refs


# ---- LLM 调用（DeepSeek Anthropic 兼容接口）----
async def llm_json(system: str, user: str) -> dict:
    payload = {
        "model": DEEPSEEK_MODEL,
        "max_tokens": 2000,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            DEEPSEEK_BASE,
            headers={"x-api-key": DEEPSEEK_KEY, "anthropic-version": "2023-06-01"},
            json=payload,
        )
        r.raise_for_status()
        data = r.json()
    # v4-pro 是推理模型，content 里可能有 thinking 块，取 text 块
    text = next((b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"), "")
    # 提取 JSON（模型可能包在 ```json 里）
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"模型未返回 JSON: {text[:200]}")
    return json.loads(text[start : end + 1])


# ---- 接口 ----
@app.post("/api/generate", response_model=TicketOut)
async def generate_ticket(req: TicketRequest):
    if not req.text.strip():
        raise HTTPException(400, "指令不能为空")

    # 1. 意图识别 + 字段提取（一次调用）
    system = (
        "你是工单生成助手。用户会说一句自然语言指令（报销/请假/采购），"
        "你需要输出 JSON：{\"intent\":\"报销|请假|采购\", \"fields\":{...}}。"
        "报销字段: applicant(申请人), amount(金额), date(日期), reason(事由), invoice(是否开发票)；"
        "请假字段: applicant, start_date, end_date, days, reason；"
        "采购字段: applicant, item(物品), quantity(数量), budget(预算), reason。"
        "缺失的字段填 null。只输出 JSON，不要其他文字。"
    )
    try:
        result = await llm_json(system, req.text)
    except Exception as e:
        raise HTTPException(502, f"意图识别失败: {e}")

    intent = result.get("intent", "")
    if intent not in INTENTS:
        raise HTTPException(422, f"无法识别的意图: {intent}")

    # 2. 知识库检索
    kb = load_knowledge()
    policy_refs = retrieve_policy(kb, intent, req.text)

    # 3. 工单生成（结合政策补全字段/校验）
    system2 = (
        "你是工单审核员。根据政策要点检查用户填写的工单字段，"
        "输出 JSON：{\"fields\": {补全后的字段}, \"warnings\": [\"提示文本\"], \"ok\": true/false}。"
        "政策要点如下，字段缺失或超限时在 warnings 说明并在 fields 中补建议值。"
    )
    user2 = json.dumps({"用户指令": req.text, "提取字段": result.get("fields", {}), "政策": policy_refs}, ensure_ascii=False)
    try:
        checked = await llm_json(system2, user2)
    except Exception:
        checked = {"fields": result.get("fields", {}), "warnings": [], "ok": True}

    ticket_id = f"TK-{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    ticket_history[ticket_id] = TicketOut(
        ticket_id=ticket_id,
        intent=intent,
        fields=checked.get("fields", result.get("fields", {})),
        policy_refs=[p["source"] for p in policy_refs],
        status="draft",
        warnings=checked.get("warnings", []),
    )
    return ticket_history[ticket_id]


@app.get("/api/tickets")
async def get_tickets():
    """工单历史列表（按 ID 倒序 = 时间倒序）"""
    tickets = sorted(ticket_history.values(), key=lambda t: t.ticket_id, reverse=True)
    return [
        {"ticket_id": t.ticket_id, "intent": t.intent, "status": t.status}
        for t in tickets
    ]


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    """工单详情"""
    ticket = ticket_history.get(ticket_id)
    if not ticket:
        raise HTTPException(404, "工单不存在")
    return ticket


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": DEEPSEEK_MODEL}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8687)
