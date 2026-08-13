"""真实 DeepSeek API 冒烟测试（默认跳过：不烧钱、不依赖网络，CI/日常回归保持全离线）。

为什么要这几条：单元测试全部 mock，验证的是"代码对 LLM 输出假设了什么"；
这几条验证"真实模型是否遵守那些假设"（prompt 服从度），是招聘流程正确性的关键一环。

运行（会真实调用 API，产生少量费用）：
    PowerShell：$env:RUN_LIVE_TESTS='1'; py -3.12 -m pytest tests/test_smoke_live.py -q
    CMD：       set RUN_LIVE_TESTS=1 && py -3.12 -m pytest tests/test_smoke_live.py -q
"""
import os

import pytest

from config import chat
from evaluator import EVALUATOR_SYSTEM
from interviewer import CLOSING_PROMPT
from jd_generator import generate_jd
from job_profile import get_profile, profile_summary
from llm_utils import parse_llm_json, to_score

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("RUN_LIVE_TESTS"),
        reason="默认跳过真实 API 测试；设置 RUN_LIVE_TESTS=1 才运行",
    ),
]

_SAMPLE_RESUME = "张三，28 岁，3 年 Python 后端经验，主导过订单系统的缓存优化（Redis 热点 key 拆分，接口 P99 从 300ms 降到 80ms）。"
_SAMPLE_DIALOG = (
    "AI 招聘官：介绍一下你最有挑战的项目。\n"
    "候选人：做了订单系统，Redis 缓存优化，热点 key 拆分，P99 从 300ms 降到 80ms。"
)


class TestClosingPrompt:
    """收口 prompt 服从度：必须以「【结论】」开头，且结论二选一（面试闭环的硬前提）"""

    def test_结论开头且通过不通过二选一(self):
        reply = chat(
            [
                {"role": "system", "content": CLOSING_PROMPT},
                {"role": "user", "content": "【对话已结束】请现在输出最终筛选结果。"},
            ],
            temperature=0.3,
        )
        assert reply.startswith("【结论】"), f"收口未以【结论】开头：{reply[:100]}"
        has_pass = "通过" in reply and "不通过" not in reply
        has_reject = "不通过" in reply
        assert has_pass or has_reject, f"结论必须明确二选一：{reply[:100]}"


class TestEvaluatorContract:
    """评估 JSON 契约：可解析、维度不超岗位配置、分数在 0-10、决策落在三值之一"""

    def test_输出可解析且符合岗位配置(self):
        profile = get_profile("ai-dev")
        content = chat(
            [
                {"role": "system", "content": EVALUATOR_SYSTEM.format(profile=profile_summary(profile))},
                {
                    "role": "user",
                    "content": f"候选人简历：\n{_SAMPLE_RESUME}\n\n沟通过程：\n{_SAMPLE_DIALOG}",
                },
            ],
            temperature=0.1,
        )
        data = parse_llm_json(content)
        reviewers = data.get("reviewers", {})
        assert reviewers.get("tech") or reviewers.get("culture"), "评审维度不能为空"
        dim_names = {d["name"] for d in profile["dimensions"]}
        for group in ("tech", "culture"):
            for d in reviewers.get(group, []):
                assert d.get("name") in dim_names, f"维度超出岗位配置：{d}"
                assert 0 <= to_score(d.get("score")) <= 10, f"分数超界：{d}"
                assert d.get("evidence"), f"证据链不能为空：{d}"
        assert data.get("decision") in ("通过", "不通过", "待复核"), f"决策值非法：{data.get('decision')}"
        assert data.get("highlights"), "优势亮点不能为空"


class TestJdGenerator:
    """JD 生成结构：核心字段齐全且为列表（下游 markdown 渲染依赖此契约）"""

    def test_JD结构完整(self):
        jd = generate_jd("AI 应用开发工程师（初级）", "RAG 知识库问答产品；Python + LangChain")
        for key in ("title", "duties", "requirements", "salary"):
            assert jd.get(key), f"JD 缺少字段 {key}"
        assert isinstance(jd["duties"], list) and len(jd["duties"]) >= 2
        assert isinstance(jd["requirements"], list) and len(jd["requirements"]) >= 2
