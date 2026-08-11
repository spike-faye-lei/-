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


def radar_figure(
    profile: dict,
    dimension_scores: dict,
    tech_score: float = None,
    culture_score: float = None,
    tech_weight: int = 0,
    culture_weight: int = 0,
    total: float = None,
    decision: str = None,
):
    """候选人评估数据看板（Python 数据分析绘图）：

    雷达图（能力轮廓） + 维度得分条形图（含权重） + 考官分组对比 + 总分/决策
    """
    dims = [d["name"] for d in profile["dimensions"]]
    reviewer_of = {d["name"]: d.get("reviewer", "tech") for d in profile["dimensions"]}
    weights = {d["name"]: d["weight"] for d in profile["dimensions"]}
    vals = [max(0.0, min(10.0, float(dimension_scores.get(d, 0)))) for d in dims]

    # 主色板（与 UI 主题一致）
    C_TECH = "#4f46e5"      # indigo：技术维度
    C_CULT = "#10b981"      # emerald：文化维度
    C_GRID = "#e2e8f0"
    C_TEXT = "#334155"

    fig = plt.figure(figsize=(12.5, 5.8), facecolor="white")
    gs = fig.add_gridspec(2, 3, height_ratios=[1.15, 1], width_ratios=[1, 1.15, 1.05],
                          left=0.07, right=0.97, top=0.88, bottom=0.10, hspace=0.55, wspace=0.45)

    # ---- 1. 雷达图（能力轮廓） ----
    ax = fig.add_subplot(gs[:, 0], polar=True)
    angles = np.linspace(0, 2 * np.pi, len(dims), endpoint=False).tolist()
    v = vals + vals[:1]
    a = angles + angles[:1]
    ax.plot(a, v, color=C_TECH, linewidth=2)
    ax.fill(a, v, color=C_TECH, alpha=0.22)
    ax.set_xticks(angles)
    ax.set_xticklabels([f"{d}\n{s:.1f}" for d, s in zip(dims, vals)], fontsize=9.5)
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], fontsize=7.5, color="#94a3b8")
    ax.grid(color=C_GRID)
    ax.set_title("候选人能力雷达图", fontsize=13, fontweight="bold", pad=16, color=C_TEXT)

    # ---- 2. 维度得分条形图（含权重） ----
    ax2 = fig.add_subplot(gs[0, 1:])
    ypos = np.arange(len(dims))[::-1]
    colors = [C_TECH if reviewer_of[d] == "tech" else C_CULT for d in dims]
    bars = ax2.barh(ypos, vals, height=0.58, color=colors, alpha=0.9, zorder=3)
    ax2.set_yticks(ypos)
    ax2.set_yticklabels(dims, fontsize=10)
    ax2.set_xlim(0, 10.6)
    ax2.set_xticks(range(0, 11, 2))
    ax2.set_xticklabels(range(0, 11, 2), fontsize=8.5, color="#94a3b8")
    ax2.tick_params(axis="y", colors=C_TEXT)
    for bar, d, s in zip(bars, dims, vals):
        ax2.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height() / 2,
                 f"{s:.1f} 分 · 权重{weights[d]}%", va="center", fontsize=9.5, color=C_TEXT)
    ax2.axvline(6, color="#f59e0b", linestyle="--", linewidth=1.2, alpha=0.7, zorder=2)
    ax2.text(6.05, len(dims) - 0.35, "及格线 6", fontsize=8.5, color="#f59e0b")
    ax2.set_title("各维度得分与岗位权重", fontsize=13, fontweight="bold", pad=10, color=C_TEXT)
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.grid(axis="x", color=C_GRID, zorder=0)

    # ---- 3. 考官分组对比（技术考官 vs 文化考官） ----
    ax3 = fig.add_subplot(gs[1, :2])
    ts = tech_score if tech_score is not None else 0
    cs = culture_score if culture_score is not None else 0
    groups = [("技术考官", ts, tech_weight, C_TECH), ("文化考官", cs, culture_weight, C_CULT)]
    y3 = np.arange(len(groups))
    for i, (label, score, w, c) in enumerate(groups):
        ax3.barh(i, score, height=0.5, color=c, alpha=0.9, zorder=3)
        ax3.text(score + 0.15, i, f"{score:.1f} / 10（权重 {w}%）", va="center", fontsize=10.5, color=C_TEXT)
    ax3.set_yticks(y3)
    ax3.set_yticklabels([g[0] for g in groups], fontsize=11)
    ax3.set_xlim(0, 10.8)
    ax3.set_xticks(range(0, 11, 2))
    ax3.set_xticklabels(range(0, 11, 2), fontsize=8.5, color="#94a3b8")
    ax3.tick_params(axis="y", colors=C_TEXT)
    ax3.set_title("多考官分组评审", fontsize=13, fontweight="bold", pad=10, color=C_TEXT)
    ax3.spines[["top", "right"]].set_visible(False)
    ax3.grid(axis="x", color=C_GRID, zorder=0)

    # ---- 4. 加权总分 + 决策 ----
    ax4 = fig.add_subplot(gs[1, 2])
    ax4.axis("off")
    t = total if total is not None else 0
    ok = decision != "不通过"
    ax4.text(0.5, 0.72, f"{t:.1f}", ha="center", fontsize=44, fontweight="bold",
             color=C_TECH, transform=ax4.transAxes)
    ax4.text(0.5, 0.52, "/ 10 · 岗位加权总分", ha="center", fontsize=11, color="#64748b",
             transform=ax4.transAxes)
    ax4.text(0.5, 0.28, f"筛选决策：{decision or '—'}", ha="center", fontsize=13,
             fontweight="bold", color=(C_CULT if ok else "#E2162A"), transform=ax4.transAxes)
    ax4.text(0.5, 0.12, "（AI 建议 · 最终由 HR 审核决定）", ha="center", fontsize=8.5,
             color="#94a3b8", transform=ax4.transAxes)

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
        w = weight_map.get(name, 0)
        weight_total += w  # 权重计入分母：缺失维度按 0 分拉低总分
        reviewer = next((d.get("reviewer") for d in profile["dimensions"] if d["name"] == name), None)
        if reviewer == "tech":
            tech_weight += w
        else:
            culture_weight += w
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
    return "\n".join(lines), radar_figure(
        profile,
        dimension_scores,
        tech_score=tech_score,
        culture_score=culture_score,
        tech_weight=tech_weight,
        culture_weight=culture_weight,
        total=total,
        decision=decision,
    )
