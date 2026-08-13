"""evaluator：证据链评分的保守默认（缺 decision 时待复核而不是通过）+ 加权分代码计算"""
import json

import evaluator
from interviewer import InterviewSession
from job_profile import get_profile

PROFILE = get_profile("ai-dev")
RESUME = {"name": "测试", "education": "本科", "years": 3, "skills": ["Python"], "projects": ["客服系统"], "target_role": "AI 开发"}

PAYLOAD_BASE = {
    "reviewers": {
        "tech": [
            {"name": "技术能力", "score": 7, "evidence": "原话", "reason": "r"},
            {"name": "项目经验", "score": 6, "evidence": "原话", "reason": "r"},
        ],
        "culture": [
            {"name": "沟通表达", "score": 8, "evidence": "原话", "reason": "r"},
            {"name": "求职意向", "score": 9, "evidence": "原话", "reason": "r"},
        ],
    },
    "highlights": ["h"], "risks": [], "invite": "邀约", "comment": "c",
}


def _run_evaluate(monkeypatch, payload):
    def fake(messages, **kwargs):
        return json.dumps(payload, ensure_ascii=False)

    monkeypatch.setattr(evaluator, "chat", fake)
    s = InterviewSession(RESUME, PROFILE)
    s.history = [{"role": "assistant", "content": "你好"}]
    report, _fig = evaluator.evaluate(s, PROFILE)
    return s, report


class TestEvaluateDecision:
    def test_缺decision时默认待复核(self, monkeypatch):
        # PAYLOAD_BASE 本身不含 decision 键 = 模型漏输出决策的场景
        s, report = _run_evaluate(monkeypatch, dict(PAYLOAD_BASE))
        assert s.report["decision"] == "待复核"  # 保守默认，而不是默认通过
        assert "待复核" in report

    def test_有decision时尊重模型输出(self, monkeypatch):
        payload = dict(PAYLOAD_BASE, decision="通过")
        s, _ = _run_evaluate(monkeypatch, payload)
        assert s.report["decision"] == "通过"

    def test_加权总分代码计算(self, monkeypatch):
        s, _ = _run_evaluate(monkeypatch, PAYLOAD_BASE)
        # (7*40 + 6*30 + 8*20 + 9*10) / 100 = 7.1
        assert s.report["total"] == 7.1

    def test_dimension_scores存入report供对比复用(self, monkeypatch):
        s, _ = _run_evaluate(monkeypatch, PAYLOAD_BASE)
        assert s.report["dimension_scores"]["技术能力"] == 7.0

    def test_非法分数不崩报告渲染(self, monkeypatch):
        # 模型返回 "abc"/None 分数：总分能算，进度条渲染也不能抛异常
        payload = {
            "reviewers": {
                "tech": [{"name": "技术能力", "score": "abc", "evidence": "x", "reason": "r"}],
                "culture": [{"name": "沟通表达", "score": None, "evidence": "x", "reason": "r"}],
            },
            "highlights": [], "risks": [], "invite": "邀约", "comment": "c",
            "decision": "不通过",
        }
        s, report = _run_evaluate(monkeypatch, payload)
        assert s.report["total"] == 0.0  # 非法分数按 0 计
        assert "░" * 10 in report  # 进度条正常渲染（int(to_score) 不崩）
