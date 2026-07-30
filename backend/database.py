"""
SQLite 数据库 - 饮食记录存储
"""
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "data" / "smartkitchen.db"

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    """初始化数据库表"""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            health_goal TEXT DEFAULT 'maintain',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT OR IGNORE INTO members (name, health_goal) VALUES ('default', 'maintain');
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_name TEXT NOT NULL,
            food_name_cn TEXT,
            weight_g REAL NOT NULL,
            calories REAL,
            protein_g REAL,
            fat_g REAL,
            carbs_g REAL,
            confidence REAL,
            image_path TEXT,
            member TEXT DEFAULT 'default',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_food_logs_date ON food_logs(created_at);
        CREATE INDEX IF NOT EXISTS idx_food_logs_member ON food_logs(member);
    """)
    conn.commit()
    conn.close()

def add_food_log(food_name, food_name_cn, weight_g, calories,
                 protein_g=0, fat_g=0, carbs_g=0, confidence=0,
                 image_path=None, member="default"):
    conn = get_connection()
    conn.execute("""
        INSERT INTO food_logs
        (food_name, food_name_cn, weight_g, calories,
         protein_g, fat_g, carbs_g, confidence, image_path, member)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (food_name, food_name_cn, weight_g, calories,
          protein_g, fat_g, carbs_g, confidence, image_path, member))
    conn.commit()
    log_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return log_id

def get_history(days=7, member=None, limit=50):
    conn = get_connection()
    query = """
        SELECT * FROM food_logs
        WHERE created_at >= datetime('now', ?)
    """
    params = [f"-{days} days"]
    if member:
        query += " AND member = ?"
        params.append(member)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_daily_summary(date=None):
    conn = get_connection()
    if date:
        rows = conn.execute("""
            SELECT SUM(calories) as total_cal, SUM(protein_g) as total_protein,
                   SUM(fat_g) as total_fat, SUM(carbs_g) as total_carbs,
                   COUNT(*) as count
            FROM food_logs WHERE date(created_at) = ?
        """, [date]).fetchone()
    else:
        rows = conn.execute("""
            SELECT date(created_at) as day,
                   SUM(calories) as total_cal,
                   SUM(protein_g) as total_protein,
                   SUM(fat_g) as total_fat,
                   SUM(carbs_g) as total_carbs,
                   COUNT(*) as count
            FROM food_logs
            GROUP BY date(created_at)
            ORDER BY day DESC LIMIT 14
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows] if isinstance(rows, list) else dict(rows)

def get_members():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM members ORDER BY created_at").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_member(name, health_goal="maintain"):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO members (name, health_goal) VALUES (?, ?)", (name, health_goal))
    conn.commit()
    m = conn.execute("SELECT * FROM members WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(m) if m else None

def delete_member(member_id):
    conn = get_connection()
    conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
    conn.commit()
    conn.close()

def update_member_goal(name, health_goal):
    conn = get_connection()
    conn.execute("UPDATE members SET health_goal = ? WHERE name = ?", (health_goal, name))
    conn.commit()
    conn.close()

def get_daily_summary_by_member(date=None, member=None):
    conn = get_connection()
    if date:
        rows = conn.execute("""
            SELECT SUM(calories) as total_cal, SUM(protein_g) as total_protein,
                   SUM(fat_g) as total_fat, SUM(carbs_g) as total_carbs,
                   COUNT(*) as count
            FROM food_logs WHERE date(created_at) = ? AND member = ?
        """, [date, member]).fetchone()
    else:
        rows = conn.execute("""
            SELECT date(created_at) as day,
                   SUM(calories) as total_cal,
                   SUM(protein_g) as total_protein,
                   SUM(fat_g) as total_fat,
                   SUM(carbs_g) as total_carbs,
                   COUNT(*) as count
            FROM food_logs WHERE member = ?
            GROUP BY date(created_at)
            ORDER BY day DESC LIMIT 14
        """, [member]).fetchall()
    conn.close()
    return [dict(r) for r in rows] if isinstance(rows, list) else dict(rows) if rows else {}

init_db()
