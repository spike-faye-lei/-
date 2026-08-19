import hashlib
import hmac
import json
import os
import secrets
import uuid
from datetime import datetime

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()
if not os.getenv("DEEPSEEK_API_KEY"):
    raise EnvironmentError("DEEPSEEK_API_KEY 环境变量未设置")
DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE", "https://api.deepseek.com/anthropic/v1/messages")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro")

if not os.getenv("NFC_DEVICE_SECRET"):
    raise EnvironmentError("NFC_DEVICE_SECRET 环境变量未设置")
DEVICE_SECRET = os.getenv("NFC_DEVICE_SECRET")

# 内存模拟标签库（演示用，真实场景为 NFC 标签）
mock_tags = {}

# 已发放挑战值（天团评审修复：challenge -> 过期时间戳，60 秒有效期，一次性）
challenge_store = {}


# ---- 模型 ----
class WriteRequest(BaseModel):
    content: str  # 要写入标签的内容（文本/JSON）
    owner: str = "demo-user"  # 写入者


class WriteResult(BaseModel):
    allowed: bool
    reasons: list
    signed_data: dict = None
    tag_id: str = None


class AuthRequest(BaseModel):
    tag_id: str
    challenge: str
    response: str


class AuthResult(BaseModel):
    ok: bool
    message: str


# ---- 工具 ----
def sign_data(data: dict) -> dict:
    """HMAC-SHA256 签名（演示）。天团评审结论：ts 必须先加入 payload 再签名（防重放）。"""
    ts = int(datetime.now().timestamp())
    payload = json.dumps({**data, "ts": ts}, sort_keys=True, ensure_ascii=False)
    sig = hmac.new(DEVICE_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return {**data, "sig": sig, "ts": ts}


def verify_signature(data: dict) -> bool:
    sig = data.get("sig")
    if not sig:
        return False
    original_data = {k: v for k, v in data.items() if k != "sig"}
    payload = json.dumps(original_data, sort_keys=True, ensure_ascii=False)
    expect = hmac.new(DEVICE_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expect)


async def llm_judge(content: str, owner: str) -> dict:
    """AI 内容合法性校验：敏感词/格式/分类"""
    system = (
        "你是 NFC 标签内容安全审查员。用户要往 NFC 标签写入一段内容，"
        "请判断是否允许写入。输出 JSON：{\"allowed\": true/false, \"reasons\": [\"原因\"], \"category\": \"内容分类\"}。"
        "拒绝情形：诈骗/违法信息、恶意链接、冒充身份、色情暴力内容。"
        "普通内容如优惠信息、名片、URL、祝福语等允许。只输出 JSON。"
    )
    payload = {
        "model": DEEPSEEK_MODEL,
        "max_tokens": 500,
        "system": system,
        "messages": [{"role": "user", "content": f"写入者: {owner}\n内容: {content}"}],
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            DEEPSEEK_BASE,
            headers={"x-api-key": DEEPSEEK_KEY, "anthropic-version": "2023-06-01"},
            json=payload,
        )
        if not (200 <= r.status_code < 300):
            raise HTTPException(r.status_code, f"AI 校验失败: {r.text}")
        data = r.json()
    text = next((b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"), "")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {"allowed": True, "reasons": [], "category": "未知"}
    return json.loads(text[start : end + 1])


# ---- 接口 ----
@app.post("/api/card/write-check", response_model=WriteResult)
async def write_check(req: WriteRequest):
    if not req.content.strip():
        raise HTTPException(400, "内容为空")
    try:
        judge = await llm_judge(req.content, req.owner)
    except Exception as e:
        raise HTTPException(502, f"AI 校验失败: {e}")

    allowed = judge.get("allowed", False)
    reasons = judge.get("reasons", [])
    if allowed:
        tag_id = f"TAG-{uuid.uuid4().hex[:8].upper()}"
        record = {"owner": req.owner, "content": req.content,
                  "category": judge.get("category", "未知"), "written_at": datetime.now().isoformat()}
        signed = sign_data(record)
        mock_tags[tag_id] = signed
        return WriteResult(allowed=True, reasons=reasons, signed_data=signed, tag_id=tag_id)
    return WriteResult(allowed=False, reasons=reasons)


@app.get("/api/card/challenge")
async def get_challenge(response: Response):
    """读卡身份认证：服务端发挑战值（60 秒有效）。演示模式经响应头下发密钥（生产环境密钥在设备端）"""
    challenge = secrets.token_hex(16)
    challenge_store[challenge] = datetime.now().timestamp() + 60
    return {"challenge": challenge}


@app.post("/api/card/auth", response_model=AuthResult)
async def auth_card(req: AuthRequest):
    """读卡认证：校验 HMAC 响应 + 标签签名完整性"""
    # 0. 挑战值有效性：存在且未过期，验证后一次性删除
    exp = challenge_store.get(req.challenge)
    if not exp or datetime.now().timestamp() > exp:
        raise HTTPException(401, "挑战值无效或已过期")
    tag = mock_tags.get(req.tag_id)
    if not tag:
        raise HTTPException(404, "标签不存在")
    # 1. 验证签名数据完整性
    data = dict(tag)
    if not verify_signature(data):
        return AuthResult(ok=False, message="签名校验失败：数据被篡改")
    # 2. 验证挑战-响应
    expect = hmac.new(DEVICE_SECRET.encode(), req.challenge.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect, req.response):
        return AuthResult(ok=False, message="挑战响应错误：身份验证失败")
    del challenge_store[req.challenge]  # 一次性
    return AuthResult(ok=True, message="身份验证通过，标签内容可信")


@app.get("/api/card/{tag_id}")
async def read_card(tag_id: str):
    tag = mock_tags.get(tag_id)
    if not tag:
        raise HTTPException(404, "标签不存在")
    return {"tag_id": tag_id, "record": {k: v for k, v in tag.items() if k != "sig"}}


@app.get("/api/cards")
async def get_cards():
    """标签列表（不含签名）"""
    return [{"tag_id": k, "owner": v["owner"], "category": v["category"]} for k, v in mock_tags.items()]


@app.delete("/api/cards/{tag_id}")
async def delete_card(tag_id: str):
    if tag_id not in mock_tags:
        raise HTTPException(404, "标签不存在")
    del mock_tags[tag_id]
    return {"ok": True, "message": "标签已删除"}


@app.post("/api/cards/{tag_id}/tamper")
async def tamper_card(tag_id: str):
    """篡改演示：改 content 首字符，签名失效，认证必失败"""
    if tag_id not in mock_tags:
        raise HTTPException(404, "标签不存在")
    record = mock_tags[tag_id]
    record["content"] = "X" + record["content"][1:]
    return {"tampered": True, "hint": "现在去认证会失败"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "tags": len(mock_tags)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8688)