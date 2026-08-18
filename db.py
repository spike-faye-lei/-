"""数据库层：SQLite（本地默认）/ PostgreSQL（生产切换，DB_TYPE 环境变量）

双库分支说明（不承诺"无缝"，差异在 README「数据库切换」一节列明）：
- 本地默认 SQLite（零依赖、单文件、WAL 可选），适合演示与单机部署
- 生产切换：DB_TYPE=postgres + DATABASE_URL 环境变量，_conn 走 psycopg2
- 已知差异（迁移清单见 README）：占位符 ?/%s、自增主键、ALTER 行为、事务隔离级别
"""
import json
import os
import sqlite3
from datetime import datetime

DB_TYPE = os.environ.get("DB_TYPE", "sqlite").lower()
DB_PATH = os.path.join(os.path.dirname(__file__), "recruit.db")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# 多租户默认租户：全表带 tenant_id，查询按租户过滤（多部门数据隔离）
DEFAULT_TENANT = "default"


def _conn():
    if DB_TYPE == "postgres":
        if not DATABASE_URL:
            raise RuntimeError("DB_TYPE=postgres 需要配置 DATABASE_URL")
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError as e:
            raise RuntimeError("DB_TYPE=postgres 需要安装 psycopg2：pip install psycopg2-binary") from e
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    conn = sqlite3.connect(DB_PATH, timeout=10)  # 写锁等待 10 秒（Webhook 实时入库与批处理并发写时排队而非立即报错）
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
        # 老库迁移：补列（已存在则跳过）；多租户：全表 tenant_id（多部门数据隔离）
        for table, cols in {
            "interviews": ("invite", "invite_status", "tenant_id", "session_state", "approval_trail"),
            "hr_feedback": ("job", "tenant_id"),
            "screenings": ("resume", "tenant_id"),
            "candidates": ("auth_source", "tenant_id"),
            "notifications": ("channel", "tenant_id"),
            "offers": ("tenant_id", "performance_rating"),  # 试用期绩效回传（录用后数据闭环）
            "score_cards": ("tenant_id",),
            "job_profiles": ("tenant_id", "interview_style"),  # 岗位级面试风格（技术深挖/温和引导/压力面试/快速筛选/行为面试）
            "batch_reports": ("tenant_id",),
        }.items():
            for col in cols:
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
                except sqlite3.OperationalError:
                    pass
        # 多租户兜底：老数据回填默认租户（NULL 行会被租户过滤漏掉）
        for table in ("candidates", "interviews", "screenings", "notifications", "offers", "score_cards", "job_profiles", "batch_reports", "hr_feedback"):
            try:
                conn.execute(f"UPDATE {table} SET tenant_id=? WHERE tenant_id IS NULL", (DEFAULT_TENANT,))
            except sqlite3.OperationalError:
                pass
    add_enterprise_tables()


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


def save_session_state(iid, state):
    """面试会话状态落盘（断点续面：每轮更新，中断后可恢复）"""
    with _conn() as conn:
        conn.execute(
            "UPDATE interviews SET session_state=? WHERE id=?",
            (json.dumps(state, ensure_ascii=False), iid),
        )


def load_session_state(iid):
    """读取落盘的面试会话状态（无记录返回 None）"""
    with _conn() as conn:
        r = conn.execute("SELECT session_state FROM interviews WHERE id=?", (iid,)).fetchone()
        if not r or not r["session_state"]:
            return None
        try:
            return json.loads(r["session_state"])
        except json.JSONDecodeError:
            return None


def find_unfinished_interview(candidate_name, job):
    """查某候选人同岗位未完成的面试记录（状态=面试中 且有落盘会话），供断点续面"""
    with _conn() as conn:
        r = conn.execute(
            "SELECT * FROM interviews WHERE candidate=? AND job=? AND decision='面试中' AND session_state IS NOT NULL "
            "ORDER BY id DESC LIMIT 1",
            (candidate_name, job),
        ).fetchone()
        return dict(r) if r else None


def set_invite(iid, invite_text, status="已发送"):
    """回写邀约文本与发送状态"""
    with _conn() as conn:
        conn.execute(
            "UPDATE interviews SET invite=?, invite_status=? WHERE id=?",
            (invite_text, status, iid),
        )


def update_interview_result(iid, decision, score, chat_history, report_md):
    """面试完成回写：面试中 → 最终结论（断点续面流：记录先建为「面试中」，完成后更新）"""
    with _conn() as conn:
        conn.execute(
            "UPDATE interviews SET decision=?, score=?, chat=?, report=?, session_state=NULL WHERE id=?",
            (decision, score, json.dumps(chat_history, ensure_ascii=False), report_md, iid),
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


# ==================== 企业级扩展：候选人全生命周期 + 岗位规则 + 通知/Offer ====================
# 生产替换说明：以下 SQL 均为标准 SQL，生产环境只需替换 _conn 为 PostgreSQL 连接即可

# 候选人状态机（全流程追踪，每个候选人必处其一）。
# 真实招聘顺序：Offer 前审批链（HR审核→业务审批→薪酬定薪→最终审批→发Offer）；
#               背景调查在候选人接受 Offer 之后（背调前需候选人单独授权）。
# 新入库 → 已解析 → 已初筛 → 初筛通过 → 面试中 → 待HR审核 → 业务审批中 → 薪酬定薪中 → HR通过
#     → 已发通知 → 已发Offer → Offer已接受 → 背景调查中 → 已入职
#     ↘ 初筛淘汰      ↘ HR驳回 → 已发婉拒     ↘ Offer已拒绝
STATUS_FLOW = [
    "新入库", "已解析", "已初筛", "初筛通过", "初筛淘汰", "面试中", "待HR审核",
    "业务审批中", "薪酬定薪中",
    "HR通过", "HR驳回", "已发通知", "已发Offer", "Offer已接受", "Offer已拒绝",
    "背景调查中", "已入职",
]
# HR 审核阶段（Offer 前的审批链，每环节记录审批人与时间戳；背景调查在 Offer 接受后单独发起）
REVIEW_STAGES = ["业务审批", "薪酬定薪", "最终审批"]
RESUME_DIR = os.path.join(os.path.dirname(__file__), "resumes")  # 简历文件存储目录（原文件落盘 + DB 存路径与解析文本）


def add_enterprise_tables():
    """企业级新表（幂等创建，init_db 内调用）"""
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                jd_text TEXT,
                rubric_id TEXT,
                rules TEXT,
                status TEXT DEFAULT '启用',
                interview_style TEXT DEFAULT 'tech',
                tenant_id TEXT DEFAULT 'default',
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source TEXT,
                resume_file TEXT,
                resume_text TEXT,
                parsed TEXT,
                status TEXT DEFAULT '新入库',
                status_note TEXT,
                match_score REAL,
                screen_score REAL,
                job_title TEXT,
                auth_source TEXT DEFAULT '候选人授权·本地上传',
                tenant_id TEXT DEFAULT 'default',
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER,
                candidate_name TEXT,
                ntype TEXT,
                content TEXT,
                status TEXT DEFAULT '已生成',
                channel TEXT,
                tenant_id TEXT DEFAULT 'default',
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER,
                candidate_name TEXT,
                job_title TEXT,
                salary TEXT,
                status TEXT DEFAULT '待接受',
                tenant_id TEXT DEFAULT 'default',
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hotword_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT,
                comment TEXT,
                status TEXT DEFAULT '待审核',
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS batch_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT,
                status TEXT DEFAULT '排队中',
                progress INTEGER DEFAULT 0,
                result TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS score_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER,
                candidate_name TEXT,
                job_title TEXT,
                final_score REAL,
                decision TEXT,
                breakdown TEXT,
                evidence TEXT,
                human_review TEXT,
                tenant_id TEXT DEFAULT 'default',
                created_at TEXT
            )
            """
        )


def save_job_profile(title, jd_text, rubric_id, rules, interview_style="tech"):
    """保存岗位配置（JD + 筛选规则 JSON + 岗位级面试风格），返回 id"""
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO job_profiles (title, jd_text, rubric_id, rules, interview_style, created_at) VALUES (?,?,?,?,?,?)",
            (title, jd_text, rubric_id, json.dumps(rules, ensure_ascii=False), interview_style,
             datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        return cur.lastrowid


def save_hotword_suggestion(word, comment=""):
    """热词建议入库（HR 提交新词 → 管理员审核后合并入 SKILL_LEXICON）"""
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO hotword_suggestions (word, comment, status, created_at) VALUES (?,?,?,?)",
            (word.strip().lower(), comment, "待审核", datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        return cur.lastrowid


def list_hotword_suggestions(limit=50):
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM hotword_suggestions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def list_job_profiles():
    """岗位配置列表（新→旧）"""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, title, rubric_id, rules, status, created_at FROM job_profiles ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_job_profile(jid):
    with _conn() as conn:
        r = conn.execute("SELECT * FROM job_profiles WHERE id=?", (jid,)).fetchone()
        return dict(r) if r else None


def get_latest_job_style(rubric_id):
    """按 rubric 取最近配置的岗位级面试风格（无配置回退 tech）"""
    with _conn() as conn:
        r = conn.execute(
            "SELECT interview_style FROM job_profiles WHERE rubric_id=? AND interview_style IS NOT NULL "
            "ORDER BY id DESC LIMIT 1", (rubric_id,)
        ).fetchone()
        return r["interview_style"] if r else "tech"


def add_candidate(name, resume_text, source="", resume_file="", parsed=None, job_title="", auth_source="候选人授权·本地上传"):
    """候选人入库（简历文本 + 文件路径 + 代码侧解析字段），状态=新入库，返回 id

    auth_source 为合规授权日志：候选人授权·本地上传 / 平台接口·授权 / 演示数据（见 docs 合规说明）
    """
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO candidates (name, source, resume_file, resume_text, parsed, job_title, auth_source, tenant_id, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                name, source, resume_file, resume_text,
                json.dumps(parsed, ensure_ascii=False) if parsed else None,
                job_title, auth_source, DEFAULT_TENANT, datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        return cur.lastrowid


def search_candidates(keyword, limit=100, tenant=None):
    """简历全文检索（关键字 → 姓名/技能/简历文本命中，按租户隔离）。

    本地实现：SQLite LIKE 扫描（数据量小足够）；生产替换位：Elasticsearch 全文检索
    （IK 中文分词 + 高亮），接口不变。
    """
    tenant = tenant or DEFAULT_TENANT
    kw = (keyword or "").strip()
    if not kw:
        return list_candidates(limit=limit, tenant=tenant)
    like = f"%{kw}%"
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM candidates WHERE tenant_id=? AND (name LIKE ? OR resume_text LIKE ? OR parsed LIKE ?) "
            "ORDER BY id DESC LIMIT ?",
            (tenant, like, like, like, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def update_candidate(cid, status=None, status_note=None, match_score=None, screen_score=None):
    """更新候选人状态/评分（只更新传入的非 None 字段）"""
    fields, values = [], []
    if status is not None:
        fields.append("status=?"); values.append(status)
    if status_note is not None:
        fields.append("status_note=?"); values.append(status_note)
    if match_score is not None:
        fields.append("match_score=?"); values.append(match_score)
    if screen_score is not None:
        fields.append("screen_score=?"); values.append(screen_score)
    if not fields:
        return
    values.append(cid)
    with _conn() as conn:
        conn.execute(f"UPDATE candidates SET {', '.join(fields)} WHERE id=?", values)


def list_candidates(status=None, limit=500, tenant=None):
    """候选人列表（按租户隔离；tenant=None 用 DEFAULT_TENANT），新→旧"""
    tenant = tenant or DEFAULT_TENANT
    with _conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM candidates WHERE tenant_id=? AND status=? ORDER BY id DESC LIMIT ?", (tenant, status, limit)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM candidates WHERE tenant_id=? ORDER BY id DESC LIMIT ?", (tenant, limit)).fetchall()
        return [dict(r) for r in rows]


def get_candidate(cid, tenant=None):
    tenant = tenant or DEFAULT_TENANT
    with _conn() as conn:
        r = conn.execute("SELECT * FROM candidates WHERE id=? AND tenant_id=?", (cid, tenant)).fetchone()
        return dict(r) if r else None


def get_candidate_by_name(name, status=None, tenant=None):
    """按姓名取最新一条候选人记录（同名取最新，按租户隔离）"""
    tenant = tenant or DEFAULT_TENANT
    with _conn() as conn:
        if status:
            r = conn.execute(
                "SELECT * FROM candidates WHERE tenant_id=? AND name=? AND status=? ORDER BY id DESC LIMIT 1", (tenant, name, status)
            ).fetchone()
        else:
            r = conn.execute(
                "SELECT * FROM candidates WHERE tenant_id=? AND name=? ORDER BY id DESC LIMIT 1", (tenant, name)
            ).fetchone()
        return dict(r) if r else None


def save_notification(candidate_id, candidate_name, ntype, content):
    """通知记录（面试邀约/婉拒/Offer 邮件），状态=已生成，发送后回写已发送"""
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO notifications (candidate_id, candidate_name, ntype, content, created_at) VALUES (?,?,?,?,?)",
            (candidate_id, candidate_name, ntype, content, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        return cur.lastrowid


def mark_notification_sent(nid, channel=None):
    """通知发送回写（channel：企业微信/短信/邮件/站内信，本地为模拟发送记录）"""
    with _conn() as conn:
        if channel:
            conn.execute("UPDATE notifications SET status='已发送', channel=? WHERE id=?", (channel, nid))
        else:
            conn.execute("UPDATE notifications SET status='已发送' WHERE id=?", (nid,))


def list_notifications(limit=100):
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def save_offer(candidate_id, candidate_name, job_title, salary):
    """Offer 记录（HR 通过后自动生成）"""
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO offers (candidate_id, candidate_name, job_title, salary, created_at) VALUES (?,?,?,?,?)",
            (candidate_id, candidate_name, job_title, salary, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        return cur.lastrowid


def list_offers(limit=100):
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM offers ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def update_offer_status(oid, status):
    with _conn() as conn:
        conn.execute("UPDATE offers SET status=? WHERE id=?", (status, oid))


def record_approval(iid, stage, conclusion, approver="HR"):
    """审批轨迹留痕：录用决策链每个环节（业务审批/薪酬定薪/背景调查/最终审批）记录审批人与时间戳"""
    with _conn() as conn:
        r = conn.execute("SELECT approval_trail FROM interviews WHERE id=?", (iid,)).fetchone()
        trail = []
        if r and r["approval_trail"]:
            try:
                trail = json.loads(r["approval_trail"])
            except json.JSONDecodeError:
                trail = []
        trail.append({"stage": stage, "conclusion": conclusion, "approver": approver,
                       "at": datetime.now().strftime("%Y-%m-%d %H:%M")})
        conn.execute("UPDATE interviews SET approval_trail=? WHERE id=?",
                      (json.dumps(trail, ensure_ascii=False), iid))
        return trail


def record_performance(oid, rating, comment=""):
    """试用期绩效回传：录用后 3 个月绩效 vs 当初 AI 打分（数据闭环的关键证据链）"""
    with _conn() as conn:
        conn.execute(
            "UPDATE offers SET performance_rating=?, status=? WHERE id=?",
            (f"{rating}｜{comment}" if comment else rating, "已回传绩效", oid),
        )


def delete_candidate_data(candidate_id=None, candidate_name=None):
    """候选人数据删除（PIPL 删除权）：删候选人 + 全部关联记录 + 简历文件

    返回删除的关联记录数。生产环境建议先软删除（标记+保留审计日志）再定期物理清理。
    """
    deleted = 0
    cid = candidate_id
    name = candidate_name
    with _conn() as conn:
        if cid is None and name:
            r = conn.execute("SELECT id, name, resume_file FROM candidates WHERE name=? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
            if r:
                cid, name = r["id"], r["name"]
        if cid is None:
            return 0
        # 关联记录清理（按候选人 id 或姓名）
        for table, col in (("interviews", "candidate"), ("screenings", "candidate"),
                            ("score_cards", "candidate_id"), ("notifications", "candidate_id"),
                            ("offers", "candidate_id")):
            if col == "candidate":
                cur = conn.execute(f"DELETE FROM {table} WHERE {col}=?", (name,))
            else:
                cur = conn.execute(f"DELETE FROM {table} WHERE {col}=?", (cid,))
            deleted += cur.rowcount
        row = conn.execute("SELECT resume_file FROM candidates WHERE id=?", (cid,)).fetchone()
        resume_file = row["resume_file"] if row else ""
        cur = conn.execute("DELETE FROM candidates WHERE id=?", (cid,))
        deleted += cur.rowcount
    # 简历原文件清除
    if resume_file and os.path.exists(resume_file):
        try:
            os.remove(resume_file)
        except OSError:
            pass
    return deleted


def cleanup_old_score_cards(keep_days: int = 365):
    """评分卡保留策略：默认保留 365 天——覆盖入职后试用期（3-6 个月）绩效回传窗口，
    保证《AI 打分 vs 入职表现一致率报告》有完整数据支撑"""
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=keep_days)).strftime("%Y-%m-%d %H:%M")
    with _conn() as conn:
        cur = conn.execute("DELETE FROM score_cards WHERE created_at < ?", (cutoff,))
        return cur.rowcount


def funnel_stats(tenant=None):
    """全流程漏斗统计：候选人各状态计数（按状态机顺序排列）

    tenant 语义：None → 默认租户；"all" → 跨租户聚合（集团 HR 视角，跨子公司对比招聘效率）
    """
    with _conn() as conn:
        if tenant == "all":
            rows = conn.execute("SELECT status, COUNT(*) AS cnt FROM candidates GROUP BY status").fetchall()
        else:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS cnt FROM candidates WHERE tenant_id=? GROUP BY status", (tenant or DEFAULT_TENANT,)
            ).fetchall()
        cnt = {r["status"]: r["cnt"] for r in rows}
        known = [(s, cnt.get(s, 0)) for s in STATUS_FLOW if cnt.get(s, 0) > 0]
        known += [(s, cnt[s]) for s in cnt if s not in STATUS_FLOW]
        return known


def create_batch_task(task_type="批量任务"):
    """异步批处理任务：提交即返回，后台线程执行（大规模简历处理不阻塞界面）"""
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO batch_tasks (task_type, created_at) VALUES (?,?)",
            (task_type, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        return cur.lastrowid


def update_batch_task(tid, status=None, progress=None, result=None):
    fields, values = [], []
    if status is not None:
        fields.append("status=?"); values.append(status)
    if progress is not None:
        fields.append("progress=?"); values.append(progress)
    if result is not None:
        fields.append("result=?"); values.append(result)
    if not fields:
        return
    values.append(tid)
    with _conn() as conn:
        conn.execute(f"UPDATE batch_tasks SET {', '.join(fields)} WHERE id=?", values)


def get_batch_task(tid):
    with _conn() as conn:
        r = conn.execute("SELECT * FROM batch_tasks WHERE id=?", (tid,)).fetchone()
        return dict(r) if r else None


def list_batch_tasks(limit=20):
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM batch_tasks ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def save_score_card(candidate_id, candidate_name, job_title, final_score, decision, breakdown, evidence, human_review=""):
    """评分卡入库：打分全过程的中间结果留痕（可审计证据链，总监可一眼看懂算法）"""
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO score_cards (candidate_id, candidate_name, job_title, final_score, decision, breakdown, evidence, human_review, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                candidate_id, candidate_name, job_title, final_score, decision,
                json.dumps(breakdown, ensure_ascii=False), json.dumps(evidence, ensure_ascii=False),
                human_review, datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        return cur.lastrowid


def get_score_card(candidate_id, job_title=None):
    """取候选人最新评分卡（同岗位最新一张）"""
    with _conn() as conn:
        if job_title:
            r = conn.execute(
                "SELECT * FROM score_cards WHERE candidate_id=? AND job_title=? ORDER BY id DESC LIMIT 1",
                (candidate_id, job_title),
            ).fetchone()
        else:
            r = conn.execute(
                "SELECT * FROM score_cards WHERE candidate_id=? ORDER BY id DESC LIMIT 1",
                (candidate_id,),
            ).fetchone()
        return dict(r) if r else None


def update_score_card_review(card_id, human_review):
    """HR 复核意见回写评分卡（人工复核留痕）"""
    with _conn() as conn:
        conn.execute("UPDATE score_cards SET human_review=? WHERE id=?", (human_review, card_id))
