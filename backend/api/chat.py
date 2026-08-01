"""
AI 营养师对话
POST /api/chat — 将用户饮食记录作为上下文，调用 DeepSeek 回答营养问题

环境变量:
  DEEPSEEK_API_KEY — DeepSeek API 密钥 (https://platform.deepseek.com)
  未配置时返回友好提示，不影响其他功能
"""
import os
import json
import urllib.request
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.database import get_history

router = APIRouter(prefix="/api", tags=["chat"])

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

SYSTEM_PROMPT = """你是"智能厨房助手"内置的 AI 营养师，回答用户关于饮食营养的问题。
要求：
1. 使用中文，简洁专业，口语化但准确
2. 回答时引用用户当天的饮食记录数据（如已提供）
3. 给出具体可执行的建议（食物选择、分量、搭配）
4. 涉及医学问题（疾病、用药）时提示"建议咨询专业医生"
5. 每次回答控制在 150 字以内，重点突出"""


class ChatRequest(BaseModel):
    message: str
    member: str = "default"
    days: int = 1


def _call_deepseek(messages, api_key):
    """调用 DeepSeek API（urllib，无第三方依赖）"""
    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": 300,
    }).encode("utf-8")

    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _build_context(records):
    """把饮食记录转成上下文文本"""
    if not records:
        return "用户今天还没有饮食记录。"
    lines = []
    for r in records[:20]:
        lines.append(
            f"- {r.get('food_name_cn') or r.get('food_name')} "
            f"{r.get('weight_g', 0):.0f}g "
            f"({r.get('calories', 0):.0f} kcal, 蛋白 {r.get('protein_g', 0):.0f}g, "
            f"脂肪 {r.get('fat_g', 0):.0f}g, 碳水 {r.get('carbs_g', 0):.0f}g)"
        )
    return "用户今天的饮食记录：\n" + "\n".join(lines)


@router.post("/chat")
async def chat(request: ChatRequest):
    """AI 营养师对话"""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return {
            "success": False,
            "reply": "AI 营养师尚未配置。请在服务器设置环境变量 DEEPSEEK_API_KEY 后重启服务。",
            "configured": False,
        }

    # 拉取用户饮食记录作为上下文
    records = get_history(days=request.days, member=request.member, limit=20)
    context = _build_context(records)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{context}\n\n用户问题：{request.message}"},
    ]

    try:
        reply = _call_deepseek(messages, api_key)
        return {"success": True, "reply": reply.strip(), "configured": True}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败: {str(e)[:100]}")
