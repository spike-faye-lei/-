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


def add_hr_feedback_row(decision, comment):
    """HR 审核反馈入库（校准闭环持久化，重启不丢）"""
    with _conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS hr_feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, decision TEXT, comment TEXT, created_at TEXT)"
        )
        conn.execute(
            "INSERT INTO hr_feedback (decision, comment, created_at) VALUES (?,?,?)",
            (decision, comment, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )


def load_hr_feedback(limit=6):
    """读取最近的 HR 反馈（旧→新，与内存 append 顺序一致），表不存在时返回空列表（启动兜底）"""
    with _conn() as conn:
        try:
            rows = conn.execute(
                "SELECT decision, comment FROM hr_feedback ORDER BY id ASC LIMIT ?",
                (limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [{"decision": r["decision"], "comment": r["comment"]} for r in rows]


def save_interview(candidate, source, job, style, decision, score, hr_comment, chat_history, report_md):
    with _conn() as conn:
        conn.execute(
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


def list_interviews():
    """最近记录列表：id + 摘要"""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, candidate, job, decision, score, created_at FROM interviews ORDER BY id DESC LIMIT 50"
        ).fetchall()
        return [dict(r) for r in rows]


def get_interview(iid):
    with _conn() as conn:
        r = conn.execute("SELECT * FROM interviews WHERE id=?", (iid,)).fetchone()
        return dict(r) if r else None
