"""筛选决策报告：多考官分组评审（技术考官/文化考官）+ 证据链评分 + 加权总分 + 雷达图
评分确定性：LLM 只输出各维度分数与证据，加权总分由代码计算
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

# 中文字体配置：雷达图标签必须用中文字体，否则全是方块
# 精确匹配优先（排除 SimSun-ExtG 这类生僻字库），按优先级取第一个可用字体
_ZH_FONT_PRIORITY = ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans SC", "Noto Sans CJK SC"]
_available = {f.name for f in font_manager.fontManager.ttflist}
_zh_font = next((n for n in _ZH_FONT_PRIORITY if n in _available), None)
if _zh_font:
    matplotlib.rcParams["font.family"] = _zh_font
matplotlib.rcParams["axes.unicode_minus"] = False

from config import chat
from job_profile import REVIEWER_NAMES, profile_summary

EVALUATOR_SYSTEM = """你是招聘评估系统的评审委员会负责人，组织技术考官与文化考官分别评审候选人。严格输出 JSON（不要其他内容）：
{{
  "reviewers": {{
    "tech": [
      {{"name": "维度名(必须与岗位配置的技术维度一致)", "score": 0-10的数字, "evidence": "引用候选人原话或简历原文作为证据，必须具体", "reason": "一句话评分理由"}}
    ],
    "culture": [
      {{"name": "维度名(必须与岗位配置的文化维度一致)", "score": 0-10的数字, "evidence": "引用候选人原话或简历原文作为证据，必须具体", "reason": "一句话评分理由"}}
    ]
  }},
  "highlights": ["候选人优势，2-3条，每条附证据"],
  "risks": ["候选人风险点，1-2条，每条附证据"],
  "decision": "通过/不通过",
  "invite": "通过时给线下面试邀约话术（含时间地点）；不通过时给婉拒话术",
  "comment": "一句话总结论"
}}

岗位配置与评分规则（必须遵守）：
{profile}

考官分工：
- 技术考官（tech）：按技术维度评分，必须是懂技术的专家视角，能识别技术深浅
- 文化考官（culture）：按软性维度评分，考察沟通、动机、团队契合

注意：评分必须引用对话或简历中的具体内容作为证据，禁止无依据打分；评分要公允，候选人紧张或话少不算技术缺陷，只看证据。"""


def _parse_json(content: str) -> dict:
    """容错解析 LLM 输出的 JSON"""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        return json.loads(content[start : end + 1])


def _to_score(value) -> float:
    """分数钳制到 [0, 10]，非法值按 0 处理（不信任 LLM 输出）"""
    try:
        s = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(10.0, s))


def radar_figure(profile: dict, dimension_scores: dict):
    """生成评分雷达图（matplotlib）"""
    dims = [d["name"] for d in profile["dimensions"]]
    vals = [max(0, min(10, float(dimension_scores.get(d, 0)))) for d in dims]
    angles = np.linspace(0, 2 * np.pi, len(dims), endpoint=False).tolist()
    vals += vals[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(5.2, 4.2), subplot_kw=dict(polar=True))
    ax.plot(angles, vals, color="#4f46e5", linewidth=2)
    ax.fill(angles, vals, color="#4f46e5", alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([f"{d}\n{s}/10" for d, s in zip(dims, vals[:-1])], fontsize=10)
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], fontsize=8, color="#94a3b8")
    ax.grid(color="#e2e8f0")
    ax.set_title("候选人能力雷达图", fontsize=12, pad=18)
    plt.tight_layout()
    return fig


def evaluate(session, profile: dict):
    """多考官评审：返回 (markdown 报告, 雷达图 figure)"""
    history_text = "\n".join(
        f"{'AI 招聘官' if m['role'] == 'assistant' else '候选人'}：{m['content']}"
        for m in session.history
    )
    content = chat(
        [
            {"role": "system", "content": EVALUATOR_SYSTEM.format(profile=profile_summary(profile))},
            {
                "role": "user",
                "content": f"候选人简历：\n{session.resume}\n\n沟通过程：\n{history_text[-6000:]}",
            },
        ],
        temperature=0.1,
    )
    data = _parse_json(content)

    # 按考官分组收集分数（代码计算加权总分，确定性）
    reviewers = data.get("reviewers", {})
    weight_map = {d["name"]: d["weight"] for d in profile["dimensions"]}
    dimension_scores = {}
    weighted_sum = 0.0
    weight_total = 0
    tech_weight = tech_sum = 0
    culture_weight = culture_sum = 0
    unknown_dims = []
    for group in ("tech", "culture"):
        for d in reviewers.get(group, []):
            name = d.get("name", "")
            score = _to_score(d.get("score", 0))
            if name not in weight_map:
                unknown_dims.append(name)  # 配置外的维度：忽略并提示，不静默
                continue
            dimension_scores[name] = score
            w = weight_map.get(name, 0)
            weighted_sum += score * w
            weight_total += w
            if group == "tech":
                tech_weight += w
                tech_sum += score * w
            else:
                culture_weight += w
                culture_sum += score * w
    # 配置了但模型没评的维度：按 0 分计入并提示（防总分虚高）
    missing_dims = [d["name"] for d in profile["dimensions"] if d["name"] not in dimension_scores]
    for name in missing_dims:
        dimension_scores[name] = 0.0
    total = round(weighted_sum / weight_total, 1) if weight_total else 0
    data["total"] = total
    session.report = data  # 存给 HR 审核闸门用
    tech_score = round(tech_sum / tech_weight, 1) if tech_weight else 0
    culture_score = round(culture_sum / culture_weight, 1) if culture_weight else 0

    decision = data.get("decision", "通过")
    lines = [
        f"## 筛选决策报告（{profile['job']}）",
        "",
        f"**加权总分：{total}/10**（各维度按岗位权重加权，代码计算）",
        "",
        f"**多考官评审：** 技术考官 {tech_score}/10（权重{tech_weight}%） ｜ 文化考官 {culture_score}/10（权重{culture_weight}%）",
        "",
    ]
    if missing_dims:
        lines += [f"> ⚠️ **未获评分维度（按 0 分计入）：** {'、'.join(missing_dims)}", ""]
    if unknown_dims:
        lines += [f"> ⚠️ **模型输出了配置外的维度，已忽略：** {'、'.join(unknown_dims)}", ""]
    for group in ("tech", "culture"):
        label = REVIEWER_NAMES.get(group, group)
        lines += [f"### {label}评分", "", "| 维度 | 得分 | 证据 |", "| --- | --- | --- |"]
        for d in reviewers.get(group, []):
            name, score = d.get("name", "?"), d.get("score", 0)
            bar = "█" * int(score) + "░" * (10 - int(score))
            evidence = d.get("evidence", "—")
            if len(evidence) > 55:
                evidence = evidence[:55] + "…"
            lines.append(f"| {name} | {score}/10 {bar} | {evidence} |")
        lines.append("")

    lines += ["**优势亮点：**"]
    lines += [f"- {h}" for h in data.get("highlights", [])]
    lines += ["", "**风险提示：**"]
    lines += [f"- {r}" for r in data.get("risks", [])]
    lines += [
        "",
        f"**筛选决策：{decision}**",
        "",
        f"**下一步（待 HR 审核确认后发送）：** {data.get('invite', '—')}",
        "",
        f"**总评：** {data.get('comment', '—')}",
    ]
    return "\n".join(lines), radar_figure(profile, dimension_scores)
