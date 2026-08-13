"""handlers 层单测（全 mock，不调真实 API / DB / 网络）

覆盖重构后 handlers.py 中未被原测试覆盖的部分：
聊天历史转 markdown、队列展示、通知提取、对比条目、记录详情与待审核、
HR 审核闸门、批量初筛收集/评分/勾选、JD/题库错误路径、数据看板等。
"""
import types
from unittest.mock import Mock

import pytest

import handlers
from handlers import (
    _collect_resumes,
    _entry_from_session,
    _extract_invite,
    confirm_invite,
    empty_radar_figure,
    history_to_markdown,
    hr_review,
    load_pending,
    load_queue_from_db,
    queue_markdown,
    refresh_pending,
    refresh_records,
    restore_queue,
    run_bulk_screen,
    run_jd_gen,
    run_question_gen,
    search_candidate,
    send_to_queue,
    show_record,
    stats_markdown,
    submit_pending,
)
from job_profile import get_profile


def _session(report=None, interview_id=None):
    """构造与 handlers 交互的面试会话替身"""
    return types.SimpleNamespace(
        resume={"name": "张三"},
        profile={"job": "AI 应用开发工程师"},
        style={"name": "技术深挖"},
        report=report,
        interview_id=interview_id,
    )


class TestHistoryToMarkdown:
    def test_正常转换且剥离角色前缀(self):
        md = history_to_markdown([
            {"role": "assistant", "content": "**【AI 招聘官】** → 张三\n\n你好"},
            {"role": "user", "content": "**张三（候选人 AI）：**\n\n我在"},
        ])
        assert "**AI 招聘官：** 你好" in md
        assert "**候选人：** 我在" in md
        assert "→ 张三" not in md

    def test_空历史给出占位(self):
        assert history_to_markdown([]) == "（暂无对话）"


class TestQueueMarkdown:
    def test_空队列(self):
        assert "空" in queue_markdown([])

    def test_含候选人且剥离txt后缀(self):
        md = queue_markdown([{"name": "张三.txt", "total": 8.0}])
        assert "张三" in md and "张三.txt" not in md and "8" in md


class TestExtractInvite:
    def test_从报告提取邀请文本(self):
        report = "**下一步（待 HR 审核确认后发送）：** 欢迎来面试\n**总评：** 不错"
        assert _extract_invite(report) == "欢迎来面试"

    def test_无匹配返回空(self):
        assert _extract_invite("没有邀请") == ""


class TestEntryFromSession:
    def test_无报告返回None(self):
        assert _entry_from_session("张三", _session(report=None)) is None

    def test_有报告提取条目(self):
        entry = _entry_from_session("张三", _session(report={"total": 8.0, "decision": "通过", "dimension_scores": {"技术能力": 8}}))
        assert entry == {"name": "张三", "total": 8.0, "decision": "通过", "dimension_scores": {"技术能力": 8}}


class TestRefreshPending:
    def test_选择项格式(self, monkeypatch):
        monkeypatch.setattr(handlers, "list_pending", lambda: [{"id": 3, "candidate": "张三", "job": "AI岗", "score": 8.0}])
        assert refresh_pending() == [("#3 张三 · AI岗 · 8.0分", 3)]


class TestRefreshRecords:
    def test_空库提示(self, monkeypatch):
        monkeypatch.setattr(handlers, "list_interviews", lambda: [])
        choices, msg = refresh_records()
        assert choices == [] and "暂无面试记录" in msg

    def test_有记录返回选择项与计数(self, monkeypatch):
        monkeypatch.setattr(handlers, "list_interviews", lambda: [
            {"created_at": "2026-08-13 21:00", "candidate": "张三", "job": "AI岗", "decision": "通过", "score": 8.0, "id": 1}
        ])
        choices, msg = refresh_records()
        assert len(choices) == 1 and choices[0][1] == 1 and "共 1 条记录" in msg


class TestShowRecord:
    def test_不存在的记录(self, monkeypatch):
        monkeypatch.setattr(handlers, "get_interview", lambda i: None)
        assert show_record(1) == "记录不存在"

    def test_正常渲染记录详情(self, monkeypatch):
        monkeypatch.setattr(handlers, "get_interview", lambda i: {
            "id": 1, "candidate": "张三", "created_at": "2026-08-13", "job": "AI岗",
            "style": "技术深挖", "decision": "通过", "score": 8.0, "source": "内置",
            "hr_comment": "", "chat": '[{"role": "assistant", "content": "你好"}]', "report": "报告",
        })
        md = show_record(1)
        assert "张三" in md and "报告" in md

    def test_非法JSON对话不崩(self, monkeypatch):
        monkeypatch.setattr(handlers, "get_interview", lambda i: {
            "id": 1, "candidate": "张三", "created_at": "x", "job": "AI岗", "style": "s",
            "decision": "通过", "score": 8.0, "source": "s", "hr_comment": "", "chat": "not-json", "report": "",
        })
        assert "张三" in show_record(1)


class TestLoadPending:
    def test_载入待审核记录构造状态(self, monkeypatch):
        monkeypatch.setattr(handlers, "get_interview", lambda i: {
            "id": 1, "candidate": "张三", "job": "AI岗",
            "report": "**下一步（待 HR 审核确认后发送）：** 欢迎来面试",
        })
        monkeypatch.setattr(handlers, "show_record", lambda i: "详情")
        detail, invite, state, status = load_pending(1)
        assert detail == "详情" and invite == "欢迎来面试"
        assert state == {"iid": 1, "candidate": "张三", "job": "AI岗"}
        assert "张三" in status

    def test_未选择给出提示(self):
        detail, invite, state, status = load_pending(None)
        assert invite == "" and state is None and "请先选择" in status


class TestSubmitPending:
    def test_通过回写结论与反馈(self, monkeypatch):
        calls = []
        monkeypatch.setattr(handlers, "update_interview_hr", lambda *a: calls.append(a))
        monkeypatch.setattr(handlers, "add_hr_feedback", lambda *a: calls.append(a))
        state = {"iid": 1, "candidate": "张三", "job": "AI岗"}
        _, new_state, pending, status = submit_pending("通过（进入线下面试）", "不错", "邀约文本", state)
        assert new_state["verdict"] == "通过" and pending is None
        assert len(calls) == 2 and "审核完成" in status

    def test_驳回路径(self, monkeypatch):
        monkeypatch.setattr(handlers, "update_interview_hr", lambda *a: None)
        monkeypatch.setattr(handlers, "add_hr_feedback", lambda *a: None)
        _, new_state, _, status = submit_pending("驳回", "", "文本", {"iid": 1, "candidate": "张三", "job": "AI岗"})
        assert new_state["verdict"] == "驳回" and "婉拒通知" in status


class TestConfirmInvite:
    def test_无待发送通知(self):
        _, _, _, _, state, status = confirm_invite("文本", [], None, None, None)
        assert state is None and "没有待发送" in status

    def test_空文本拦截(self):
        _, _, _, _, state, status = confirm_invite("", [], None, None, {"iid": 1, "verdict": "通过", "candidate": "张三"})
        assert state is not None and "文本为空" in status

    def test_确认发送回写存档(self, monkeypatch):
        sent = []
        monkeypatch.setattr(handlers, "set_invite", lambda iid, text: sent.append((iid, text)))
        history, _, _, _, state, status = confirm_invite(" 欢迎来面试 ", [], None, None, {"iid": 7, "verdict": "通过", "candidate": "张三"})
        assert sent == [(7, "欢迎来面试")] and state is None and "已确认发送" in status


class TestHrReview:
    def test_无报告拦截(self):
        _, _, _, invite, pending, status = hr_review("通过", "", [], _session(report=None), None)
        assert invite == "" and pending is None and "请先完成面试" in status

    def test_手动模式通过入库(self, monkeypatch):
        saved = []
        monkeypatch.setattr(handlers, "add_hr_feedback", lambda *a: None)
        monkeypatch.setattr(handlers, "save_interview", lambda *a: saved.append(a) or 42)
        _, session, _, invite, pending, status = hr_review(
            "通过（进入线下面试）", "不错", [], _session(report={"invite": "欢迎", "total": 8.0}), None
        )
        assert len(saved) == 1 and pending == {"iid": 42, "verdict": "通过", "candidate": "张三"}
        assert session.report is None and "审核完成" in status

    def test_驳回路径(self, monkeypatch):
        monkeypatch.setattr(handlers, "add_hr_feedback", lambda *a: None)
        monkeypatch.setattr(handlers, "save_interview", lambda *a: 9)
        _, _, _, _, pending, _ = hr_review("驳回", "", [], _session(report={"invite": "婉拒", "total": 4.0}), None)
        assert pending["verdict"] == "驳回"

    def test_自动面试记录回写不新建(self, monkeypatch):
        updated = []
        monkeypatch.setattr(handlers, "add_hr_feedback", lambda *a: None)
        monkeypatch.setattr(handlers, "update_interview_hr", lambda *a: updated.append(a))
        monkeypatch.setattr(handlers, "save_interview", lambda *a: pytest.fail("不应新建记录"))
        _, _, _, _, pending, _ = hr_review("通过", "", [], _session(report={"invite": "欢迎"}, interview_id=7), None)
        assert updated and pending["iid"] == 7


class TestCollectResumes:
    def test_粘贴多份分割与文件解析(self, monkeypatch):
        def fake_extract(name):
            if name == "bad.txt":
                raise OSError("boom")
            return "文件简历内容"
        monkeypatch.setattr(handlers, "extract_text", fake_extract)
        files = [types.SimpleNamespace(name="good.txt"), types.SimpleNamespace(name="bad.txt")]
        resumes = _collect_resumes(files, "张三\n张三的简历\n===\n李四\n李四的简历")
        assert [r[0] for r in resumes] == ["good.txt", "张三", "李四"]
        assert resumes[0][1] == "上传文件" and resumes[1][1] == "粘贴文本"


class TestRunBulkScreen:
    def test_空输入提示(self):
        gen = run_bulk_screen(None, "", "ai-dev", progress=types.SimpleNamespace())
        rows, state, check, note = next(gen)
        assert rows is None and state is None and "请上传" in note

    def test_评分后输出排序结果表(self, monkeypatch):
        def fake_screen_batch(resumes, profile):
            yield 1, 1, [{
                "name": "张三", "total": 8.0, "decision": "通过", "comment": "不错",
                "dimension_scores": {"技术能力": 8.0},
            }]
        monkeypatch.setattr(handlers, "screen_batch", fake_screen_batch)
        gen = run_bulk_screen(None, "张三\n简历", "ai-dev", progress=Mock())
        *_, last = list(gen)
        rows, state, check, note = last
        assert rows[0][1] == "张三" and rows[0][2] == 8.0
        assert list(state["by_label"].keys()) and "人工复核" in note


class TestSendToQueue:
    def test_无初筛状态提示(self):
        queue, note, _ = send_to_queue([], None)
        assert queue == [] and "请先运行批量初筛" in note

    def test_未勾选提示人工复核必须(self):
        state = {"profile_id": "ai-dev", "by_label": {"lbl": {}}}
        queue, note, _ = send_to_queue([], state)
        assert "人工复核是必须环节" in note

    def test_勾选后落库并重建队列(self, monkeypatch):
        saved = []
        monkeypatch.setattr(handlers, "screening_in_queue", lambda *a: False)
        monkeypatch.setattr(handlers, "save_screening", lambda *a, **k: saved.append(a) or 5)
        monkeypatch.setattr(handlers, "update_screening_hr", lambda *a: None)
        monkeypatch.setattr(handlers, "load_queue_from_db", lambda: [{"screening_id": 5, "name": "张三", "source": "", "resume_text": "", "total": 8.0}])
        state = {"profile_id": "ai-dev", "by_label": {"lbl": {"name": "张三", "source": "粘贴", "total": 8.0, "decision": "通过", "resume_text": "简历"}}}
        queue, note, _ = send_to_queue(["lbl"], state)
        assert len(saved) == 1 and len(queue) == 1 and "HR 复核结论已存档" in note


class TestQueueFromDb:
    def test_重建队列结构(self, monkeypatch):
        monkeypatch.setattr(handlers, "list_screening_queue", lambda: [
            {"id": 1, "candidate": "张三", "source": "s", "resume": "r", "total": 8.0}
        ])
        queue = load_queue_from_db()
        assert queue == [{"screening_id": 1, "name": "张三", "source": "s", "resume_text": "r", "total": 8.0}]

    def test_restore返回队列与展示(self, monkeypatch):
        monkeypatch.setattr(handlers, "load_queue_from_db", lambda: [{"screening_id": 1, "name": "张三", "total": 8.0}])
        queue, md = restore_queue()
        assert len(queue) == 1 and "张三" in md


class TestSearchCandidate:
    def test_选中候选人返回简历(self):
        label = handlers.CANDIDATES[0]["label"]
        text, _, status = search_candidate(label, [], None)
        assert text == handlers.CANDIDATES[0]["resume"] and "已从" in status

    def test_未选中提示(self):
        assert search_candidate(None, [], None)[0] is None


class TestJdAndQuestions:
    def test_JD为空岗位名提示(self):
        assert run_jd_gen("", None) == "请先填写岗位名称"

    def test_JD生成成功拼接rubric(self, monkeypatch):
        monkeypatch.setattr(handlers, "generate_jd", lambda r, n: {"title": "X"})
        monkeypatch.setattr(handlers, "jd_to_markdown", lambda jd: "### JD")
        monkeypatch.setattr(handlers, "match_rubric_markdown", lambda jd: "### 岗位配置匹配")
        md = run_jd_gen("AI工程师", "要点")
        assert "### JD" in md and "### 岗位配置匹配" in md

    def test_JD异常给出错误提示(self, monkeypatch):
        monkeypatch.setattr(handlers, "generate_jd", lambda r, n: (_ for _ in ()).throw(RuntimeError("boom")))
        assert "JD 生成失败" in run_jd_gen("AI工程师", "")

    def test_题库生成与异常路径(self, monkeypatch):
        monkeypatch.setattr(handlers, "generate_questions", lambda p, n: "## 面试题库（X）")
        assert "面试题库" in run_question_gen("ai-dev", 3)
        monkeypatch.setattr(handlers, "generate_questions", lambda p, n: (_ for _ in ()).throw(RuntimeError("boom")))
        assert "题库生成失败" in run_question_gen("ai-dev", 3)


class TestStatsMarkdown:
    def test_看板包含全部指标(self, monkeypatch):
        monkeypatch.setattr(handlers, "get_stats", lambda: {
            "total": 5, "passed": 3, "pass_rate": 60.0, "avg_score": 7.5,
            "screened": 10, "invited": 2, "jobs": [("AI应用开发工程师", 5)],
        })
        md = stats_markdown()
        assert "5" in md and "60.0%" in md and "AI应用开发工程师" in md


class TestEmptyRadar:
    def test_占位雷达图可生成(self):
        fig = empty_radar_figure(get_profile("ai-dev"))
        assert fig is not None
