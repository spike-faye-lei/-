"""jd_generator：JD 生成与 rubric 匹配 + 题库生成（只含配置内维度）"""
import json

import jd_generator
from job_profile import get_profile

PROFILE = get_profile("ai-dev")


class TestGenerateJd:
    def test_输出完整JD(self, monkeypatch):
        payload = {
            "title": "AI 应用开发工程师",
            "duties": ["负责 RAG 产品开发", "优化检索链路"],
            "requirements": ["本科以上", "熟悉 Python"],
            "plus": ["有向量数据库经验"],
            "salary": "20-35K",
        }

        def fake(messages, **kwargs):
            return json.dumps(payload, ensure_ascii=False)

        monkeypatch.setattr(jd_generator, "chat", fake)
        jd = jd_generator.generate_jd("AI 应用开发工程师", "做 RAG 产品")
        assert jd["title"] == "AI 应用开发工程师"
        assert len(jd["duties"]) == 2

    def test_markdown包含rubric匹配(self, monkeypatch):
        jd = {
            "title": "AI Agent 开发工程师",
            "duties": ["开发大模型 RAG 应用，用 LangChain 构建 Agent"],
            "requirements": ["熟悉 Python 和大模型"],
            "plus": [],
            "salary": "面议",
        }
        md = jd_generator.match_rubric_markdown(jd)
        # duties 含 大模型/RAG/LangChain → 匹配 ai-dev
        assert "AI 应用开发工程师" in md
        assert "评估维度" in md

    def test_空要点也能生成(self, monkeypatch):
        payload = {"title": "X", "duties": [], "requirements": [], "plus": [], "salary": "面议"}

        def fake(messages, **kwargs):
            return json.dumps(payload, ensure_ascii=False)

        monkeypatch.setattr(jd_generator, "chat", fake)
        jd = jd_generator.generate_jd("X", "")
        assert jd["title"] == "X"


class TestGenerateQuestions:
    def test_只保留配置内维度(self, monkeypatch):
        payload = {
            "dimensions": [
                {
                    "dimension": "技术能力",
                    "questions": [
                        {"q": "RAG 的检索链路怎么设计？", "difficulty": "基础", "followup": "追问命中率"},
                        {"q": "向量召回怎么优化？", "difficulty": "进阶", "followup": ""},
                    ],
                },
                {
                    "dimension": "领导力",  # 配置外维度，应被忽略
                    "questions": [{"q": "怎么带团队？", "difficulty": "基础", "followup": ""}],
                },
            ]
        }

        def fake(messages, **kwargs):
            return json.dumps(payload, ensure_ascii=False)

        monkeypatch.setattr(jd_generator, "chat", fake)
        md = jd_generator.generate_questions(PROFILE, per_dim=2)
        assert "### 技术能力" in md
        assert "RAG 的检索链路怎么设计？" in md
        assert "领导力" not in md  # 配置外维度被过滤

    def test_全部维度非法时给出提示(self, monkeypatch):
        payload = {"dimensions": [{"dimension": "领导力", "questions": []}]}

        def fake(messages, **kwargs):
            return json.dumps(payload, ensure_ascii=False)

        monkeypatch.setattr(jd_generator, "chat", fake)
        md = jd_generator.generate_questions(PROFILE, per_dim=1)
        assert "题库生成失败" in md
