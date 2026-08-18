"""webhook 入口 / 外部通知渠道 / 数据源接口 / 评分卡（全部 mock，不真实外呼）"""
import json

import db
import webhook
from data_source import SOURCES, LocalFileSource, get_source
from handlers import score_card_markdown, refresh_scorecard_dropdown


class TestWebhook:
    def test_简历入库与解析(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "t.db"))
        db.init_db()
        monkeypatch.setattr(webhook, "notify", lambda *a, **k: "（模拟）")
        payload = {"candidate_name": "外部候选人", "resume_text": "王五，男，27岁，本科，3年Python大模型经验", "source": "钉钉审批流"}
        res = webhook.on_resume_uploaded(payload)
        assert res["status"] == "accepted" and res["candidate_id"] >= 1
        row = db.get_candidate(res["candidate_id"])
        assert row["status"] == "已解析" and row["auth_source"] == "平台接口·授权"

    def test_空简历拒绝(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "t2.db"))
        db.init_db()
        monkeypatch.setattr(webhook, "notify", lambda *a, **k: "")
        assert webhook.on_resume_uploaded({})["status"] == "error"
        assert webhook.on_resume_uploaded({"resume_text": "  "})["status"] == "error"


class TestNotifyChannels:
    def test_未配置webhook降级本地日志(self, monkeypatch):
        import notify_channels
        monkeypatch.setattr(notify_channels, "_load_dotenv_fresh", lambda: None)
        monkeypatch.setattr(notify_channels, "CHANNEL_HOOKS", {"钉钉": "", "飞书": "", "企业微信": ""})
        result = notify_channels.notify("钉钉", "测试消息")
        assert "模拟发送" in result

    def test_已配置webhook真实推送(self, monkeypatch):
        import notify_channels

        def fake_send(url, content):
            assert "测试消息" in content
            return True

        monkeypatch.setattr(notify_channels, "_load_dotenv_fresh", lambda: None)
        monkeypatch.setattr(notify_channels, "CHANNEL_HOOKS", {"钉钉": "http://fake-hook"})
        monkeypatch.setattr(notify_channels, "_SENDERS", {"钉钉": fake_send, "飞书": fake_send, "企业微信": fake_send})
        result = notify_channels.notify("钉钉", "测试消息")
        assert "已推送" in result

    def test_消息文案(self):
        import notify_channels
        msg = notify_channels.interview_done_message("张三", 78.5, "通过", "AI 应用开发工程师")
        assert "张三" in msg and "78.5" in msg and "审核" in msg


class TestDataSource:
    def test_来源列表含平台适配位(self):
        assert "本地文件夹" in SOURCES
        assert any("BOSS" in s for s in SOURCES)

    def test_本地文件夹源(self, tmp_path):
        (tmp_path / "a.txt").write_text("张伟，男，28岁，本科，2年Python经验", encoding="utf-8")
        src = LocalFileSource(str(tmp_path))
        rows = src.fetch_new_resumes()
        assert len(rows) == 1 and rows[0]["name"] == "张伟"

    def test_平台适配位未接入时明确报错(self):
        src = get_source("BOSS直聘（API 适配位）")
        import pytest
        with pytest.raises(NotImplementedError):
            src.fetch_new_resumes(None)


class TestScoreCard:
    def test_评分卡展示与落库(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "t3.db"))
        db.init_db()
        cid = db.add_candidate("张三", "简历", parsed={"years": 3})
        db.save_score_card(cid, "张三", "AI 应用开发工程师", 69.9, "综合 69.9 分",
                           {"硬门槛": {"status": "通过", "detail": "学历本科达标"},
                            "规则层(60%)": {"score": 89.3, "detail": "命中率×60+学历×20+年限×20"},
                            "语义匹配层(30%)": {"score": 44.3, "detail": "TF-IDF 余弦 0.443"},
                            "加分层(10%)": {"score": 30.0, "detail": "腾讯"}},
                           ["技术能力：3年LangChain开发经验"])
        md = score_card_markdown(cid)
        assert "张三" in md and "69.9" in md and "规则层(60%)" in md and "LangChain" in md
        assert "人工复核" in md
        choices = refresh_scorecard_dropdown()["choices"]
        assert len(choices) == 1

    def test_无评分卡提示(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "t4.db"))
        db.init_db()
        assert "暂无评分卡" in score_card_markdown(999)


class TestResumeInterview:
    def test_会话状态序列化与恢复(self):
        from interviewer import InterviewSession
        from job_profile import get_profile
        p = get_profile("ai-dev")
        s = InterviewSession({"name": "张三", "skills": [], "projects": []}, p)
        s.round = 3
        s.difficulty = 1
        s.covered_dims.add("技术能力")
        s.history = [{"role": "assistant", "content": "问题1"}]
        state = s.to_state()
        s2 = InterviewSession.from_state(state, {"name": "张三", "skills": [], "projects": []}, p)
        assert s2.round == 3 and s2.difficulty == 1
        assert s2.covered_dims == {"技术能力"} and s2.history[0]["content"] == "问题1"

    def test_断点续面落盘与恢复(self, tmp_path, monkeypatch):
        import db as d
        monkeypatch.setattr(d, "DB_PATH", str(tmp_path / "t5.db"))
        d.init_db()
        iid = d.save_interview("张三", "测试", "AI 应用开发工程师", "技术深挖", "面试中", None, "", [], "")
        d.save_session_state(iid, {"round": 2, "difficulty": 0, "history": [{"role": "assistant", "content": "你做过什么项目？"}]})
        prev = d.find_unfinished_interview("张三", "AI 应用开发工程师")
        assert prev and prev["id"] == iid
        state = d.load_session_state(iid)
        assert state["round"] == 2
        # 完成后 session_state 清空且不再命中未完成
        d.update_interview_result(iid, "待HR审核", 8.0, state["history"], "报告")
        assert d.load_session_state(iid) is None
        assert d.find_unfinished_interview("张三", "AI 应用开发工程师") is None

    def test_hr_decision_webhook(self, tmp_path, monkeypatch):
        import db as d
        monkeypatch.setattr(d, "DB_PATH", str(tmp_path / "t6.db"))
        d.init_db()
        monkeypatch.setattr(webhook, "notify", lambda *a, **k: "")
        import handlers as h
        monkeypatch.setattr(h, "add_hr_feedback", lambda *a, **k: None)
        monkeypatch.setattr(h, "_link_candidate_flow", lambda *a, **k: None)
        monkeypatch.setattr(h, "mark_notification_sent", lambda *a, **k: None)
        iid = d.save_interview("张三", "测试", "AI 应用开发工程师", "技术深挖", "待HR审核", 8.0, "", [], "报告")
        res = webhook.on_hr_decision({"interview_id": iid, "decision": "通过", "comment": "技术扎实"})
        assert res["status"] == "accepted"
        assert d.get_interview(iid)["decision"] == "通过"
        assert webhook.on_hr_decision({"interview_id": 999, "decision": "通过"})["status"] == "error"

    def test_数据删除webhook(self, tmp_path, monkeypatch):
        import db as d
        monkeypatch.setattr(d, "DB_PATH", str(tmp_path / "t7.db"))
        d.init_db()
        cid = d.add_candidate("李四", "简历内容", source="测试")
        d.save_score_card(cid, "李四", "AI岗", 70.0, "通过", {}, [])
        res = webhook.on_data_deletion({"candidate_id": cid})
        assert res["status"] == "accepted" and res["deleted_records"] >= 2
        assert d.get_candidate(cid) is None
