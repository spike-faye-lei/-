"""多候选人横向对比：代码生成确定性对比矩阵 + LLM 推荐排序与总结"""
from config import chat
from llm_utils import parse_llm_json

COMPARE_SYSTEM = """你是招聘评审负责人，基于多候选人的对比数据给出推荐排序。严格输出 JSON（不要其他内容）：
{{
  "ranking": ["候选人姓名，按推荐优先顺序排列"],
  "per_candidate": [{{"name": "姓名", "comment": "一句话点评（优势或短板，必须基于数据）"}}],
  "summary": "整体对比总结（2-3句：谁最强、梯队如何分布、建议优先联系谁）"
}}

注意：排序必须与对比矩阵的分数一致，不允许脱离数据排序；点评不得编造矩阵中没有的信息。"""


def build_matrix(entries, profile: dict) -> str:
    """代码生成对比矩阵（确定性，不依赖 LLM）：行=候选人，列=维度+总分+决策"""
    dims = [d["name"] for d in profile["dimensions"]]
    lines = [
        f"| 候选人 | {' | '.join(dims)} | 加权总分 | 决策 |",
        f"| --- | {' | '.join(['---'] * len(dims))} | --- | --- |",
    ]
    for e in entries:
        cells = " | ".join(f"{e.get('dimension_scores', {}).get(d, 0):.1f}" for d in dims)
        lines.append(f"| {e['name']} | {cells} | **{e.get('total', 0):.1f}** | {e.get('decision', '')} |")
    return "\n".join(lines)


def compare_report(entries, profile: dict):
    """entries = [{name, total, decision, dimension_scores}] → (对比矩阵 markdown, LLM 排序总结 markdown)"""
    matrix = build_matrix(entries, profile)
    content = chat(
        [
            {"role": "system", "content": COMPARE_SYSTEM},
            {"role": "user", "content": f"招聘岗位：{profile['job']}\n\n候选人对比如下：\n{matrix}\n\n请给出推荐排序与点评。"},
        ],
        temperature=0.3,
    )
    data = parse_llm_json(content)
    ranking = data.get("ranking") or [e["name"] for e in entries]  # 空列表/缺失都回退按分数顺序
    per = {c.get("name"): c.get("comment", "") for c in data.get("per_candidate", [])}
    lines = ["### AI 推荐排序"]
    for i, n in enumerate(ranking, 1):
        lines.append(f"{i}. **{n}** — {per.get(n, '')}")
    lines += ["", "### 综合评语", data.get("summary", "—")]
    return matrix, "\n".join(lines)
