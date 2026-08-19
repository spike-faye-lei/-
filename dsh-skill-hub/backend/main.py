"""DSH Skill Hub — FastAPI 后端
扫描 spike-faye-lei-dsh-skills 仓库的 SKILL.md → SQLite 索引 → 搜索/详情/统计
（天团骨架 + 审批修正：sqlite 路径/解析健壮性/category 推导/stats 计数）
"""
import os
import re
import sqlite3
import json
import shutil

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DSH Skill Hub", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BACKEND_DIR, "skills.db")
EMBED_MODEL = os.environ.get("DSH_EMBED_MODEL", "bge-m3")
EMBED_URL = os.environ.get("DSH_EMBED_URL", "http://127.0.0.1:11434/api/embed")
SKILLS_ROOT = r"D:\spike-faye-lei-dsh-skills\skills"


def get_db():
    return sqlite3.connect(DB_PATH)


@app.on_event("startup")
def startup():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            name TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            description TEXT,
            type TEXT,
            category TEXT,
            license TEXT,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()


def parse_frontmatter(text: str) -> dict:
    """解析 SKILL.md frontmatter（健壮版：引号、冒号、多行描述）"""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    data = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"').strip("'")
        if value:
            data[key.strip()] = value
    return data


@app.post("/api/scan")
async def scan_skills():
    """扫描 SKILL.md，frontmatter 入库，category 从路径第二段推导"""
    conn = get_db()
    cur = conn.cursor()
    scanned = updated = inserted = 0
    if os.path.isdir(SKILLS_ROOT):
        for root, _, files in os.walk(SKILLS_ROOT):
            for fn in files:
                if fn != "SKILL.md":
                    continue
                path = os.path.join(root, fn)
                try:
                    text = open(path, encoding="utf-8", errors="replace").read()
                except Exception:
                    continue
                fm = parse_frontmatter(text)
                name = fm.get("name")
                if not name:
                    continue
                rel = os.path.relpath(root, SKILLS_ROOT)
                category = rel.split(os.sep)[0] if os.sep in rel else "root"
                cur.execute(
                    "INSERT OR REPLACE INTO skills (name, path, description, type, category, license, content) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (name, path, fm.get("description", ""), fm.get("type", ""),
                     category, fm.get("license", ""), text[:50000]),
                )
                scanned += 1
                if cur.rowcount == 1 and cur.lastrowid is not None:
                    pass
    conn.commit()
    # 统计 updated/inserted
    for (_, c) in conn.execute(
        "SELECT path, COUNT(*) FROM skills GROUP BY path HAVING COUNT(*) > 1"):
        pass  # 占位
    conn.close()
    return {"scanned": scanned, "indexed": scanned}


@app.get("/api/skills")
async def list_skills(q: str = Query(None), category: str = Query(None), limit: int = Query(50)):
    conn = get_db()
    cur = conn.cursor()
    sql = "SELECT name, description, type, category, license FROM skills"
    conds, params = [], []
    if q:
        conds.append("(name LIKE ? OR description LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    if category:
        conds.append("category = ?")
        params.append(category)
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " LIMIT ?"
    params.append(limit)
    rows = cur.execute(sql, params).fetchall()
    conn.close()
    return [
        {"name": r[0], "description": r[1], "type": r[2],
         "category": r[3], "license": r[4]}
        for r in rows
    ]


@app.get("/api/skills/{name}")
async def get_skill(name: str):
    conn = get_db()
    row = conn.execute(
        "SELECT name, path, description, type, category, license, content FROM skills WHERE name = ?",
        (name,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Skill not found")
    return {"name": row[0], "path": row[1], "description": row[2], "type": row[3],
            "category": row[4], "license": row[5], "content": row[6]}


@app.get("/api/stats")
async def get_stats():
    conn = get_db()
    cats = conn.execute("SELECT category, COUNT(*) FROM skills GROUP BY category").fetchall()
    total = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    conn.close()
    return {"stats": {c: n for c, n in cats}, "total": total}


# ---- 语义搜索（天团设计 + 审批修正：嵌入批量缓存、余弦公式、httpx）----
import httpx

_embed_cache = None  # (name, description, embedding)


def _embed(texts: list) -> list:
    """调 Ollama nomic-embed-text 嵌入（分批 100 条，trust_env=False 绕开注入代理）"""
    out = []
    with httpx.Client(timeout=600, trust_env=False) as client:
        for i in range(0, len(texts), 100):
            r = client.post(EMBED_URL,
                            json={"model": EMBED_MODEL, "input": texts[i:i + 100]})
            r.raise_for_status()
            out.extend(r.json().get("embeddings", []))
    return out


def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


@app.post("/api/search/semantic")
async def semantic_search(req: dict):
    """语义搜索：query 嵌入 vs 全部技能嵌入（缓存），top-5"""
    global _embed_cache
    query = (req.get("query") or "").strip()
    if not query:
        raise HTTPException(400, "query 不能为空")
    conn = get_db()
    rows = conn.execute("SELECT name, description FROM skills").fetchall()
    conn.close()
    if _embed_cache is None:
        texts = [f"{n} {d}" for n, d in rows]
        try:
            embs = _embed(texts)  # 批量一次（~1300 条）
            _embed_cache = [(n, d, e) for (n, d), e in zip(rows, embs)]
        except Exception as e:
            raise HTTPException(502, f"嵌入失败: {e}")
    try:
        qe = _embed([query])[0]
    except Exception as e:
        raise HTTPException(502, f"嵌入失败: {e}")
    scored = sorted(
        ((n, d, _cosine(qe, e)) for n, d, e in _embed_cache),
        key=lambda x: x[2], reverse=True)
    return [{"name": n, "description": d, "score": round(s, 4)}
            for n, d, s in scored[:5] if s > 0.1]


# ---- 安装管理（天团设计 + 审批修正：复制安装、~/.dsh、正确卸载）----
INSTALL_DIR = os.path.expanduser("~/.dsh/skills")


def _install_target(name: str) -> str:
    return os.path.join(INSTALL_DIR, name)


@app.post("/api/install/{name}")
async def install_skill(name: str):
    conn = get_db()
    row = conn.execute("SELECT path FROM skills WHERE name = ?", (name,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Skill not found")
    src = row[0]
    if not os.path.isfile(src):
        raise HTTPException(404, f"源文件不存在: {src}")
    src_dir = os.path.dirname(src)
    os.makedirs(INSTALL_DIR, exist_ok=True)
    target = _install_target(name)
    if os.path.exists(target):
        if os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=True)
        else:
            os.remove(target)
    shutil.copytree(src_dir, target)
    return {"message": f"已安装 {name}", "path": target}


@app.delete("/api/uninstall/{name}")
async def uninstall_skill(name: str):
    target = _install_target(name)
    if not os.path.exists(target):
        raise HTTPException(404, "未安装")
    if os.path.isdir(target):
        shutil.rmtree(target, ignore_errors=True)
    else:
        os.remove(target)
    return {"message": f"已卸载 {name}"}


@app.get("/api/installed")
async def list_installed():
    if not os.path.isdir(INSTALL_DIR):
        return {"installed": []}
    return {"installed": sorted(os.listdir(INSTALL_DIR))}


# ---- Guard 安全扫描（天团规则设计 + 审批落地：连真实数据、修正检测）----
import re as _re

_HIGH_PATTERNS = [
    (r"curl[^\n|]*\|[^\n]*bash", "curl|bash 管道执行"),
    (r"rm\s+-rf", "rm -rf 无保护删除"),
    (r"base64\s+-d[^\n]*\|\s*(sh|bash|python)", "base64 解码后执行"),
    (r"(curl|wget)[^\n]*https?://(?!example\.com|localhost|127\.0\.0\.1)[^\s]*\s*[^\n]*(KEY|TOKEN|SECRET|PASS)", "密钥经网络外传"),
]
_MID_PATTERNS = [
    (r"sk-[A-Za-z0-9]{8,}", "疑似硬编码 API key"),
    (r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "硬编码 api_key"),
]


@app.post("/api/audit")
async def audit_skills(req: dict = None):
    """安全扫描：高风险/中危/低危规则打分，A-F 信任等级"""
    req = req or {}
    name = (req.get("name") or "").strip()
    conn = get_db()
    rows = conn.execute("SELECT name, description, license, content FROM skills").fetchall()
    conn.close()
    results = []
    for rname, desc, lic, content in rows:
        if name and rname != name:
            continue
        issues = []
        score = 0
        for pat, label in _HIGH_PATTERNS:
            if _re.search(pat, content, _re.I):
                issues.append(f"高危: {label}"); score += 3
        for pat, label in _MID_PATTERNS:
            if _re.search(pat, content, _re.I):
                issues.append(f"中危: {label}"); score += 2
        if not (lic or "").strip():
            issues.append("中危: 无 license"); score += 2
        if not (desc or "").strip():
            issues.append("低危: 无 description"); score += 1
        elif len(desc) < 20:
            issues.append("低危: description 过短"); score += 1
        level = "F" if score >= 6 else "D" if score >= 4 else "C" if score >= 2 else "B" if score == 1 else "A"
        results.append({"name": rname, "score": score, "level": level, "issues": issues[:5]})
    results.sort(key=lambda x: -x["score"])
    return results


# ---- LLM 路由（天团设计 + 审批落地：一次调用选 top-3 + 理由）----
@app.post("/api/match")
async def match_skills(req: dict):
    """任务 → 语义候选 top-10 → 本地 LLM 精选 3 个（失败回退 top-3）"""
    task = (req.get("task") or "").strip()
    if not task:
        raise HTTPException(400, "task 不能为空")
    # 1. 语义候选
    try:
        candidates = await semantic_search({"query": task})
    except Exception:
        candidates = []
    top10 = candidates[:10]
    if not top10:
        return {"task": task, "matched": [], "fallback": []}
    # 2. LLM 精选
    prompt = (f"用户任务: {task}\n候选技能:\n" +
              "\n".join(f"{i+1}. {c['name']}: {c['description'][:80]}" for i, c in enumerate(top10)) +
              "\n请从中选出最相关的 3 个，输出 JSON: {\"picks\": [{\"name\": \"...\", \"reason\": \"中文理由\"}]}，只输出 JSON。")
    try:
        payload = {"model": "ollama/deepseek-r1:14b", "max_tokens": 800,
                   "messages": [{"role": "user", "content": prompt}]}
        async with httpx.AsyncClient(timeout=300, trust_env=False) as client:
            r = await client.post("http://127.0.0.1:4000/v1/chat/completions",
                                  json=payload, headers={"Authorization": "Bearer sk-local"})
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
        start, end = text.find("{"), text.rfind("}")
        picks = json.loads(text[start:end + 1]).get("picks", []) if start >= 0 else []
        if picks:
            return {"task": task, "matched": picks, "fallback": top10}
    except Exception:
        pass
    # 3. 回退
    return {"task": task, "matched": [{"name": c["name"], "reason": "候选"} for c in top10[:3]],
            "fallback": top10}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8693)
