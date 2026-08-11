"""候选人 AI 模拟器：基于简历人设自动回答招聘官的问题
用于全自动演示——招聘官 AI 与候选人 AI 互相聊天
"""
from config import chat, chat_stream

CANDIDATE_SYSTEM = """你是候选人{name}，正在与「智聘科技」的 AI 招聘官沟通。
你的简历：
{resume}

人设与回答规则：
1. 严格按简历内容如实回答，不夸大、不编造
2. 回答简洁专业（2-3 句），技术问题给出具体细节；简历里没有的深度问题，可以说"没有实际做过"
3. 简历里没有的技能，直接说不会或没接触过，不要硬编
4. 用中文，语气自然，像真实求职者
5. 只回答招聘官的问题，不要反问"""


def _build_messages(name: str, resume_text: str, chat_history: list, question: str) -> list:
    messages = [
        {
            "role": "system",
            "content": CANDIDATE_SYSTEM.format(name=name, resume=resume_text[:3000]),
        }
    ]
    messages.extend(chat_history[-6:])  # 只看最近几轮，保持人设一致
    messages.append({"role": "user", "content": f"招聘官刚说：{question}\n请以你的身份回答。"})
    return messages


def reply(name: str, resume_text: str, chat_history: list, question: str) -> str:
    """候选人 AI 基于简历人设回答当前问题"""
    return chat(_build_messages(name, resume_text, chat_history, question), temperature=0.8)


def reply_stream(name: str, resume_text: str, chat_history: list, question: str):
    """流式版 reply：逐块 yield 回复增量（打字机效果）"""
    parts = []
    for chunk in chat_stream(_build_messages(name, resume_text, chat_history, question), temperature=0.8):
        parts.append(chunk)
        yield "".join(parts)
