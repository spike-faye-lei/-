"""compare：对比矩阵确定性输出 + LLM 推荐排序渲染"""
import json

import compare
from job_profile import get_profile

PROFILE = get_profile("ai-dev")

ENTRIES = [
    {
        "name": "张三",
        "total": 7.3,
        "decision": "通过",
        "dimension_scores": {"技术能力": 8.0, "项目经验": 7.0, "沟通表达": 7.0, "求职意向": 7.0},
    },
    {
        "name": "李四",
        "total": 5.5,
        "decision": "不通过",
        "dimension_scores": {"技术能力": 5.0, "项目经验": 6.0, "沟通表达": 6.0, "求职意向": 5.0},
    },
]


class TestBuildMatrix:
    def test_表头含全部维度与总分列(self):
        m = compare.build_matrix(ENTRIES, PROFILE)
        assert "| 候选人 | 技术能力 | 项目经验 | 沟通表达 | 求职意向 | 加权总分 | 决策 |" in m

    def test_数值格式正确且确定性(self):
        m1 = compare.build_matrix(ENTRIES, PROFILE)
        m2 = compare.build_matrix(ENTRIES, PROFILE)
        assert m1 == m2
        assert "| 张三 | 8.0 | 7.0 | 7.0 | 7.0 | **7.3** | 通过 |" in m1
        assert "| 李四 | 5.0 | 6.0 | 6.0 | 5.0 | **5.5** | 不通过 |" in m1

    def test_缺维度按0显示(self):
        e = [{"name": "王五", "total": 0.0, "decision": "", "dimension_scores": {}}]
        m = compare.build_matrix(e, PROFILE)
        assert "| 王五 | 0.0 | 0.0 | 0.0 | 0.0 | **0.0** |  |" in m


class TestCompareReport:
    def test_输出含矩阵与推荐排序(self, monkeypatch):
        payload = {
            "ranking": ["张三", "李四"],
            "per_candidate": [
                {"name": "张三", "comment": "技术扎实"},
                {"name": "李四", "comment": "经验不足"},
            ],
            "summary": "张三明显更强，建议优先联系。",
        }

        def fake(messages, **kwargs):
            return json.dumps(payload, ensure_ascii=False)

        monkeypatch.setattr(compare, "chat", fake)
        matrix, summary = compare.compare_report(ENTRIES, PROFILE)
        assert "| 张三 | 8.0" in matrix
        assert "### AI 推荐排序" in summary
        assert "1. **张三** — 技术扎实" in summary
        assert "### 综合评语" in summary
        assert "张三明显更强" in summary

    def test_LLM缺少ranking时回退候选人顺序(self, monkeypatch):
        payload = {"ranking": [], "per_candidate": [], "summary": "无"}

        def fake(messages, **kwargs):
            return json.dumps(payload, ensure_ascii=False)

        monkeypatch.setattr(compare, "chat", fake)
        _, summary = compare.compare_report(ENTRIES, PROFILE)
        assert "1. **张三**" in summary
        assert "2. **李四**" in summary
