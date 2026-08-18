"""批量简历初筛：LLM 逐份评分（证据链口径与面试评估一致）→ 代码加权 → 排序

演示规模每批上限 20 份；生产叙事：1000 份简历 = 分 50 批处理，每批后过人工复核闸门。
"""
from config import chat
from job_profile import profile_summary
from llm_utils import parse_llm_json, to_score

BATCH_LIMIT = 20  # 每批上限（LLM 逐份调用，演示控制时长）

SCREEN_SYSTEM = """你是招聘平台的简历初筛专家，按岗位配置对简历逐份打分。严格输出 JSON（不要其他内容）：
{{
  "dimension_scores": {{
    "维度名(必须与岗位配置的维度完全一致)": {{"score": 0-10的数字, "evidence": "引用简历原文作为证据，必须具体"}}
  }},
  "highlights": ["候选人优势，1-2条"],
  "risks": ["风险点或硬伤，1-2条"],
  "decision": "建议进入面试" 或 "建议淘汰",
  "comment": "一句话点评"
}}

岗位配置与评分规则（必须遵守）：
{profile}

注意：只依据简历原文打分，禁止脑补；维度名必须与岗位配置完全一致，不要自创维度。"""


def screen_resume(resume_text: str, profile: dict) -> dict:
    """单份简历评分。返回 {dimension_scores, highlights, risks, decision, comment, total}

    加权总分由代码计算（不信任 LLM 算数）；配置了但没评的维度按 0 分计入防虚高。
    """
    content = chat(
        [
            {"role": "system", "content": SCREEN_SYSTEM.format(profile=profile_summary(profile))},
            {"role": "user", "content": f"候选人简历：\n{resume_text[:3500]}"},
        ],
        temperature=0.1,
    )
    data = parse_llm_json(content)

    weight_map = {d["name"]: d["weight"] for d in profile["dimensions"]}
    raw = data.get("dimension_scores", {})
    scores = {}
    evidence = {}  # 证据链保留：维度名 → 简历原文引用（评分卡展示用）
    weighted_sum = 0.0
    weight_total = 0
    for dim in profile["dimensions"]:
        name = dim["name"]
        item = raw.get(name, {})
        score = to_score(item.get("score", 0)) if isinstance(item, dict) else to_score(item)
        scores[name] = score
        if isinstance(item, dict) and item.get("evidence"):
            evidence[name] = item["evidence"]
        w = weight_map[name]
        weighted_sum += score * w
        weight_total += w
    data["dimension_scores"] = scores
    data["evidence"] = evidence
    data["total"] = round(weighted_sum / weight_total, 1) if weight_total else 0
    return data


def screen_batch(resumes, profile: dict):
    """批量初筛（generator）：resumes = [(name, source, text)]

    每完成一份 yield (done, total, 当前按总分降序的部分结果)；
    单份失败不中断整批（记 error，总分 -1 排末尾）。
    调用方在循环结束后取最后一次 yield 的结果即完整排序。
    """
    results = []
    total = len(resumes)
    for i, (name, source, text) in enumerate(resumes, 1):
        try:
            r = screen_resume(text, profile)
            r.update(name=name, source=source, resume_text=text)
        except Exception as e:
            r = {"name": name, "source": source, "resume_text": text, "error": str(e), "total": -1.0}
        results.append(r)
        yield i, total, sorted(results, key=lambda r: r.get("total", -1), reverse=True)
