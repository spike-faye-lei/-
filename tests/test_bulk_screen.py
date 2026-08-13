"""bulk_screen：单份评分（加权分代码计算/钳制/缺失维度按0）+ 批量 generator（降序/错误不中断）"""
import json

import bulk_screen
from job_profile import get_profile

PROFILE = get_profile("ai-dev")  # 技术能力40 / 项目经验30 / 沟通表达20 / 求职意向10


def _fake_chat(payload, monkeypatch):
    """把 config.chat 换成返回指定 payload 的假函数（bulk_screen 内部引用的是模块属性）"""
    def fake(messages, **kwargs):
        return json.dumps(payload, ensure_ascii=False)
    monkeypatch.setattr(bulk_screen, "chat", fake)


class TestScreenResume:
    def test_加权总分代码计算(self, monkeypatch):
        payload = {
            "dimension_scores": {
                "技术能力": {"score": 8, "evidence": "简历提到 LangChain"},
                "项目经验": {"score": 6, "evidence": "独立负责检索链路"},
                "沟通表达": {"score": 7, "evidence": "表述清晰"},
                "求职意向": {"score": 9, "evidence": "期望薪资匹配"},
            },
            "highlights": [], "risks": [], "decision": "建议进入面试", "comment": "ok",
        }
        _fake_chat(payload, monkeypatch)
        r = bulk_screen.screen_resume("李强简历……", PROFILE)
        # (8*40 + 6*30 + 7*20 + 9*10) / 100 = 7.3
        assert r["total"] == 7.3
        assert r["dimension_scores"]["技术能力"] == 8.0

    def test_缺失维度按0计拉低总分(self, monkeypatch):
        payload = {
            "dimension_scores": {
                "技术能力": {"score": 8, "evidence": "x"},
                "项目经验": {"score": 6, "evidence": "x"},
                "沟通表达": {"score": 7, "evidence": "x"},
                # 求职意向缺失
            },
            "decision": "建议进入面试", "comment": "ok",
        }
        _fake_chat(payload, monkeypatch)
        r = bulk_screen.screen_resume("简历……", PROFILE)
        # (8*40 + 6*30 + 7*20 + 0*10) / 100 = 6.4（权重计入分母）
        assert r["total"] == 6.4

    def test_分数钳制与非法值(self, monkeypatch):
        payload = {
            "dimension_scores": {
                "技术能力": {"score": 15, "evidence": "x"},   # 钳到 10
                "项目经验": {"score": "abc", "evidence": "x"},  # 非法 -> 0
                "沟通表达": {"score": -2, "evidence": "x"},    # 钳到 0
                "求职意向": {"score": 5, "evidence": "x"},
            },
            "decision": "建议淘汰", "comment": "ok",
        }
        _fake_chat(payload, monkeypatch)
        r = bulk_screen.screen_resume("简历……", PROFILE)
        # (10*40 + 0*30 + 0*20 + 5*10) / 100 = 4.5
        assert r["total"] == 4.5

    def test_代码块包裹的响应也能解析(self, monkeypatch):
        payload = {
            "dimension_scores": {d["name"]: {"score": 5, "evidence": "x"} for d in PROFILE["dimensions"]},
            "decision": "建议进入面试", "comment": "ok",
        }
        def fake(messages, **kwargs):
            return "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"
        monkeypatch.setattr(bulk_screen, "chat", fake)
        r = bulk_screen.screen_resume("简历……", PROFILE)
        assert r["total"] == 5.0


class TestScreenBatch:
    def _make_fake(self, monkeypatch, first_payload):
        """第一份成功、第二份抛异常，验证不中断整批"""
        calls = {"n": 0}

        def fake(messages, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("网络错误")
            return json.dumps(first_payload, ensure_ascii=False)

        monkeypatch.setattr(bulk_screen, "chat", fake)

    def test_逐份yield且错误不中断(self, monkeypatch):
        payload = {
            "dimension_scores": {d["name"]: {"score": 8, "evidence": "x"} for d in PROFILE["dimensions"]},
            "decision": "建议进入面试", "comment": "ok",
        }
        self._make_fake(monkeypatch, payload)
        resumes = [("甲", "上传文件", "简历甲"), ("乙", "上传文件", "简历乙")]
        yields = list(bulk_screen.screen_batch(resumes, PROFILE))
        # 第一次 yield：1 份完成
        assert yields[0][0] == 1 and yields[0][1] == 2
        assert yields[0][2][0]["name"] == "甲" and yields[0][2][0]["total"] == 8.0
        # 第二次 yield：2 份完成，乙失败 total=-1 排末尾
        assert yields[1][0] == 2 and yields[1][1] == 2
        assert yields[1][2][0]["name"] == "甲"
        assert yields[1][2][1]["name"] == "乙" and yields[1][2][1]["total"] == -1.0

    def test_按总分降序(self, monkeypatch):
        results = {"甲": 6.0, "乙": 9.0, "丙": 3.0}
        calls = {"n": 0}

        def fake(messages, **kwargs):
            calls["n"] += 1
            name = ["甲", "乙", "丙"][calls["n"] - 1]
            payload = {
                "dimension_scores": {d["name"]: {"score": results[name], "evidence": "x"} for d in PROFILE["dimensions"]},
                "decision": "建议进入面试", "comment": "ok",
            }
            return json.dumps(payload, ensure_ascii=False)

        monkeypatch.setattr(bulk_screen, "chat", fake)
        resumes = [("甲", "s", "a"), ("乙", "s", "b"), ("丙", "s", "c")]
        yields = list(bulk_screen.screen_batch(resumes, PROFILE))
        final = yields[-1][2]
        assert [r["name"] for r in final] == ["乙", "甲", "丙"]

    def test_空列表不产出(self, monkeypatch):
        assert list(bulk_screen.screen_batch([], PROFILE)) == []
