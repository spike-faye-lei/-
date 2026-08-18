"""db：SQLite 全表 CRUD + 统计（tmp_path 隔离，不碰真实 recruit.db）"""
import pytest

import db


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    """每个用例独立数据库文件"""
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    return db


def _save_interview(iso, name="张三", decision="通过", score=8.0):
    return iso.save_interview(name, "测试", "AI 应用开发工程师", "技术深挖", decision, score, "", [], "报告")


class TestInterviews:
    def test_save返回自增id且可回查(self, isolated_db):
        iid = _save_interview(isolated_db)
        assert iid == 1
        r = isolated_db.get_interview(iid)
        assert r["candidate"] == "张三"
        assert r["score"] == 8.0

    def test_set_invite回写发送状态(self, isolated_db):
        iid = _save_interview(isolated_db)
        isolated_db.set_invite(iid, "邀请文本", "已发送")
        r = isolated_db.get_interview(iid)
        assert r["invite"] == "邀请文本"
        assert r["invite_status"] == "已发送"

    def test_list_interviews新在前(self, isolated_db):
        _save_interview(isolated_db, name="甲")
        _save_interview(isolated_db, name="乙")
        names = [r["candidate"] for r in isolated_db.list_interviews()]
        assert names == ["乙", "甲"]


class TestScreenings:
    def test_save与list(self, isolated_db):
        isolated_db.save_screening("甲", "上传文件", "AI 应用开发工程师", {"技术能力": 8.0}, 8.0, "建议进入面试")
        isolated_db.save_screening("乙", "粘贴文本", "AI 应用开发工程师", {}, 3.0, "建议淘汰")
        rows = isolated_db.list_screenings()
        assert len(rows) == 2
        assert rows[0]["candidate"] == "乙"  # 新在前

    def test_update_hr回写复核结果(self, isolated_db):
        isolated_db.save_screening("甲", "s", "j", {}, 8.0, "建议进入面试")
        isolated_db.update_screening_hr(1, "进入面试队列", "技术不错")
        r = isolated_db.get_screening(1)
        assert r["hr_decision"] == "进入面试队列"
        assert r["hr_comment"] == "技术不错"

    def test_scores_JSON序列化中文(self, isolated_db):
        isolated_db.save_screening("甲", "s", "j", {"技术能力": 7.5}, 7.5, "建议进入面试")
        r = isolated_db.get_screening(1)
        import json
        assert json.loads(r["scores"]) == {"技术能力": 7.5}


class TestBatchReports:
    def test_add与get_batch按总分降序(self, isolated_db):
        isolated_db.add_batch_report("b1", "甲", "AI 应用开发工程师", 7.0, "通过", {"技术能力": 7.0})
        isolated_db.add_batch_report("b1", "乙", "AI 应用开发工程师", 9.0, "通过", {"技术能力": 9.0})
        rows = isolated_db.get_batch("b1")
        assert [r["name"] for r in rows] == ["乙", "甲"]

    def test_list_batches聚合(self, isolated_db):
        isolated_db.add_batch_report("b1", "甲", "j", 7.0, "通过", {})
        isolated_db.add_batch_report("b1", "乙", "j", 8.0, "通过", {})
        isolated_db.add_batch_report("b2", "丙", "j", 6.0, "通过", {})
        batches = isolated_db.list_batches()
        assert len(batches) == 2
        assert batches[0]["batch_id"] == "b2"  # 新批次在前
        assert batches[0]["cnt"] == 1
        assert batches[1]["cnt"] == 2


class TestStats:
    def test_统计正确(self, isolated_db):
        _save_interview(isolated_db, name="甲", decision="通过", score=8.0)
        _save_interview(isolated_db, name="乙", decision="驳回", score=6.0)
        _save_interview(isolated_db, name="丙", decision="跳过", score=None)  # 跳过不计入结论
        isolated_db.save_screening("丁", "s", "j", {}, 5.0, "建议淘汰")
        isolated_db.set_invite(1, "邀请", "已发送")
        s = isolated_db.get_stats()
        assert s["total"] == 2
        assert s["passed"] == 1
        assert s["pass_rate"] == 50.0
        assert s["avg_score"] == 7.0
        assert s["screened"] == 1
        assert s["invited"] == 1

    def test_待HR审核不计入结论(self, isolated_db):
        _save_interview(isolated_db, name="甲", decision="待HR审核", score=7.0)
        s = isolated_db.get_stats()
        assert s["total"] == 0  # AI 结论不算最终决策
        assert s["passed"] == 0

    def test_空库不炸(self, isolated_db):
        s = isolated_db.get_stats()
        assert s["total"] == 0
        assert s["pass_rate"] == 0
        assert s["avg_score"] is None


class TestHrFeedbackCalibration:
    def test_load取最近且旧到新(self, isolated_db):
        for d, c, j in [("通过", "A", "岗位1"), ("驳回", "B", "岗位2"), ("通过", "C", "岗位1")]:
            isolated_db.add_hr_feedback_row(d, c, j)
        rows = isolated_db.load_hr_feedback()
        assert [r["comment"] for r in rows] == ["A", "B", "C"]  # 旧→新，最新在最后
        assert rows[-1]["job"] == "岗位1"

    def test_load超过limit只取最近(self, isolated_db):
        for i in range(8):
            isolated_db.add_hr_feedback_row("通过", f"意见{i}", "岗位1")
        rows = isolated_db.load_hr_feedback(limit=3)
        assert [r["comment"] for r in rows] == ["意见5", "意见6", "意见7"]  # 最近 3 条


class TestUpdateInterviewHr:
    def test_回写HR结论而不新建(self, isolated_db):
        iid = _save_interview(isolated_db, decision="待HR审核")
        isolated_db.update_interview_hr(iid, "通过", "HR 复核意见")
        r = isolated_db.get_interview(iid)
        assert r["decision"] == "通过"
        assert r["hr_comment"] == "HR 复核意见"
        assert len(isolated_db.list_interviews()) == 1  # 没有产生重复记录


class TestPendingList:
    def test_只列待HR审核记录(self, isolated_db):
        _save_interview(isolated_db, name="甲", decision="待HR审核")
        _save_interview(isolated_db, name="乙", decision="待HR审核")
        _save_interview(isolated_db, name="丙", decision="通过")
        _save_interview(isolated_db, name="丁", decision="跳过")
        rows = isolated_db.list_pending()
        assert [r["candidate"] for r in rows] == ["甲", "乙"]

    def test_审核后移出待审队列(self, isolated_db):
        iid = _save_interview(isolated_db, name="甲", decision="待HR审核")
        isolated_db.update_interview_hr(iid, "驳回", "经验不足")
        assert isolated_db.list_pending() == []

    def test_get_hr_decision取最新结论(self, isolated_db):
        _save_interview(isolated_db, name="甲", decision="待HR审核")
        iid = _save_interview(isolated_db, name="甲", decision="通过")
        isolated_db.update_interview_hr(iid, "驳回", "改主意")
        assert isolated_db.get_hr_decision("甲", "AI 应用开发工程师") == "驳回"
        assert isolated_db.get_hr_decision("不存在的人", "AI 应用开发工程师") is None


class TestScreeningDedup:
    def test_screening_in_queue防重复(self, isolated_db):
        assert not isolated_db.screening_in_queue("甲", "j")
        sid = isolated_db.save_screening("甲", "s", "j", {}, 8.0, "建议进入面试", resume_text="简历")
        isolated_db.update_screening_hr(sid, "进入面试队列")
        assert isolated_db.screening_in_queue("甲", "j")
        # 同岗位已面试的不算在队列
        isolated_db.update_screening_hr(sid, "已面试")
        assert not isolated_db.screening_in_queue("甲", "j")


class TestScreeningQueue:
    def test_复核落库与队列持久化(self, isolated_db):
        sid = isolated_db.save_screening("甲", "上传文件", "j", {}, 8.0, "建议进入面试", resume_text="简历原文")
        assert sid == 1
        isolated_db.update_screening_hr(sid, "进入面试队列", "HR 复核通过")
        q = isolated_db.list_screening_queue()
        assert len(q) == 1
        assert q[0]["candidate"] == "甲"
        assert q[0]["resume"] == "简历原文"
        r = isolated_db.get_screening(sid)
        assert r["hr_decision"] == "进入面试队列"  # 复核结论真正落库

    def test_已面试的不再出现在队列(self, isolated_db):
        sid = isolated_db.save_screening("甲", "s", "j", {}, 8.0, "建议进入面试", resume_text="简历")
        isolated_db.update_screening_hr(sid, "进入面试队列")
        isolated_db.update_screening_hr(sid, "已面试", "自动面试完成")
        assert isolated_db.list_screening_queue() == []

    def test_未复核的进不了队列(self, isolated_db):
        isolated_db.save_screening("甲", "s", "j", {}, 8.0, "建议进入面试", resume_text="简历")  # hr_decision 为空
        assert isolated_db.list_screening_queue() == []


class TestEnterpriseTables:
    def test_岗位配置保存与读取(self, isolated_db):
        jid = isolated_db.save_job_profile("AI 应用开发工程师", "JD文本", "ai-dev", {"min_years": 2})
        assert jid == 1
        p = isolated_db.get_job_profile(1)
        assert p["title"] == "AI 应用开发工程师"
        import json
        assert json.loads(p["rules"]) == {"min_years": 2}
        assert len(isolated_db.list_job_profiles()) == 1

    def test_候选人状态机流转(self, isolated_db):
        cid = isolated_db.add_candidate("张三", "简历文本", source="测试", parsed={"years": 3})
        assert isolated_db.get_candidate(cid)["status"] == "新入库"
        isolated_db.update_candidate(cid, status="已解析", match_score=0.7, screen_score=8.0)
        r = isolated_db.get_candidate(cid)
        assert r["status"] == "已解析" and r["match_score"] == 0.7 and r["screen_score"] == 8.0
        isolated_db.update_candidate(cid, status="初筛通过")
        assert isolated_db.get_candidate(cid)["status"] == "初筛通过"

    def test_按姓名取最新记录(self, isolated_db):
        isolated_db.add_candidate("张三", "旧简历")
        cid = isolated_db.add_candidate("张三", "新简历")
        assert isolated_db.get_candidate_by_name("张三")["id"] == cid
        assert isolated_db.get_candidate_by_name("不存在") is None

    def test_漏斗统计(self, isolated_db):
        isolated_db.add_candidate("甲", "a")
        isolated_db.add_candidate("乙", "b")
        isolated_db.add_candidate("丙", "c")
        isolated_db.update_candidate(1, status="已解析")
        isolated_db.update_candidate(2, status="已解析")
        isolated_db.update_candidate(3, status="初筛淘汰")
        stats = dict(isolated_db.funnel_stats())
        assert stats["已解析"] == 2 and stats["初筛淘汰"] == 1

    def test_通知与Offer(self, isolated_db):
        nid = isolated_db.save_notification(1, "张三", "面试邀约", "欢迎参加面试")
        assert isolated_db.list_notifications()[0]["status"] == "已生成"
        isolated_db.mark_notification_sent(nid)
        assert isolated_db.list_notifications()[0]["status"] == "已发送"
        isolated_db.save_offer(1, "张三", "AI 应用开发工程师", "25K")
        assert isolated_db.list_offers()[0]["salary"] == "25K"
