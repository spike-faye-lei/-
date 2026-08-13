"""招聘流程自动化工具：JD 生成 + 岗位 rubric 自动匹配 + 面试题库生成"""
from config import chat
from crawler import match_profile
from job_profile import REVIEWER_NAMES, get_profile
from llm_utils import parse_llm_json

JD_SYSTEM = """你是资深招聘专家。根据用户提供的岗位需求，生成一份完整规范的招聘 JD。严格输出 JSON（不要其他内容）：
{{
  "title": "岗位名称",
  "duties": ["岗位职责，4-6 条，具体可量化"],
  "requirements": ["任职要求，4-6 条，含学历/经验/技能"],
  "plus": ["加分项，2-3 条"],
  "salary": "薪资范围（用户未提供则写 面议）"
}}"""


def generate_jd(role_name: str, notes: str) -> dict:
    """输入岗位名称 + 要点，输出结构化 JD"""
    user = f"岗位名称：{role_name or '未指定'}"
    if notes and notes.strip():
        user += f"\n岗位要点：{notes.strip()}"
    content = chat(
        [
            {"role": "system", "content": JD_SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.5,
    )
    return parse_llm_json(content)


def jd_to_markdown(jd: dict) -> str:
    """JD dict → markdown（含 rubric 匹配结果）"""
    lines = [f"## {jd.get('title', '未命名岗位')}", "", f"**薪资范围：** {jd.get('salary', '面议')}", "", "### 岗位职责"]
    lines += [f"{i}. {d}" for i, d in enumerate(jd.get("duties", []), 1)]
    lines += ["", "### 任职要求"]
    lines += [f"{i}. {r}" for i, r in enumerate(jd.get("requirements", []), 1)]
    plus = jd.get("plus", [])
    if plus:
        lines += ["", "### 加分项"]
        lines += [f"{i}. {p}" for i, p in enumerate(plus, 1)]
    return "\n".join(lines)


def match_rubric_markdown(jd: dict) -> str:
    """把 JD 关键词匹配到内置岗位 rubric（复用爬虫的同款关键词匹配，确定性）"""
    jd_text = f"{jd.get('title', '')} {' '.join(jd.get('duties', []))} {' '.join(jd.get('requirements', []))}"
    pid = match_profile(jd_text)
    profile = get_profile(pid)
    dims = "、".join(
        f"{d['name']}（权重 {d['weight']}% · {REVIEWER_NAMES.get(d.get('reviewer'), '技术考官')}）"
        for d in profile["dimensions"]
    )
    rules = "\n".join(f"- {r}" for r in profile["rules"])
    return (
        f"### 岗位配置匹配\n\n"
        f"自动匹配到内置评估配置：**{profile['job']}**（{pid}）\n\n"
        f"评估维度：{dims}\n\n评分规则：\n{rules}\n\n"
        f"> 面试时将按此配置进行多考官评分"
    )


QUESTION_SYSTEM = """你是资深技术面试官。按岗位配置为每个评估维度出面试题。严格输出 JSON（不要其他内容）：
{{
  "dimensions": [
    {{
      "dimension": "维度名（必须与岗位配置一致）",
      "questions": [
        {{"q": "面试题（结合真实场景，可追问细节）", "difficulty": "基础/进阶/深度", "followup": "追问点"}}
      ]
    }}
  ]
}}"""


def generate_questions(profile: dict, per_dim: int = 3) -> str:
    """按岗位维度生成面试题库（每维度 per_dim 题，三档难度），返回 markdown"""
    dim_names = "、".join(d["name"] for d in profile["dimensions"])
    content = chat(
        [
            {"role": "system", "content": QUESTION_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"招聘岗位：{profile['job']}\n"
                    f"评估维度：{dim_names}\n"
                    f"每个维度出 {per_dim} 道题，难度覆盖 基础/进阶/深度 三档。"
                ),
            },
        ],
        temperature=0.6,
    )
    data = parse_llm_json(content)
    lines = [f"## 面试题库（{profile['job']}）", ""]
    valid = {d["name"] for d in profile["dimensions"]}
    for group in data.get("dimensions", []):
        dim = group.get("dimension", "未命名维度")
        if dim not in valid:
            continue  # 配置外维度忽略（不信任 LLM）
        lines += [f"### {dim}"]
        for i, item in enumerate(group.get("questions", []), 1):
            diff = item.get("difficulty", "基础")
            lines.append(f"{i}. 【{diff}】{item.get('q', '')}")
            if item.get("followup"):
                lines.append(f"   - 追问点：{item['followup']}")
        lines.append("")
    return "\n".join(lines) if len(lines) > 2 else "题库生成失败：模型未返回有效题目，请重试"
