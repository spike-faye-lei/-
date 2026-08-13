"""LLM 输出解析小工具：JSON 容错解析 + 分数钳制（evaluator/bulk_screen/compare 共用）"""
import json


def parse_llm_json(content: str) -> dict:
    """容错解析 LLM 输出的 JSON：去掉 ``` 代码块标记，截取最外层花括号"""
    content = (content or "").strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        return json.loads(content[start : end + 1])


def to_score(value) -> float:
    """分数钳制到 [0, 10]，非法值按 0 处理（不信任 LLM 输出）"""
    try:
        s = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(10.0, s))
