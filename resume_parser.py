"""简历解析：简历文本 -> 结构化 JSON"""
import json

from config import chat

SYSTEM_PROMPT = """你是资深 HR 简历解析器。从用户提供的简历文本中提取以下信息，严格输出 JSON（不要输出其他内容）：
{
  "name": "姓名（未知则填 未知）",
  "education": "最高学历与学校",
  "years": "工作年限（数字，未知填 null）",
  "skills": ["核心技能列表"],
  "projects": ["项目经验要点（每项目一行概括）"],
  "target_role": "求职方向/意向岗位（未知则填 未知）"
}"""


def parse_resume(resume_text: str) -> dict:
    """解析简历文本，返回结构化字典"""
    content = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"简历内容：\n{resume_text[:8000]}"},
        ],
        temperature=0.2,
    )
    # 容错：去掉 markdown 代码块标记
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 提取最外层花括号
        start, end = content.find("{"), content.rfind("}")
        if start >= 0 and end > start:
            return json.loads(content[start : end + 1])
        raise RuntimeError(f"简历解析失败，模型返回：{content[:200]}")


def format_resume_summary(resume: dict) -> str:
    """把结构化简历格式化成给面试官看的中文摘要"""
    return (
        f"姓名：{resume.get('name', '未知')}\n"
        f"学历：{resume.get('education', '未知')}\n"
        f"工作年限：{resume.get('years', '未知')}\n"
        f"核心技能：{', '.join(resume.get('skills', []))}\n"
        f"项目经验：\n" + "\n".join(f"- {p}" for p in resume.get("projects", [])) +
        f"\n求职方向：{resume.get('target_role', '未知')}"
    )


PRE_SCREEN_PROMPT = """你是招聘初筛系统。根据候选人简历，输出 JSON（不要其他内容）：
{
  "match": "高/中/低",
  "reason": "一句话初筛意见（为什么匹配或不匹配）",
  "focus": "后续沟通中需要重点核实的点"
}"""


def pre_screen(resume: dict) -> str:
    """快速初筛，返回 Markdown 摘要"""
    content = chat(
        [
            {"role": "system", "content": PRE_SCREEN_PROMPT},
            {"role": "user", "content": f"候选人简历：\n{format_resume_summary(resume)}"},
        ],
        temperature=0.2,
    )
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        data = json.loads(content[start : end + 1])
    match = data.get("match", "中")
    return (
        f"**初筛结论：{match}匹配**\n\n"
        f"**初筛意见：** {data.get('reason', '—')}\n"
        f"**沟通中需重点核实：** {data.get('focus', '—')}"
    )
