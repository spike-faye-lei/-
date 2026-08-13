"""SQLite 持久化：面试记录入库，历史可回看（演示后数据不丢，重启仍可查）"""
import json
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "recruit.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate TEXT NOT NULL,
                source TEXT,
                job TEXT,
                style TEXT,
                decision TEXT,
                score REAL,
                hr_comment TEXT,
                created_at TEXT,
                chat TEXT,
                report TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hr_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision TEXT,
                comment TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS screenings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate TEXT NOT NULL,
                source TEXT,
                job TEXT,
                scores TEXT,
                total REAL,
                decision TEXT,
                hr_decision TEXT,
                hr_comment TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS batch_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT,
                name TEXT,
                job TEXT,
                total REAL,
                decision TEXT,
                scores TEXT,
                created_at TEXT
            )
            """
        )
        # 老库迁移：补列（已存在则跳过）
        for table, cols in {
            "interviews": ("invite", "invite_status"),
            "hr_feedback": ("job",),
            "screenings": ("resume",),
        }.items():
            for col in cols:
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
                except sqlite3.OperationalError:
                    pass


def add_hr_feedback_row(decision, comment, job=""):
    """HR 审核反馈入库（校准闭环持久化，重启不丢，按岗位隔离）"""
    with _conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS hr_feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, decision TEXT, comment TEXT, job TEXT, created_at TEXT)"
        )
        conn.execute(
            "INSERT INTO hr_feedback (decision, comment, job, created_at) VALUES (?,?,?,?)",
            (decision, comment, job, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )


def load_hr_feedback(limit=60):
    """读取最近的 HR 反馈（旧→新，与内存 append 顺序一致），表不存在时返回空列表（启动兜底）

    DESC 取最近 limit 条再反转——修复老实现 ASC LIMIT 取到最早记录的 bug。
    """
    with _conn() as conn:
        try:
            rows = conn.execute(
                "SELECT decision, comment, job FROM hr_feedback ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [
            {"decision": r["decision"], "comment": r["comment"], "job": r["job"] or ""}
            for r in reversed(rows)
        ]


def save_interview(candidate, source, job, style, decision, score, hr_comment, chat_history, report_md):
    """存档面试记录，返回记录 id（邀约发送状态回写用）"""
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO interviews (candidate, source, job, style, decision, score, hr_comment, created_at, chat, report) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                candidate,
                source,
                job,
                style,
                decision,
                score,
                hr_comment,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                json.dumps(chat_history, ensure_ascii=False),
                report_md,
            ),
        )
        return cur.lastrowid


def set_invite(iid, invite_text, status="已发送"):
    """回写邀约文本与发送状态"""
    with _conn() as conn:
        conn.execute(
            "UPDATE interviews SET invite=?, invite_status=? WHERE id=?",
            (invite_text, status, iid),
        )


def update_interview_hr(iid, decision, hr_comment):
    """HR 审核结论回写已有面试记录（自动面试先按「待HR审核」入库，审核时更新而不是新建）"""
    with _conn() as conn:
        conn.execute(
            "UPDATE interviews SET decision=?, hr_comment=? WHERE id=?",
            (decision, hr_comment, iid),
        )


def get_stats():
    """招聘数据看板统计：累计面试/通过率/平均分/岗位分布/邀约发送数"""
    with _conn() as conn:
        decided = conn.execute(
            "SELECT COUNT(*) FROM interviews WHERE decision IN ('通过','驳回')"
        ).fetchone()[0]
        passed = conn.execute(
            "SELECT COUNT(*) FROM interviews WHERE decision='通过'"
        ).fetchone()[0]
        avg = conn.execute(
            "SELECT AVG(score) FROM interviews WHERE score IS NOT NULL"
        ).fetchone()[0]
        jobs = conn.execute(
            "SELECT job, COUNT(*) AS cnt FROM interviews GROUP BY job ORDER BY cnt DESC"
        ).fetchall()
        invited = conn.execute(
            "SELECT COUNT(*) FROM interviews WHERE invite_status IS NOT NULL"
        ).fetchone()[0]
        screened = conn.execute(
            "SELECT COUNT(*) FROM screenings"
        ).fetchone()[0]
        return {
            "total": decided,
            "passed": passed,
            "pass_rate": round(passed / decided * 100, 1) if decided else 0,
            "avg_score": round(avg, 1) if avg else None,
            "jobs": [(r["job"], r["cnt"]) for r in jobs],
            "invited": invited,
            "screened": screened,
        }


def list_interviews():
    """最近记录列表：id + 摘要"""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, candidate, job, decision, score, created_at FROM interviews ORDER BY id DESC LIMIT 50"
        ).fetchall()
        return [dict(r) for r in rows]


def get_interview(iid):
    """按 id 查面试记录；Gradio 下拉可能传 list/tuple，统一归一化（防 sqlite 绑定报错）"""
    if isinstance(iid, (list, tuple)):
        iid = iid[0] if iid else None
    try:
        iid = int(iid)
    except (TypeError, ValueError):
        return None
    with _conn() as conn:
        r = conn.execute("SELECT * FROM interviews WHERE id=?", (iid,)).fetchone()
        return dict(r) if r else None


def list_pending():
    """待 HR 审核的面试记录（自动面试后按「待HR审核」入库，在此排队人工审核）"""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, candidate, job, score, created_at FROM interviews "
            "WHERE decision='待HR审核' ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_hr_decision(candidate, job):
    """某候选人同岗位的最新 HR 最终结论（通过/驳回），没有则返回 None"""
    with _conn() as conn:
        r = conn.execute(
            "SELECT decision FROM interviews WHERE candidate=? AND job=? AND decision IN ('通过','驳回') "
            "ORDER BY id DESC LIMIT 1",
            (candidate, job),
        ).fetchone()
        return r["decision"] if r else None


def screening_in_queue(candidate, job):
    """该候选人是否已在「进入面试队列」状态（防重复勾选产生重复面试）"""
    with _conn() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM screenings WHERE candidate=? AND job=? AND hr_decision='进入面试队列'",
            (candidate, job),
        ).fetchone()[0]
        return n > 0


def save_screening(candidate, source, job, scores, total, decision, resume_text="", hr_decision="", hr_comment=""):
    """批量初筛结果入库（scores 为维度分 dict，resume 原文留档供面试队列复用），返回记录 id"""
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO screenings (candidate, source, job, scores, total, decision, resume, hr_decision, hr_comment, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                candidate,
                source,
                job,
                json.dumps(scores, ensure_ascii=False),
                total,
                decision,
                resume_text,
                hr_decision,
                hr_comment,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        return cur.lastrowid


def update_screening_hr(sid, hr_decision, hr_comment=""):
    """人工复核结果回写（进入面试队列 / 淘汰 / 已面试）"""
    with _conn() as conn:
        conn.execute(
            "UPDATE screenings SET hr_decision=?, hr_comment=? WHERE id=?",
            (hr_decision, hr_comment, sid),
        )


def list_screening_queue():
    """取 HR 已复核通过、等待面试的候选人（面试队列持久化：刷新/重启不丢）"""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, candidate, source, job, total, resume FROM screenings "
            "WHERE hr_decision='进入面试队列' AND resume IS NOT NULL AND resume != '' "
            "ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def list_screenings(limit=50):
    """批量初筛记录列表（新→旧）"""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, candidate, job, total, decision, hr_decision, created_at FROM screenings ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_screening(sid):
    with _conn() as conn:
        r = conn.execute("SELECT * FROM screenings WHERE id=?", (sid,)).fetchone()
        return dict(r) if r else None


def add_batch_report(batch_id, name, job, total, decision, scores):
    """一批面试中每个候选人的结构化结果（维度分 JSON），供横向对比复用"""
    with _conn() as conn:
        conn.execute(
            "INSERT INTO batch_reports (batch_id, name, job, total, decision, scores, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (batch_id, name, job, total, decision, json.dumps(scores, ensure_ascii=False),
             datetime.now().strftime("%Y-%m-%d %H:%M")),
        )


def list_batches(limit=10):
    """面试批次列表（batch_id + 人数 + 时间），新→旧"""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT batch_id, COUNT(*) AS cnt, MIN(created_at) AS created_at "
            "FROM batch_reports GROUP BY batch_id ORDER BY MAX(id) DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_batch(batch_id):
    """取一批面试的全部结构化结果"""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT name, job, total, decision, scores FROM batch_reports WHERE batch_id=? ORDER BY total DESC",
            (batch_id,),
        ).fetchall()
        return [dict(r) for r in rows]
