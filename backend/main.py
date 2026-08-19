"""天团控制台后端 v2 — 127.0.0.1:8777
直连 Ollama(11434)：聊天会话（流式+工具循环）、天团自适应循环、任务队列、统计、记忆库、战报。
所有计算走本机 Ollama，零外网模型调用。WebSocket 实时推送。
"""
import asyncio
import csv
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.request
from collections import deque
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="天团控制台")

REQUESTS = {"n": 0}
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # 所有子进程禁止弹黑框


@app.middleware("http")
async def count_requests(request, call_next):
    REQUESTS["n"] += 1
    return await call_next(request)

# ---------------------------------------------------------------- 路径与配置

IS_FROZEN = bool(getattr(sys, "frozen", False))  # PyInstaller 打包后 exe
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
# 打包成 exe 后程序目录只读，数据放 %LOCALAPPDATA%\TeamConsole；开发态沿用仓库目录
if IS_FROZEN:
    DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ROOT_DIR), "TeamConsole")
    FRONTEND_DIR = os.path.join(getattr(sys, "_MEIPASS", ROOT_DIR), "frontend")
else:
    DATA_DIR = os.path.join(BACKEND_DIR, "..")
    FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
DATA_DIR = os.path.abspath(DATA_DIR)
os.makedirs(DATA_DIR, exist_ok=True)  # sqlite 不会自建父目录，import 时就要可用
DATABASE = os.path.join(DATA_DIR, "tasks.db")
OUTPUT_DIR = os.path.join(DATA_DIR, "outputs")
LOG_DIR = os.path.join(DATA_DIR, "logs")
REPORT_DIR = os.path.join(DATA_DIR, "reports")

# 用户可覆盖配置（数据目录下 config.json）：ollama 路径 / 追加技能目录
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
try:
    with open(CONFIG_PATH, encoding="utf-8") as _f:
        CONFIG = json.load(_f)
except Exception:
    CONFIG = {}
HOME = os.path.expanduser("~")
USAGE_CSV = os.path.join(HOME, ".claude", "logs", "local-usage.csv")
MEMORY_SCRIPT = os.path.join(HOME, ".claude", "scripts", "proj-memory.py")
SEARCH_SCRIPT = os.path.join(HOME, ".claude", "scripts", "search.py")
OLLAMA_EXE = os.path.join(HOME, "AppData", "Local", "Programs", "Ollama", "ollama.exe")
OLLAMA_URL = "http://127.0.0.1:11434"
_PY312 = os.path.join(HOME, "AppData", "Local", "Programs", "Python", "Python312", "python.exe")
PYTHON_EXE = _PY312 if os.path.isfile(_PY312) else ("python" if IS_FROZEN else (sys.executable or "python"))

# 天团花名册：模型 -> 岗位（与桌面《本地模型天团名单》一致）
ROSTER = {
    "qwen3:14b": "主审·拍板调度",
    "qwen2.5-coder:14b": "代码师",
    "deepseek-r1:14b": "推理师",
    "deepseek-coder-v2:16b": "算法王",
    "qwen3:8b": "文书员/数学师",
    "gemma2:9b": "快小秘",
    "llama3.1:8b": "英文王",
    "qwen2-math:7b": "数学王",
    "qwen2.5vl:7b": "视觉师",
    "bge-m3": "检索师(嵌入)",
    "qwen3:4b": "轻聊小秘·路由器",
}

# 天团自适应循环：初稿按任务派最合适的模型，主审验收，不合格派对应专家修，
# 一直到 PASS 或达到最大轮数。岗位关键词 → 修复派工表。
FIXER_HINTS = [
    (("代码", "bug", "接口", "函数", "语法", "报错", "实现"), "qwen2.5-coder:14b"),
    (("逻辑", "推理", "证明", "分析", "根因", "矛盾"), "deepseek-r1:14b"),
    (("算法", "复杂度", "性能", "优化", "边界"), "deepseek-coder-v2:16b"),
    (("数学", "计算", "公式", "数值"), "qwen2-math:7b"),
    (("英文", "翻译", "邮件", "英文"), "llama3.1:8b"),
    (("结构", "表达", "格式", "文案", "总结"), "qwen3:8b"),
]

# ---------------------------------------------------------------- 实时事件总线

class Hub:
    """WebSocket 广播 + 活动时间线环形缓冲（页面加载时可回放最近事件）。"""

    def __init__(self):
        self.clients = set()
        self.timeline = deque(maxlen=300)
        self.loop = None
        self.lock = threading.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket):
        self.clients.discard(ws)

    def emit(self, ev: dict):
        """线程安全广播；同时写入时间线。"""
        ev["ts"] = datetime.now().strftime("%H:%M:%S")
        with self.lock:
            self.timeline.append(ev)
        if not self.clients or not self.loop:
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(ev), self.loop)

    async def _broadcast(self, ev: dict):
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_text(json.dumps(ev, ensure_ascii=False))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)


hub = Hub()

# 运行状态：model -> 正在干什么（供"看到他们什么时候在做什么"）
BUSY = {}
BUSY_LOCK = threading.Lock()
# gen_id -> {"cancel": bool}，取消生成用
ACTIVE = {}


def set_busy(model, what):
    with BUSY_LOCK:
        if what is None:
            BUSY.pop(model, None)
        else:
            BUSY[model] = {"what": what, "since": time.time()}
    hub.emit({"type": "models_changed"})

# ---------------------------------------------------------------- 数据库

def create_tables():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            model TEXT, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            finished_at DATETIME, result_path TEXT, error TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL DEFAULT '新会话',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            thinking TEXT,
            model TEXT, tokens INTEGER DEFAULT 0, duration_ms INTEGER DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS team_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            task TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'running',
            result_path TEXT, error TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            finished_at DATETIME)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS team_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL, step INTEGER NOT NULL,
            name TEXT NOT NULL, model TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            tokens INTEGER DEFAULT 0, duration_ms INTEGER DEFAULT 0, error TEXT)""")
        conn.commit()


create_tables()

# ---------------------------------------------------------------- Ollama 客户端

def ollama_online():
    try:
        urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3)
        return True
    except Exception:
        return False


def _ollama_tags():
    """已装模型清单：name -> {size, family, quant}。失败返回 {}。"""
    try:
        d = json.loads(urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5).read())
        out = {}
        for m in d.get("models", []):
            det = m.get("details") or {}
            out[m["name"]] = {"size_gb": round(m.get("size", 0) / 1e9, 1),
                              "family": det.get("family", ""),
                              "quant": det.get("quantization_level", "")}
        return out
    except Exception:
        return {}


EMBED_FAMILIES = {"bert", "embedding", "nomic-bert"}
_tags_cache = {"at": 0.0, "data": {}}


def installed_models():
    """带 30s 缓存的已装模型表。"""
    if time.time() - _tags_cache["at"] > 30 or not _tags_cache["data"]:
        _tags_cache["data"] = _ollama_tags()
        _tags_cache["at"] = time.time()
    return _tags_cache["data"]


def installed_chat_models():
    tags = installed_models()
    return [n for n, v in tags.items()
            if v.get("family") not in EMBED_FAMILIES and "embed" not in n.lower()]


def ensure_ollama():
    """Ollama 不在线则拉起（PATH + 默认安装位 + config 覆盖），最多等 60 秒。"""
    if ollama_online():
        return True
    cands = []
    if CONFIG.get("ollama_path"):
        cands.append(CONFIG["ollama_path"])
    cands += [OLLAMA_EXE, "ollama"]
    for exe in cands:
        try:
            subprocess.Popen([exe, "serve"], creationflags=NO_WINDOW,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            break
        except Exception:
            continue
    for _ in range(60):
        if ollama_online():
            return True
        time.sleep(1)
    return False


def log_usage(model, task, prompt_tokens, completion_tokens, chars):
    """与 ~/.claude/logs/local-usage.csv 同格式记账，daily-report.py 继续可用。"""
    try:
        os.makedirs(os.path.dirname(USAGE_CSV), exist_ok=True)
        with open(USAGE_CSV, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    model, task.replace("\n", " ")[:40],
                                    prompt_tokens, completion_tokens, chars])
    except Exception:
        pass


def split_thinking(text):
    """兼容 <think>...</think> 内联思维链（老版 ollama 输出格式）。"""
    m = re.search(r"<think>(.*?)</think>", text, re.S)
    if not m:
        return text, ""
    return (text[:m.start()] + text[m.end():]).strip(), m.group(1).strip()


def ollama_stream(model, messages, max_tokens=2048, gen_id=None,
                  on_delta=None, on_thinking=None, temperature=None):
    """流式调用 /api/chat。返回 (content, thinking, stats)。gen_id 对应 ACTIVE 可取消。"""
    options = {"num_predict": max_tokens}
    if temperature is not None:
        options["temperature"] = max(0.0, min(2.0, temperature))
    body = json.dumps({"model": model, "messages": messages, "stream": True,
                       "options": options}).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    content, thinking = "", ""
    stats = {"prompt_tokens": 0, "completion_tokens": 0, "tok_s": 0.0}
    with urllib.request.urlopen(req, timeout=600) as resp:
        for raw in resp:
            if gen_id and ACTIVE.get(gen_id, {}).get("cancel"):
                raise RuntimeError("已取消")
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            d = json.loads(line)
            msg = d.get("message", {})
            if msg.get("thinking"):
                thinking += msg["thinking"]
                if on_thinking:
                    on_thinking(msg["thinking"])
            if msg.get("content"):
                content += msg["content"]
                if on_delta:
                    on_delta(msg["content"])
            if d.get("done"):
                stats["completion_tokens"] = d.get("eval_count", 0)
                stats["prompt_tokens"] = d.get("prompt_eval_count", 0)
                dur = d.get("eval_duration", 0) / 1e9
                stats["tok_s"] = round(stats["completion_tokens"] / dur, 1) if dur > 0 else 0.0
    content, inline = split_thinking(content)
    if inline:
        thinking = (thinking + "\n" + inline).strip()
    return content.strip(), thinking.strip(), stats


def generate(gen_id, model, messages, max_tokens, ev_extra, session_id, msg_id, what,
             temperature=None):
    """后台线程通用生成：流式回调 -> WebSocket 事件 + 落库。返回 (content, thinking, stats, duration_ms)。"""
    t0 = time.time()
    set_busy(model, what)

    def push(kind, payload=""):
        ev = {"type": kind, "session_id": session_id, "msg_id": msg_id,
              "model": model, "payload": payload}
        ev.update(ev_extra)
        hub.emit(ev)

    try:
        content, thinking, stats = ollama_stream(
            model, messages, max_tokens, gen_id,
            on_delta=lambda d: push("chat_delta", d),
            on_thinking=lambda t: push("chat_thinking", t),
            temperature=temperature)
        duration_ms = int((time.time() - t0) * 1000)
        if msg_id > 0:
            with sqlite3.connect(DATABASE) as conn:
                conn.execute("""UPDATE messages SET content=?, thinking=?, model=?, tokens=?,
                                duration_ms=? WHERE id=?""",
                             (content, thinking, model, stats["completion_tokens"],
                              duration_ms, msg_id))
                conn.execute("UPDATE sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
                             (session_id,))
                conn.commit()
        log_usage(model, messages[-1]["content"] if messages else "",
                  stats["prompt_tokens"], stats["completion_tokens"], len(content))
        push("chat_done", {"tokens": stats["completion_tokens"],
                           "tok_s": stats["tok_s"], "duration_ms": duration_ms})
        return content, thinking, stats, duration_ms
    except Exception as e:
        err = "已取消" if "已取消" in str(e) else str(e)[:300]
        if msg_id > 0:
            with sqlite3.connect(DATABASE) as conn:
                conn.execute("UPDATE messages SET model=? WHERE id=?", (model, msg_id))
                conn.commit()
        push("chat_error", err)
        raise
    finally:
        set_busy(model, None)
        ACTIVE.pop(gen_id, None)

# ---------------------------------------------------------------- 技能/角色库（全机资产）

SKILL_DIRS = [
    os.path.join(HOME, ".claude", "skills"),
    os.path.join(HOME, ".agents", "skills"),
    r"D:\Hermes\skills",
]
PLUGIN_SKILL_GLOB = os.path.join(HOME, ".zcode", "cli", "plugins", "cache",
                                 "*", "*", "*", "skills")
SKILL_REPO_GLOB = os.path.join(HOME, ".claude", "skills-repos", "*", "**", "SKILL.md")
AGENT_DIRS = [
    os.path.join(HOME, ".claude", "agents"),
    os.path.join(HOME, ".claude", "plugins", "marketplaces",
                 "claude-plugins-official", "plugins", "*", "agents"),
    os.path.join(HOME, ".claude", "plugins", "cache",
                 "claude-plugins-official", "*", "*", "agents"),
    os.path.join(HOME, ".claude", "agents-backup"),
]

_skills_cache = {"at": 0.0, "data": []}
_agents_cache = {"at": 0.0, "data": []}


def _parse_md(path):
    """读 markdown，剥掉 frontmatter，返回 (正文, description)。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return "", ""
    desc = ""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            fm = text[3:end]
            m = re.search(r"^description:\s*(.+)$", fm, re.M)
            if m:
                desc = m.group(1).strip().strip("\"'")
            text = text[end + 4:]
    body = "\n".join(l for l in text.splitlines() if l.strip() and not l.startswith("---"))
    return body, desc[:120]


def find_skill(name):
    for base in SKILL_DIRS:
        if not os.path.isdir(base):
            continue
        p = os.path.join(base, name, "SKILL.md")
        if os.path.isfile(p):
            return p
    import glob as _g
    for pat in (os.path.join(PLUGIN_SKILL_GLOB, name, "SKILL.md"),
                os.path.join(HOME, ".claude", "skills-repos", name, "SKILL.md"),
                SKILL_REPO_GLOB.replace("**", name)):
        for p in sorted(_g.glob(pat)):
            return p
    return None


def agent_dirs():
    import glob as _g
    for pat in AGENT_DIRS:
        for d in sorted(_g.glob(pat)):
            if os.path.isdir(d):
                yield d


def scan_skills():
    if time.time() - _skills_cache["at"] < 60:
        return _skills_cache["data"]
    out = []
    for base in SKILL_DIRS:
        src = os.path.basename(os.path.dirname(base))  # .claude / .agents / Hermes
        try:
            names = os.listdir(base)
        except Exception:
            continue
        for n in names:
            p = os.path.join(base, n, "SKILL.md")
            if os.path.isfile(p):
                _, desc = _parse_md(p)
                out.append({"name": n, "description": desc, "source": src})
    import glob as _g
    for p in _g.glob(os.path.join(PLUGIN_SKILL_GLOB, "*", "SKILL.md")):
        n = os.path.basename(os.path.dirname(p))
        if not any(s["name"] == n for s in out):
            _, desc = _parse_md(p)
            out.append({"name": n, "description": desc, "source": "plugin"})
    out.sort(key=lambda s: s["name"])
    _skills_cache["at"], _skills_cache["data"] = time.time(), out
    return out


def scan_agents():
    if time.time() - _agents_cache["at"] < 60:
        return _agents_cache["data"]
    out, seen = [], set()
    for d in agent_dirs():  # 顺序即优先级：.claude/agents → 插件 → agents-backup
        try:
            files = sorted(os.listdir(d))
        except Exception:
            continue
        for f in files:
            if not f.endswith(".md"):
                continue
            stem = f[:-3]
            if stem in seen:
                continue
            body, desc = _parse_md(os.path.join(d, f))
            if not body.strip():
                continue
            seen.add(stem)
            out.append({"name": stem,
                        "description": desc or body.splitlines()[0][:80],
                        "source": os.path.basename(d)})
    out.sort(key=lambda a: a["name"])
    _agents_cache["at"], _agents_cache["data"] = time.time(), out
    return out


def find_agent(name):
    stem = name[:-3] if name.endswith(".md") else name
    for d in agent_dirs():
        p = os.path.join(d, stem + ".md")
        if os.path.isfile(p):
            return p
    return None


def inject_caps(message, skills, agent):
    """把技能方法论/角色定义注入消息（与 local-llm.py 的 --skill/--agent 同思路）。"""
    total = 0
    for sk in skills or []:
        if total > 12000:
            break
        p = find_skill(sk)
        if p:
            body, _ = _parse_md(p)
            body = "\n".join(body.splitlines()[:120])[:6000]
            message += f"\n\n--- 技能 [{sk}] 方法论（请按此执行）---\n{body}"
            total += len(body)
    if agent:
        p = find_agent(agent)
        if p:
            body, _ = _parse_md(p)
            body = "\n".join(body.splitlines()[:120])[:6000]
            message += f"\n\n--- 角色 [{agent}]（请以该角色身份工作）---\n{body}"
    return message

# ---------------------------------------------------------------- 路由（智能选模型）

KEYWORD_FALLBACK = [
    (("写", "代码", "接口", "函数", "页面", "bug", "报错", "python", "fastapi", "vue", "js"),
     "qwen2.5-coder:14b"),
    (("算法", "复杂度", "排序", "数学", "证明", "计算"), "qwen2-math:7b"),
    (("为什么", "分析", "诊断", "根因", "审查", "推演"), "deepseek-r1:14b"),
]

ROUTER_MAP = {
    "code": "qwen2.5-coder:14b",
    "algorithm": "qwen2-math:7b",
    "reasoning": "deepseek-r1:14b",
    "english": "llama3.1:8b",
    "vision": "qwen2.5vl:7b",
    "text": "qwen3:8b",
    "review": "qwen3:14b",
}


def route_model(command):
    """分类选模型（未装自动改派）。返回 (model, how)。"""
    inst = installed_chat_models()

    def usable(m, how):
        if not inst:
            return m, how + "（未检测到已装模型清单）"
        if m in inst:
            return m, how
        alt = "qwen3:4b" if "qwen3:4b" in inst else inst[0]
        return alt, f"{how}（{m} 未安装，改派）"

    if not ollama_online():
        for kws, m in KEYWORD_FALLBACK:
            if any(k in command.lower() for k in kws):
                return usable(m, "关键词兜底(离线)")
        return usable("qwen3:14b", "默认主审(离线)")
    try:
        body = json.dumps({
            "model": "qwen3:4b" if not inst or "qwen3:4b" in inst else inst[0],
            "stream": False,
            "messages": [
                {"role": "system",
                 "content": "你是分类器。只输出一个词，从这些里选：code, algorithm, reasoning, english, vision, text, review"},
                {"role": "user", "content": command[:500]}],
            "options": {"num_predict": 8, "temperature": 0}}).encode()
        req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=body,
                                     headers={"Content-Type": "application/json"})
        d = json.loads(urllib.request.urlopen(req, timeout=60).read())
        out = (d.get("message", {}).get("content") or "").strip().lower()
        cls = next((k for k in ROUTER_MAP if k in out), None)
        if cls:
            return usable(ROUTER_MAP[cls], f"路由器(分类→{cls})")
    except Exception:
        pass
    for kws, m in KEYWORD_FALLBACK:
        if any(k in command.lower() for k in kws):
            return usable(m, "关键词兜底")
    return usable("qwen3:14b", "默认主审")

# ---------------------------------------------------------------- Pydantic 请求体

class ChatIn(BaseModel):
    session_id: int | None = None
    message: str
    model: str = "auto"
    skills: list[str] = []
    agent: str = ""
    temperature: float | None = None
    max_tokens: int = 2048
    context: int = 12   # 携带的历史消息条数
    tools: bool = True   # 工具循环总开关（False=纯对话；True=按 permission 档位执行）
    permission: str = "ask"  # 权限梯度：readonly/plan/ask/yolo


class TeamIn(BaseModel):
    session_id: int | None = None
    task: str
    skills: list[str] = []
    agent: str = ""
    max_rounds: int = 6
    permission: str = "ask"  # 权限梯度：readonly/plan/ask/yolo（天团读写文件时生效）


class TaskCreate(BaseModel):
    command: str


class MemoryIn(BaseModel):
    project: str
    entry: str


class CancelIn(BaseModel):
    session_id: int


class ReportIn(BaseModel):
    session_id: int | None = None


class ModelIn(BaseModel):
    model: str


class ToolResolve(BaseModel):
    key: str
    allow: bool

# ---------------------------------------------------------------- 基础接口

@app.on_event("startup")
async def startup():
    create_tables()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    hub.loop = asyncio.get_event_loop()
    threading.Thread(target=ensure_ollama, daemon=True).start()


@app.get("/")
async def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/api/health")
async def health():
    return {"status": "ok", "ollama": ollama_online(),
            "busy": dict(BUSY), "reqs": REQUESTS["n"],
            "now": datetime.now().isoformat(timespec="seconds")}


_vram_cache = {"at": 0.0, "data": None}


def vram_info():
    """nvidia-smi 显存水位，10s 缓存。无独显返回 None。"""
    if time.time() - _vram_cache["at"] < 10 and _vram_cache["data"] is not None:
        return _vram_cache["data"]
    info = None
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.total,memory.used",
                            "--format=csv,noheader,nounits"], capture_output=True,
                           text=True, timeout=6, creationflags=NO_WINDOW)
        if r.returncode == 0:
            total, used = [int(x.strip()) for x in r.stdout.strip().splitlines()[0].split(",")]
            info = {"total_mb": total, "used_mb": used}
    except Exception:
        info = None
    _vram_cache.update(at=time.time(), data=info)
    return info


@app.get("/api/models")
async def get_models():
    """动态花名册：只列本机已装模型，已知成员带岗位，陌生模型作「客座」。"""
    ensure_ollama()
    tags = installed_models()
    ps = {}
    try:
        d = json.loads(urllib.request.urlopen(f"{OLLAMA_URL}/api/ps", timeout=5).read())
        for m in d.get("models", []):
            key = m["name"] if ":" in m["name"] else m["name"] + ":latest"
            ps[key] = round(m.get("size_vram", 0) / 1e9, 1)
    except Exception:
        pass
    names = [n for n in ROSTER if n in tags] + [n for n in sorted(tags) if n not in ROSTER]
    out = []
    for name in names:
        v = tags.get(name, {})
        is_embed = v.get("family") in EMBED_FAMILIES or "embed" in name.lower()
        role = "检索师(嵌入)" if is_embed else ROSTER.get(name, "客座")
        with BUSY_LOCK:
            busy = BUSY.get(name)
        if busy:
            status, extra = "busy", busy["what"]
        elif name in ps:
            status, extra = "loaded", f"驻留 {ps[name]}G 显存"
        else:
            extra = f"磁盘 {v.get('size_gb', '?')}G"
            if v.get("quant"):
                extra += f" · {v['quant']}"
            extra += "，不占显存"
            status = "idle"
        out.append({"name": name, "role": role, "status": status,
                    "detail": extra, "size_gb": v.get("size_gb", 0),
                    "embed": is_embed})
    return {"vram": vram_info(), "models": out}


@app.get("/api/skills")
async def list_skills():
    return {"skills": scan_skills(), "agents": scan_agents()}


@app.get("/api/stats")
async def get_stats():
    agg = {}
    if os.path.isfile(USAGE_CSV):
        with open(USAGE_CSV, encoding="utf-8", errors="replace") as f:
            for row in csv.reader(f):
                if len(row) < 6 or row[0] == "time":
                    continue
                a = agg.setdefault(row[1], {"tokens": 0, "calls": 0})
                try:
                    a["tokens"] += int(row[3]) + int(row[4])
                    a["calls"] += 1
                except ValueError:
                    pass
    return [{"model": m, "role": ROSTER.get(m, ""), "tokens": v["tokens"], "calls": v["calls"]}
            for m, v in sorted(agg.items(), key=lambda x: -x[1]["tokens"])]


@app.get("/api/events")
async def recent_events():
    with hub.lock:
        return list(hub.timeline)[-80:]


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await hub.connect(ws)
    try:
        while True:
            await ws.receive_text()  # 客户端心跳；收到即忽略
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        hub.disconnect(ws)

# ---------------------------------------------------------------- 会话与聊天

def new_session(title="新会话"):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.execute("INSERT INTO sessions (title) VALUES (?)", (title[:30],))
        conn.commit()
        return cur.lastrowid


@app.get("/api/sessions")
async def list_sessions():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""SELECT s.*, (SELECT COUNT(*) FROM messages m
                             WHERE m.session_id=s.id) AS msg_count
                             FROM sessions s ORDER BY s.updated_at DESC LIMIT 50""").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/session")
async def create_session():
    sid = new_session()
    hub.emit({"type": "session_new", "payload": {"id": sid}})
    return {"session_id": sid}


@app.delete("/api/sessions/{sid}")
async def delete_session(sid: int):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("DELETE FROM messages WHERE session_id=?", (sid,))
          # conn.execute("""DELETE FROM team_steps WHERE run_id IN
                            # (SELECT id FROM team_runs WHERE session_id=?)""", (sid,))
          # _old_conn_execute("""DELETE FROM team_steps WHERE run_id IN
                          # _old_select id FROM team_runs WHERE session_id=?)""", (sid,))
        conn.execute("DELETE FROM team_runs WHERE session_id=?", (sid,))
        conn.execute("DELETE FROM sessions WHERE id=?", (sid,))
        conn.commit()
    hub.emit({"type": "session_deleted", "payload": {"id": sid}})
    return {"ok": True}


@app.get("/api/sessions/{sid}/messages")
async def session_messages(sid: int):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""SELECT id, role, content, thinking, model, tokens,
                              duration_ms, created_at FROM messages
                              WHERE session_id=? ORDER BY id""", (sid,)).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/sessions/{sid}/trajectory")
async def session_trajectory(sid: int):
    """事件账本（DSH trajectory 同思路）：会话内每次模型调用的起止/耗时/token。"""
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""SELECT id, role, model, tokens, duration_ms, created_at
                              FROM messages WHERE session_id=? ORDER BY id""", (sid,)).fetchall()
    out = []
    t0 = None
    for r in rows:
        try:
            ts = datetime.strptime(r["created_at"], "%Y-%m-%d %H:%M:%S").timestamp()
        except Exception:
            continue
        if t0 is None:
            t0 = ts
        dur_s = (r["duration_ms"] or 0) / 1000
        out.append({"msg_id": r["id"], "role": r["role"], "model": r["model"],
                    "tokens": r["tokens"] or 0, "dur_s": round(dur_s, 1),
                    "start_s": round(ts - t0, 1),
                    "tok_s": round((r["tokens"] or 0) / dur_s, 1) if dur_s > 0.3 else 0})
    return out


def history_messages(sid, limit=12):
    """取最近 N 条对话做多轮上下文。"""
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""SELECT role, content FROM messages WHERE session_id=?
                              ORDER BY id DESC LIMIT ?""", (sid, limit)).fetchall()
    msgs = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    return [m for m in msgs if m["content"].strip()]

# ---------------------------------------------------------------- 工具循环（让本地模型真的能动手）

TOOL_ROUNDS = 6          # 每条消息最多工具轮数
# 权限梯度：哪些工具自动执行（其余需用户逐次批准）
PERM_AUTO = {
    0: set(),                                    # 严格：一切工具都要批准
    1: {"LS", "READ", "SEARCH"},                 # 标准：读类自动，写/跑需批准
    2: {"LS", "READ", "SEARCH", "WRITE"},        # 宽松：写文件也自动，仅命令需批准
    3: {"LS", "READ", "SEARCH", "WRITE", "RUN"}, # 全开：全自动
}
PERM_NAMES = {0: "严格", 1: "标准", 2: "宽松", 3: "全开"}
TOOL_PROMPT = """

【重要：你有工具，禁止说"无法访问/无法列出"】你可以真实操作这台电脑：
[LS: 目录路径] —— 列出目录
[READ: 文件路径] —— 读文件前4000字
[SEARCH: 关键词] —— 联网搜索
[WRITE: 文件路径] —— 写文件，下一行用 <<< 和 >>> 包裹完整内容：
[WRITE: D:\\x\\a.py]
<<<
print(1)
>>>
[RUN: 命令] —— 执行命令，超时60秒
用法：把工具调用写在回复末尾，单独成行。系统执行后把真实结果回传给你继续。
涉及文件/目录/系统信息的任务，必须先调用 [LS:] 或 [READ:] 拿真实内容再回答，禁止编造。
[READ:] 的路径必须来自 [LS:] 结果里真实列出的文件，禁止猜路径；读不到就换真实存在的文件。
例：用户问"D:\\x 里有什么" → 你输出一行 [LS: D:\\x] 即可，不要自己猜。"""

WRITE_RE = re.compile(r"[\[［]\s*WRITE\s*[:：]\s*(.+?)\s*[\]］]\s*(?:\r?\n|$)\s*<<<\s*(?:\r?\n)(.*?)(?:\r?\n)\s*>>>", re.S | re.I)
LINE_TOOL_RE = re.compile(r"^\s*(?:[-*•]\s*)?[\[［]\s*(LS|READ|RUN|SEARCH)\s*[:：]\s*(.+?)\s*[\]］]\s*[.。]?\s*$", re.M | re.I)
PENDING = {}  # 批准键 -> {"event":Event,"allow":False}


def _fix_path(p):
    """清洗模型输出的路径：引号/括号、环境变量、~、以及把 \\t 还原成 t。"""
    p = (p or "").strip()
    if not p:
        return p
    """清洗模型输出的路径：引号/括号、环境变量、~、以及把 \\t 还原成 t。"""
    p = p.strip('"').strip("'").strip("`").strip()
    p = p.strip("[]（）").strip()
    p = os.path.expandvars(os.path.expanduser(p)).strip()
    if os.path.exists(p):
        return p
    alt = p.replace("\t", "t")
    return alt if os.path.exists(alt) else p


def exec_tool(tool, arg, block=None):
    """执行一个工具调用，返回结果字符串（截断）。调用方已保证批准。"""
    try:
        if tool == "LS":
            arg = _fix_path(arg)
            if not os.path.isdir(arg):
                return f"[LS {arg}] 不是目录"
            items = sorted(os.listdir(arg))[:60]
            out = [i + ("/" if os.path.isdir(os.path.join(arg, i)) else "") for i in items]
            # 附上可直接 READ 的关键文件全路径（两层内），杜绝模型猜路径
            keys = []
            for dirpath, dirs, fs in os.walk(arg):
                dirs[:] = [d for d in dirs
                           if not d.startswith((".", "__"))
                           and d not in ("node_modules", "dist", "build", "__pycache__")]
                if dirpath.count(os.sep) - arg.count(os.sep) > 1:
                    dirs[:] = []
                    continue
                for f in fs:
                    if re.search(r"(?i)(readme|main|app|index|package|requirements|setup|config|\.py$|\.js$)",
                                 f) and not f.endswith((".log", ".bak")):
                        keys.append(os.path.join(dirpath, f))
                if len(keys) > 14:
                    break
            extra = ("\n可直接 [READ:] 的关键文件（真实存在）：\n" +
                     "\n".join(keys[:14])) if keys else ""
            return (f"[LS {arg}]\n" + "\n".join(out) +
                    f"\n（共 {len(items)} 项，最多显示60）" + extra)
        if tool == "READ":
            arg = _fix_path(arg)
            if not os.path.isfile(arg):
                d = os.path.dirname(arg) or "."
                sibs = ", ".join(sorted(os.listdir(d))[:20]) if os.path.isdir(d) else "目录也不存在"
                return (f"[READ {arg}] 文件不存在（不是权限问题）。该目录下实际有：{sibs}。"
                        "请从这些真实文件里选。")
            with open(arg, encoding="utf-8", errors="replace") as f:
                return f"[READ {arg} 前4000字]\n" + f.read()[:4000]
        if tool == "WRITE":
            arg = _fix_path(arg)
            os.makedirs(os.path.dirname(os.path.abspath(arg)) or ".", exist_ok=True)
            with open(arg, "w", encoding="utf-8") as f:
                f.write(block or "")
            return f"[WRITE {arg}] 已写入 {len(block or '')} 字符"
        if tool == "RUN":
            r = subprocess.run(arg, shell=True, capture_output=True, text=True,
                               timeout=60, creationflags=NO_WINDOW)
            out = ((r.stdout or "") + (r.stderr or ""))[:3000]
            return f"[RUN {arg}] 退出码 {r.returncode}\n{out}"
        if tool == "SEARCH":
            if not os.path.isfile(SEARCH_SCRIPT):
                return "[SEARCH] search.py 不存在，无法搜索"
            r = subprocess.run([PYTHON_EXE, SEARCH_SCRIPT, arg, "5"],
                               capture_output=True, text=True, timeout=60,
                               encoding="utf-8", errors="replace",
                               creationflags=NO_WINDOW)
            return f"[SEARCH {arg}]\n" + (r.stdout or "")[:3000]
    except Exception as e:
        return f"[{tool} {arg}] 失败: {str(e)[:200]}"
    return f"[{tool}] 未知工具"


def parse_tools(content):
    """从模型输出提取工具调用并返回 (清理后文本, [(tool,arg,block)])。"""
    calls = []
    for m in WRITE_RE.finditer(content):
        calls.append(("WRITE", m.group(1).strip(), m.group(2)))
    cleaned = WRITE_RE.sub("[WRITE 已提取]", content)
    for m in LINE_TOOL_RE.finditer(cleaned):
        calls.append((m.group(1).upper(), m.group(2).strip(), None))
    cleaned = LINE_TOOL_RE.sub("", cleaned)
    return cleaned.strip(), calls

def heal_tool_path(tool, arg, last_user):
    """清洗工具路径；路径不存在时从用户原话中找真实存在的路径自愈。
    WRITE 的新文件路径保持原样（exec_tool 会自动创建父目录）。"""
    arg = _fix_path(arg)
    if tool == "WRITE" or os.path.exists(arg):
        return arg, ""
    for tok in re.findall(r'[A-Za-z]:[\\/][^\s，。,;：:]+', last_user or ""):
        cand = tok.rstrip('.,;，。')
        while cand:
            if os.path.exists(cand):
                return cand, f"（原路径不存在，已按你的原话改用 {cand}）"
            cand = cand.rstrip("\\/") \
                if "\\" not in cand[3:] and "/" not in cand[3:] else \
                cand[:max(cand.rfind("\\"), cand.rfind("/"))]
    return arg, ""


# ---------------------------------------------------------------- 权限梯度（readonly/plan/ask/yolo）
# 四档递进：只读(只查不改) → 计划(查+预览改动不执行) → 询问(查自动+写需批准) → 自动(全自动)
PERM_LEVELS = ["readonly", "plan", "ask", "yolo"]


def perm_policy(level):
    """返回 (规范档位, 工具策略)。策略决定每个工具：auto / confirm / preview / block。"""
    level = level or "ask"
    if level not in PERM_LEVELS:
        level = "ask"
    policy = {"auto": {"LS", "READ", "SEARCH"},
              "confirm": set(), "preview": set(), "block": set()}
    if level == "readonly":
        policy["block"] = {"WRITE", "RUN"}
    elif level == "plan":
        policy["preview"] = {"WRITE", "RUN"}
    elif level == "ask":
        policy["confirm"] = {"WRITE", "RUN"}
    elif level == "yolo":
        policy["auto"] = {"LS", "READ", "SEARCH", "WRITE", "RUN"}
    return level, policy


PERM_SUFFIX = {
    "readonly": "\n[权限] 当前为只读模式：你只能使用 LS/READ/SEARCH 查看本机文件，WRITE/RUN 已禁用。需要修改文件时请告诉用户切换到更高权限。",
    "plan": "\n[权限] 当前为计划模式：你可列目录/读文件，但 WRITE/RUN 不会真正执行，只把计划展示给你确认。请聚焦给出方案。",
    "ask": "\n[权限] 当前为询问模式：LS/READ/SEARCH 自动执行；WRITE/RUN 需用户逐次批准后才执行。",
    "yolo": "\n[权限] 当前为全自动模式：所有工具（含 WRITE/RUN）自动执行，你可直接读写文件与运行命令。",
}


def chat_generate(gen_id, model, msgs, max_tokens, temperature, sid, msg_id,
                  permission="ask", ev_extra=None):
    """带工具循环的聊天生成（/api/chat 与天团 run_step 共用）。流式直播 + 工具执行 + 批准门。
    permission 控制工具梯度：readonly/plan/ask/yolo；ev_extra 透传给 WebSocket 事件（天团步骤带 team 标记）。"""
    t0 = time.time()
    set_busy(model, f"会话#{sid} 聊天")
    total_stats = {"prompt_tokens": 0, "completion_tokens": 0}
    tool_log = []
    final_text = ""
    thinking_all = ""
    last_user = msgs[-1]["content"] if msgs else ""

    def push(kind, payload=""):
        ev = {"type": kind, "session_id": sid, "msg_id": msg_id,
              "model": model, "payload": payload}
        ev.update(ev_extra or {})
        hub.emit(ev)

    try:
        level, policy = perm_policy(permission)
        tool_prompt = TOOL_PROMPT + PERM_SUFFIX.get(level, "")
        msgs[-1]["content"] = msgs[-1]["content"] + tool_prompt

        # 工具模式低温：实测 qwen 系在温度>0.4 时会抄错路径/漏字符
        eff_temp = min(temperature if temperature is not None else 0.7, 0.3)
        for round_no in range(TOOL_ROUNDS + 1):
            content, thinking, stats = ollama_stream(
                model, msgs, max_tokens, gen_id,
                on_delta=lambda d: push("chat_delta", d),
                on_thinking=lambda t: push("chat_thinking", t),
                temperature=eff_temp)
            total_stats["prompt_tokens"] += stats["prompt_tokens"]
            total_stats["completion_tokens"] += stats["completion_tokens"]
            thinking_all += (("\n" if thinking_all else "") + thinking)
            cleaned, calls = parse_tools(content) if level != "off" else (content, [])
            final_text = cleaned
            if not calls or round_no == TOOL_ROUNDS:
                # 兜底：第一轮没调工具但用户消息里有真实路径 → 自动 LS 塞回真实结果
                if level != "off" and not calls and round_no == 0:
                    m = re.search(r'[A-Za-z]:[\\/][^\s，。,;：:]+', last_user)
                    cand = m.group(0).rstrip('.,;，。') if m else ""
                    target = None
                    while cand:
                        if os.path.exists(cand):
                            target = cand
                            break
                        cut = max(cand.rfind("\\"), cand.rfind("/"))
                        cand = cand[:cut] if cut > 2 else ""
                    if target:
                        if os.path.isfile(target):
                            target = os.path.dirname(target) or "."
                        res = exec_tool("LS", target)
                        tool_log.append(f"LS {target} → 自动执行(取自你的消息)")
                        hub.emit({"type": "tool_result", "session_id": sid, "msg_id": msg_id,
                                  "payload": f"LS {target[:80]} → 已自动执行",
                                  "excerpt": res[:400]})
                        push("chat_delta", "\n\n[已自动读取目录，继续处理…]\n")
                        msgs = [
                            {"role": "user", "content": last_user + tool_prompt},
                            {"role": "assistant", "content": final_text[:4000]},
                            {"role": "user", "content":
                             f"系统已自动执行 [LS: {target}]，真实结果：\n{res[:3500]}\n"
                             "基于真实结果继续完成任务；需要更多文件内容就用 [READ:]（路径从上面真实列出的文件里选），"
                             "信息足够就直接给最终分析。"}]
                        continue
                break
            results = []
            for tool, arg, block in calls[:4]:
                fixed = ""
                if tool in ("LS", "READ", "WRITE"): arg, fixed = heal_tool_path(tool, arg, last_user)
                    # arg = _fix_path(arg)
                    # if (needs_heal := (not os.path.isdir(os.path.dirname(os.path.abspath(arg)) or ".")) if tool == "WRITE" else (not os.path.exists(arg))):
                          # if needs_heal:
                            # original_arg = arg
                        # 路径自愈：模型抄错时，从用户原话里找真实存在的路径
                        # for tok in re.findall(r'[A-Za-z]:[\\/][^\s，。,;：:]+', last_user):
                            # cand = tok.rstrip('.,;，。')
                            # while cand:
                                # if os.path.exists(cand):
                                    # fixed = f"（原路径不存在，已按你的原话改用 {cand}）"
                                    # arg = os.path.join(cand, os.path.basename(original_arg)) if tool == "WRITE" and os.path.basename(original_arg) else cand
                                    # break
                                # cand = cand.rstrip("\\/") \
                                    # if "\\" not in cand[3:] and "/" not in cand[3:] else \
                                    # cand[:max(cand.rfind("\\"), cand.rfind("/"))]
                            # if fixed:
                                # break
                if tool in policy["auto"]:
                    status = "auto"
                    res = exec_tool(tool, arg, block)
                    tool_log.append(f"{tool} {arg} → auto{fixed}")
                    hub.emit({"type": "tool_result", "session_id": sid, "msg_id": msg_id,
                              "payload": f"{tool} {arg[:80]} → 已执行",
                              "excerpt": res[:400]})
                    results.append(res[:3500])
                    continue
                if tool in policy["preview"]:
                    pv = (f"拟写入内容预览：\n{block[:2000]}" if tool == "WRITE" and block
                          else f"拟执行命令：{arg[:2000]}" if tool == "RUN"
                          else f"参数：{arg[:2000]}")
                    msg = f"[{tool} {arg}] 计划模式：不会真正执行。\n{pv}"
                    tool_log.append(f"{tool} {arg} → planned(未执行){fixed}")
                    hub.emit({"type": "tool_result", "session_id": sid, "msg_id": msg_id,
                              "payload": f"{tool} {arg[:80]} → 计划(未执行)",
                              "excerpt": pv[:400]})
                    results.append(msg[:3500])
                    continue
                if tool in policy["block"]:
                    msg = f"[{tool} {arg}] 权限不足：当前为只读模式，WRITE/RUN 已禁用，跳过。{fixed}"
                    tool_log.append(f"{tool} {arg} → blocked")
                    hub.emit({"type": "tool_result", "session_id": sid, "msg_id": msg_id,
                              "payload": f"{tool} {arg[:80]} → 已拦截(只读)",
                              "excerpt": msg[:400]})
                    results.append(msg[:3500])
                    continue
                # 余下 WRITE/RUN：需用户逐次批准（ask 档）
                key = f"{gen_id}-{len(tool_log)}"
                ev = threading.Event()
                PENDING[key] = {"event": ev, "allow": False}
                hub.emit({"type": "tool_confirm", "session_id": sid, "msg_id": msg_id,
                          "key": key, "tool": tool, "arg": arg[:200],
                            "detail": ((block or "")[:800] if tool == "WRITE" else ""),
                          "payload": f"{tool} {arg[:120]}"})
                ok = False
                for _ in range(180):  # 等批准，每秒检查一次取消，点「停止」立刻生效
                    if ev.wait(timeout=1):
                        ok = True
                        break
                    if ACTIVE.get(gen_id, {}).get("cancel"):
                        break
                entry = PENDING.pop(key, None)
                if not ok or not (entry and entry["allow"]):
                    status = "timeout" if not ok else "denied"
                    res = f"[{tool} {arg}] {'等待批准超时' if not ok else '用户拒绝'}，跳过"
                    tool_log.append(f"{tool} {arg} → {status}")
                    hub.emit({"type": "tool_result", "session_id": sid, "msg_id": msg_id,
                                "key": key,
                              "payload": f"{tool} {arg[:80]} → {status}",
                              "excerpt": ""})
                    results.append(res)
                    continue
                status = "approved"
                res = exec_tool(tool, arg, block)
                tool_log.append(f"{tool} {arg} → {status}{fixed}")
                hub.emit({"type": "tool_result", "session_id": sid, "msg_id": msg_id,
                            "key": key,
                          "payload": f"{tool} {arg[:80]} → 已执行",
                          "excerpt": res[:400]})
                results.append(res[:3500])
            push("chat_delta", "\n\n[工具已执行，继续处理…]\n")
            msgs = [
                {"role": "user", "content": last_user + tool_prompt},
                {"role": "assistant", "content": final_text[:6000]},
                {"role": "user", "content":
                 "--- 工具结果 ---\n" + "\n\n".join(results) +
                 "\n--- 基于以上真实结果继续完成任务；信息足够就直接给最终答案"
                 "（不要再输出工具调用）。铁律：工具结果里没有的内容绝对不能编造——"
                 "文件不存在就不能自己写文件内容，只能 READ 真实列出的文件 ---"}]
        duration_ms = int((time.time() - t0) * 1000)
        if tool_log:
            final_text += "\n\n--- 工具轨迹 ---\n" + "\n".join(tool_log)
        with sqlite3.connect(DATABASE) as conn:
            conn.execute("""UPDATE messages SET content=?, thinking=?, model=?, tokens=?,
                            duration_ms=? WHERE id=?""",
                         (final_text, thinking_all, model, total_stats["completion_tokens"],
                          duration_ms, msg_id))
            conn.execute("UPDATE sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (sid,))
            conn.commit()
        log_usage(model, last_user, total_stats["prompt_tokens"],
                  total_stats["completion_tokens"], len(final_text))
        push("chat_done", {"tokens": total_stats["completion_tokens"],
                             "content": final_text,
                           "tok_s": round(total_stats["completion_tokens"] /
                                          (duration_ms / 1000), 1) if duration_ms else 0,
                           "duration_ms": duration_ms, "tools": len(tool_log)})
        # 返回与旧 generate() 同形元组，供天团 run_step 解包
        return final_text, thinking_all, total_stats, duration_ms
    except Exception as e:
        err = "已取消" if "已取消" in str(e) else str(e)[:300]
        with sqlite3.connect(DATABASE) as conn:
            conn.execute("UPDATE messages SET model=? WHERE id=?", (model, msg_id))
            conn.commit()
        push("chat_error", err)
        for _key in [k for k in list(PENDING) if k.startswith(gen_id + "-")]:
            _entry = PENDING.pop(_key, None)
            if _entry:
                _entry["allow"] = False
                _entry["event"].set()
    finally:
        for _key in [k for k in list(PENDING) if k.startswith(gen_id + "-")]:
            _entry = PENDING.pop(_key, None)
            if _entry:
                _entry["allow"] = False
                _entry["event"].set()
        set_busy(model, None)
        ACTIVE.pop(gen_id, None)


@app.post("/api/tool/resolve")
async def tool_resolve(inp: ToolResolve):
    p = PENDING.get(inp.key)
    if not p:
        return {"ok": False}
    p["allow"] = inp.allow
    p["event"].set()
    return {"ok": True}


@app.post("/api/chat")
async def chat(inp: ChatIn):
    if not inp.message.strip():
        raise HTTPException(400, "消息不能为空")
    if not ensure_ollama():
        raise HTTPException(503, "Ollama 未运行且自动拉起失败，请手动启动 Ollama")
    if inp.session_id:
        sid = inp.session_id
        with sqlite3.connect(DATABASE) as conn:
            if not conn.execute("SELECT 1 FROM sessions WHERE id=?", (sid,)).fetchone():
                raise HTTPException(404, "会话不存在")
    else:
        sid = new_session(inp.message[:20])

    model = inp.model if inp.model and inp.model != "auto" else None
    how = "手动指定"
    if not model:
        hub.emit({"type": "router_picking", "session_id": sid, "payload": "路由器正在选模型…"})
        model, how = route_model(inp.message)

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.execute(
            "INSERT INTO messages (session_id, role, content, model) VALUES (?,?,?,?)",
            (sid, "user", inp.message, None))
        user_id = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO messages (session_id, role, content, model) VALUES (?,?,?,?)",
            (sid, "assistant", "", model))
        msg_id = cur.lastrowid
        conn.execute("UPDATE sessions SET title=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                     (inp.message[:30], sid))
        conn.commit()

    gen_id = f"chat-{msg_id}"
    ACTIVE[gen_id] = {"cancel": False, "session_id": sid}
    msgs = history_messages(sid, max(2, inp.context))
    if msgs and (inp.skills or inp.agent):
        msgs[-1]["content"] = inject_caps(msgs[-1]["content"], inp.skills, inp.agent)
        hub.emit({"type": "caps_loaded", "session_id": sid,
                  "payload": f"已注入 {len(inp.skills)} 个技能" +
                             (f" + 角色[{inp.agent}]" if inp.agent else "")})
    if inp.tools:
        threading.Thread(
            target=chat_generate, daemon=True,
            args=(gen_id, model, msgs, inp.max_tokens, inp.temperature, sid, msg_id,
                  inp.permission)).start()
    else:
        threading.Thread(
            target=generate, daemon=True,
            args=(gen_id, model, msgs, inp.max_tokens, {}, sid, msg_id, f"会话#{sid} 聊天"),
            kwargs={"temperature": inp.temperature}).start()

    hub.emit({"type": "chat_start", "session_id": sid, "msg_id": msg_id,
              "model": model, "payload": how, "user_id": user_id})
    return {"session_id": sid, "msg_id": msg_id, "model": model, "routed_by": how}


@app.post("/api/chat/cancel")
async def cancel_chat(inp: CancelIn):
    n = 0
    for gid, g in list(ACTIVE.items()):
        if g.get("session_id") == inp.session_id:
            g["cancel"] = True
            n += 1
    hub.emit({"type": "chat_cancelled", "session_id": inp.session_id})
    return {"cancelled": n}

# ---------------------------------------------------------------- 天团模式（自适应循环：干到完成为止）

def _substitute(model, inst):
    """未安装则换成本机有的。返回 (model, note)。"""
    if not inst or model in inst:
        return model, ""
    alt = inst[0]
    return alt, f"（{model} 未装，{alt} 替补）"


def pick_fixer(verdict, inst):
    """按验收意见关键词派最合适的修复专家。"""
    kw = verdict.lower()
    for kws, m in FIXER_HINTS:
        if any(k in kw for k in kws):
            return _substitute(m, inst)
    return _substitute("qwen3:14b", inst)


def verdict_pass(v):
    first = next((l for l in v.splitlines() if l.strip()), "")
    up = first.upper()
    return "PASS" in up and "FAIL" not in up


def run_team(run_id, sid, task, max_rounds=6, permission="ask"):
    """线程：初稿（按任务类型派最合适模型）→ 主审验收 → 不合格派对应专家修 → 循环到 PASS。"""
    out_dir = os.path.join(OUTPUT_DIR, f"team-{run_id}")
    os.makedirs(out_dir, exist_ok=True)
    t_run0 = time.time()
    inv = 0  # 顺序调用计数（同时作为 team_steps.step 与取消键）

    def step_msg(model_name):
        with sqlite3.connect(DATABASE) as conn:
            cur = conn.execute(
                "INSERT INTO messages (session_id, role, content, model) VALUES (?,?,?,?)",
                (sid, "assistant", "", model_name))
            conn.commit()
            return cur.lastrowid

    def run_step(label, model, prompt, max_tokens, fname, round_no, permission="ask"):
        """一次派工：落库 + 直播 + 流式生成 + 存文件。"""
        nonlocal inv
        inv += 1
        with sqlite3.connect(DATABASE) as conn:
            conn.execute("""INSERT INTO team_steps (run_id, step, name, model, status)
                            VALUES (?,?,?,?, 'running')""", (run_id, inv, label, model))
            conn.commit()
        msg_id = step_msg(model)
        hub.emit({"type": "team_step", "session_id": sid, "run_id": run_id,
                  "step": inv, "round": round_no, "max_rounds": max_rounds,
                  "name": label, "model": model, "msg_id": msg_id, "status": "running",
                  "payload": f"{label} · {model}"})
        gen_id = f"team-{run_id}-{inv}"
        ACTIVE[gen_id] = {"cancel": False, "session_id": sid}
        content, _, stats, dur = chat_generate(
            gen_id, model, [{"role": "user", "content": prompt}], max_tokens,
            None, sid, msg_id, permission,
            {"team": {"run_id": run_id, "step": inv, "name": label}})
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write(content)
        with sqlite3.connect(DATABASE) as conn:
            conn.execute("""UPDATE team_steps SET status='done', tokens=?, duration_ms=?
                            WHERE run_id=? AND step=?""",
                         (stats["completion_tokens"], dur, run_id, inv))
            conn.commit()
        hub.emit({"type": "team_step", "session_id": sid, "run_id": run_id,
                  "step": inv, "round": round_no, "max_rounds": max_rounds,
                  "name": label, "model": model, "status": "done",
                  "payload": f"{label} 完成 · {stats['completion_tokens']} tok"})
        return content

    try:
        inst = installed_chat_models()
        if not inst:
            raise RuntimeError("本机没有可用的对话模型，请先在模型页拉取")

        producer, how = route_model(task)
        role = ROSTER.get(producer, "客座")
        draft = run_step(f"初稿·{role}（{how}）", producer,
                         f"{task}\n【输出要求】只输出完整可交付内容，"
                         "不要解释、不要 Markdown 代码块标记。",
                         3000, "01-draft.txt", 0, permission)

        judge, _ = _substitute("qwen3:14b", inst)
        passed = False
        verdict = ""
        r = 0
        for r in range(1, max_rounds + 1):
            verdict = run_step(
                f"第{r}轮·主审验收", judge,
                f"你是验收官，标准从严。任务：{task}\n--- 当前成果 ---\n{draft[:9000]}\n"
                "--- 要求 ---\n第一行只写 PASS 或 FAIL。若 FAIL，接着输出：\n"
                "1) 具体问题（每条一行，指向成果里的确切位置）\n"
                "2) 最该去修的岗位（从：代码师/推理师/算法王/数学王/英文王/文书员 里选一个）",
                400, f"r{r}-verdict.txt", r, permission)
            if verdict_pass(verdict):
                passed = True
                break
            fixer, note = pick_fixer(verdict, inst)
            frole = ROSTER.get(fixer, "客座")
            issues = "\n".join(verdict.splitlines()[1:])[:2500]
            draft = run_step(
                f"第{r}轮·{frole}修复{note}", fixer,
                f"你是{frole}。任务：{task}\n主审验收意见：\n{issues}\n"
                f"--- 当前成果 ---\n{draft[:12000]}\n"
                "--- 输出修正后的完整成果（不是片段，不是解释，不要代码块标记）---",
                3000, f"r{r}-fix.txt", r, permission)

        final_path = os.path.join(out_dir, "final.txt")
        with open(final_path, "w", encoding="utf-8") as f:
            f.write(draft)
        dur_total = int((time.time() - t_run0) * 1000)
        result = "验收通过" if passed else f"{max_rounds} 轮未全过，按最佳稿定稿"
        with sqlite3.connect(DATABASE) as conn:
            conn.execute("""UPDATE team_runs SET status='done', result_path=?,
                            finished_at=CURRENT_TIMESTAMP WHERE id=?""",
                         (final_path, run_id))
            conn.execute("UPDATE sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (sid,))
            conn.commit()
        hub.emit({"type": "team_done", "session_id": sid, "run_id": run_id,
                  "payload": {"result_path": final_path, "duration_ms": dur_total,
                              "rounds": r, "passed": passed, "result": result}})
    except Exception as e:
        err = "已取消" if "已取消" in str(e) else str(e)[:300]
        with sqlite3.connect(DATABASE) as conn:
            conn.execute("""UPDATE team_runs SET status=?, error=?,
                            finished_at=CURRENT_TIMESTAMP WHERE id=?""",
                         ("cancelled" if err == "已取消" else "failed",
                          err.replace("'", ""), run_id))
            conn.execute("""UPDATE team_steps SET status='failed'
                            WHERE run_id=? AND status='running'""", (run_id,))
            conn.commit()
        hub.emit({"type": "team_error", "session_id": sid, "run_id": run_id, "payload": err})
    finally:
        for k in [k for k in list(ACTIVE) if k.startswith(f"team-{run_id}-")]:
            ACTIVE.pop(k, None)


@app.post("/api/team")
async def team_run(inp: TeamIn):
    if not inp.task.strip():
        raise HTTPException(400, "任务不能为空")
    if not ensure_ollama():
        raise HTTPException(503, "Ollama 未运行且自动拉起失败")
    if inp.session_id:
        sid = inp.session_id
    else:
        sid = new_session("[天团] " + inp.task[:20])
    with sqlite3.connect(DATABASE) as conn:
        if not conn.execute("SELECT 1 FROM sessions WHERE id=?", (sid,)).fetchone():
            raise HTTPException(404, "会话不存在")
        cur = conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?,?,?)",
            (sid, "user", inp.task))
        user_id = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO team_runs (session_id, task) VALUES (?,?)", (sid, inp.task))
        run_id = cur.lastrowid
        conn.execute("UPDATE sessions SET title=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                     (("[天团] " + inp.task[:28]), sid))
        conn.commit()
    threading.Thread(target=run_team,
                     args=(run_id, sid, inject_caps(inp.task, inp.skills, inp.agent),
                           inp.max_rounds, inp.permission),
                     daemon=True).start()
    hub.emit({"type": "team_start", "session_id": sid, "run_id": run_id,
              "user_id": user_id, "payload": f"天团自适应循环启动（最多 {inp.max_rounds} 轮）"})
    return {"session_id": sid, "run_id": run_id}


@app.get("/api/team/runs")
async def team_runs():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""SELECT r.*, GROUP_CONCAT(
                              s.step || ':' || s.status || ':' || IFNULL(s.tokens,0)) AS steps
                              FROM team_runs r LEFT JOIN team_steps s ON s.run_id=r.id
                              GROUP BY r.id ORDER BY r.id DESC LIMIT 30""").fetchall()
    return [dict(r) for r in rows]

# ---------------------------------------------------------------- 战报（结束复盘，零 token：纯本地数据聚合）

def _env_snapshot():
    """本机环境一行档：OS/GPU/Ollama/量化——云端模型判断瓶颈的关键。"""
    import platform
    lines = [f"{platform.system()} {platform.release()} · Python {platform.python_version()}"]
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                            "--format=csv,noheader"], capture_output=True, text=True,
                           timeout=6, creationflags=NO_WINDOW)
        if r.returncode == 0 and r.stdout.strip():
            lines.append("GPU: " + r.stdout.strip().splitlines()[0].strip())
    except Exception:
        lines.append("GPU: 未识别（可能无独显，全部 CPU 推理）")
    try:
        exe = CONFIG.get("ollama_path") or OLLAMA_EXE
        r = subprocess.run([exe if os.path.isfile(exe) else "ollama", "--version"],
                           capture_output=True, text=True, timeout=6, creationflags=NO_WINDOW)
        ver = (r.stdout or r.stderr).strip().splitlines()[:1]
        if ver:
            lines.append(ver[0])
    except Exception:
        pass
    tags = installed_models()
    if tags:
        ms = ", ".join(f"{n}({v['size_gb']}G{',' + v['quant'] if v.get('quant') else ''})"
                       for n, v in sorted(tags.items()))
        lines.append(f"已装 {len(tags)} 个: {ms}")
    return lines


def build_report(session_id):
    """聚合会话/近 24h 全部记录 → 战报 dict。不调任何模型，零 token 消耗。"""
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        if session_id:
            msgs = conn.execute("""SELECT * FROM messages WHERE session_id=?
                                   ORDER BY id""", (session_id,)).fetchall()
            runs = conn.execute("""SELECT * FROM team_runs WHERE session_id=?
                                   ORDER BY id""", (session_id,)).fetchall()
            scope = f"会话 #{session_id}"
        else:
            msgs = conn.execute("""SELECT * FROM messages WHERE created_at >=
                                   datetime('now','-1 day') ORDER BY id""").fetchall()
            runs = conn.execute("""SELECT * FROM team_runs WHERE created_at >=
                                   datetime('now','-1 day') ORDER BY id""").fetchall()
            scope = "近 24 小时"

        people = {}
        for m in msgs:
            if m["role"] != "assistant" or not m["model"]:
                continue
            p = people.setdefault(m["model"], {"calls": 0, "tokens": 0, "chars": 0,
                                               "secs": 0.0, "fails": 0})
            p["calls"] += 1
            p["tokens"] += m["tokens"] or 0
            p["chars"] += len(m["content"] or "")
            p["secs"] += (m["duration_ms"] or 0) / 1000
            if not (m["content"] or "").strip():
                p["fails"] += 1

        stuck = []
        for r in runs:
            steps = conn.execute("""SELECT * FROM team_steps WHERE run_id=?
                                    ORDER BY step""", (r["id"],)).fetchall()
            for s in steps:
                if s["status"] in ("failed", "cancelled"):
                    stuck.append(f"天团#{r['id']} 第{s['step']}步 {s['name']}（{s['model']}）：{s['status']}")
            if r["status"] == "failed":
                stuck.append(f"天团#{r['id']} 整体失败：{(r['error'] or '')[:80]}")
        failed_tasks = conn.execute("""SELECT id, command, error FROM tasks
                                       WHERE status='failed' AND created_at >=
                                       datetime('now','-1 day') ORDER BY id""").fetchall()
        for t in failed_tasks:
            stuck.append(f"任务#{t['id']} {(t['command'] or '')[:30]}：{(t['error'] or '')[:60]}")

        files = []
        excerpts = []
        for r in runs:
            rp = r["result_path"]
            if rp and os.path.isdir(os.path.dirname(rp)):
                for f in sorted(os.listdir(os.path.dirname(rp))):
                    fp = os.path.join(os.path.dirname(rp), f)
                    files.append({"run": r["id"], "file": f,
                                  "kb": round(os.path.getsize(fp) / 1024, 1)})
                for fname in ("final.txt", "04-final.txt"):
                    final = os.path.join(os.path.dirname(rp), fname)
                    if os.path.isfile(final):
                        txt = open(final, encoding="utf-8", errors="replace").read()
                        excerpts.append(f"天团#{r['id']} 定稿前300字: {txt[:300]}")
                        break
        tried = []
        for r in runs:
            if r["status"] == "cancelled":
                tried.append(f"天团#{r['id']} 被手动中断")
            steps = conn.execute("SELECT name FROM team_steps WHERE run_id=?",
                                 (r["id"],)).fetchall()
            for s in steps:
                if "未安装" in (s["name"] or "") or "替补" in (s["name"] or ""):
                    tried.append(f"天团#{r['id']} {s['name']}")
        biggest = max((m for m in msgs if m["role"] == "assistant" and m["content"]),
                      key=lambda m: len(m["content"]), default=None)
        if biggest:
            excerpts.append(f"最长回复({biggest['model']}) 前300字: {biggest['content'][:300]}")

    compromises = []
    for model, p in people.items():
        if p["calls"] >= 1 and p["tokens"] >= 1900:
            compromises.append(f"{model} 的输出疑似顶到 token 上限被截断（单次 ≥1900 tok）")
        if p["secs"] > 5 and p["tokens"] / p["secs"] < 8:
            compromises.append(f"{model} 平均 {p['tokens']/p['secs']:.1f} tok/s —— 显存不足、部分落 CPU")
    quants = {v.get("quant") for v in installed_models().values() if v.get("quant")}
    if quants:
        compromises.append("模型均为 " + "/".join(sorted(quants)) + " 量化（省显存换精度）")
    total_tok = sum(p["tokens"] for p in people.values())
    if total_tok > 20000:
        compromises.append(f"全程 {total_tok:,} token 全走本地——同等量走云端 API 约 ${
            round(total_tok/1e6*15, 2)} 已省下")

    return {
        "scope": scope,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "env": _env_snapshot(),
        "people": [{"model": m, "role": ROSTER.get(m, "客座"), **p}
                   for m, p in sorted(people.items(), key=lambda x: -x[1]["tokens"])],
        "stuck": stuck,
        "tried": tried,
        "files": files,
        "excerpts": excerpts,
        "compromises": compromises,
        "runs": [{"id": r["id"], "task": r["task"][:40], "status": r["status"]}
                 for r in runs],
    }


REPORT_TMPL = """# 本地模型天团战报（喂给云端专家模型：读完直接开药方）

> 指令：你是资深工程专家。下面是本地小模型团队的真实工作档案。
> 请输出：1) 根因清单（按可能性排序，对应「卡点」每条）2) 每条的具体修复动作（可执行步骤/命令/代码）
> 3) 在当前算力约束下值得做的替代方案。不要复述本报告，不要客套。

## 0. 环境（诊断上下文）
{env}

## 1. 任务
范围：{scope}
{runs}

## 2. 出勤（谁做了什么）
{people}

## 3. 卡点（原样错误，未解决——请逐条对症下药）
{stuck}

## 4. 已尝试（不要重复建议这些）
{tried}

## 5. 算力约束（修复方案必须在此预算内）
{compromises}

## 6. 产物
{changes}

## 7. 关键摘录
{excerpts}
"""


def write_report(data):
    folder = os.path.join(REPORT_DIR,
                          "battle-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(folder, exist_ok=True)
    people = "\n".join(
        f"- {p['role']} {p['model']}：{p['calls']} 次 · {p['tokens']:,} token · "
        f"{p['chars']:,} 字符 · {p['secs']:.0f}s"
        + (f" · {p['tokens']/p['secs']:.1f} tok/s" if p["secs"] > 3 else "")
        + (f" · ⚠{p['fails']} 次空输出" if p["fails"] else "")
        for p in data["people"]) or "- （无记录）"
    stuck = "\n".join(f"- {s}" for s in data["stuck"]) or "- 无（仍请检查「算力约束」是否有隐患）"
    tried = "\n".join(f"- {t}" for t in data["tried"]) or "- 无特殊操作"
    comp = "\n".join(f"- {c}" for c in data["compromises"]) or "- 无明显妥协"
    changes = "\n".join(
        f"- 天团#{f['run']} → {f['file']}（{f['kb']}KB）" for f in data["files"]) \
        or "- 未产出文件（纯对话任务）"
    excerpts = "\n".join(f"- {e}" for e in data["excerpts"]) or "- 无"
    runs = "\n".join(f"- #{r['id']} [{r['status']}] {r['task']}" for r in data["runs"]) \
        or "- 无天团运行"
    md = REPORT_TMPL.format(
        env="\n".join("- " + e for e in data["env"]),
        people=people, stuck=stuck, tried=tried, compromises=comp,
        changes=changes, excerpts=excerpts, runs=runs, scope=data["scope"])
    with open(os.path.join(folder, "REPORT.md"), "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(folder, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return folder, md


@app.post("/api/report")
async def make_report(inp: ReportIn):
    data = build_report(inp.session_id)
    folder, _ = write_report(data)
    hub.emit({"type": "report_done", "payload": folder})
    try:
        os.startfile(folder)  # 直接打开文件夹
    except Exception:
        pass
    return {"path": folder, "summary": data}


@app.post("/api/open-ollama-download")
async def open_ollama_download():
    """首次使用引导：没装 Ollama 的机器上一键打开下载页。"""
    import webbrowser
    webbrowser.open("https://ollama.com/download")
    return {"ok": True}

# ---------------------------------------------------------------- 项目面板（D:\ai-projects-2026 等）

_projects_cache = {"at": 0.0, "data": None}


def project_roots():
    roots = list(CONFIG.get("project_dirs") or [])
    default = r"D:\ai-projects-2026"
    if os.path.isdir(default) and default not in roots:
        roots.append(default)
    return [r for r in roots if os.path.isdir(r)]


@app.get("/api/projects")
async def list_projects():
    """扫描项目根目录（config.json 的 project_dirs 可加），给控制台「项目」面板。"""
    if _projects_cache["data"] is not None and time.time() - _projects_cache["at"] < 60:
        return _projects_cache["data"]
    out = []
    for root in project_roots():
        try:
            entries = sorted(os.listdir(root))
        except Exception:
            continue
        for name in entries:
            p = os.path.join(root, name)
            if not os.path.isdir(p) or name.startswith((".", "__")):
                continue
            n_files, total, newest = 0, 0, 0.0
            for dirpath, dirs, fs in os.walk(p):
                dirs[:] = [d for d in dirs
                           if not d.startswith((".", "__")) and d not in ("node_modules",)]
                if n_files > 3000:
                    break
                for f in fs:
                    n_files += 1
                    try:
                        st = os.stat(os.path.join(dirpath, f))
                        total += st.st_size
                        newest = max(newest, st.st_mtime)
                    except Exception:
                        pass
            desc = ""
            for cand in ("README.md", "readme.md"):
                rp = os.path.join(p, cand)
                if os.path.isfile(rp):
                    txt = open(rp, encoding="utf-8", errors="replace").read()
                    lines = [l.strip() for l in txt.splitlines()
                             if l.strip() and not l.lstrip().startswith("#")]
                    desc = lines[0][:80] if lines else ""
                    break
            has = lambda d: os.path.isdir(os.path.join(p, d))
            kind = ("全栈" if has("backend") and has("frontend")
                    else "后端" if has("backend") else "前端" if has("frontend") else "资料")
            out.append({"name": name, "path": p, "kind": kind, "files": n_files,
                        "size_mb": round(total / 1e6, 1),
                        "modified": (datetime.fromtimestamp(newest).strftime("%m-%d %H:%M")
                                     if newest else ""),
                        "desc": desc})
    data = {"roots": project_roots(), "projects": out}
    _projects_cache.update(at=time.time(), data=data)
    return data


# ---------------------------------------------------------------- 模型管理（预热/卸载/拉取/打开目录）

def _ollama_post(path, payload, timeout=30):
    req = urllib.request.Request(f"{OLLAMA_URL}{path}",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=timeout)


@app.post("/api/model/warm")
async def model_warm(inp: ModelIn):
    """预热驻留（keep_alive 30m）——天团开跑前先把要用的模型装进显存。"""
    if not ensure_ollama():
        raise HTTPException(503, "Ollama 未运行")

    def _warm():
        set_busy(inp.model, "预热装填")
        try:
            _ollama_post("/api/generate", {"model": inp.model, "prompt": "",
                                           "keep_alive": "30m"}, timeout=300)
            hub.emit({"type": "models_changed"})
            hub.emit({"type": "warm_done", "payload": f"{inp.model} 已驻留显存(30分钟)"})
        except Exception as e:
            hub.emit({"type": "warm_done", "payload": f"{inp.model} 预热失败: {str(e)[:120]}"})
        finally:
            set_busy(inp.model, None)

    threading.Thread(target=_warm, daemon=True).start()
    return {"ok": True, "message": f"正在把 {inp.model} 装进显存…"}


@app.post("/api/model/unload")
async def model_unload(inp: ModelIn):
    """卸载释放显存（keep_alive=0）。"""
    try:
        _ollama_post("/api/generate", {"model": inp.model, "keep_alive": 0})
        hub.emit({"type": "models_changed"})
        return {"ok": True, "message": f"{inp.model} 已卸载"}
    except Exception as e:
        raise HTTPException(500, str(e)[:200])


@app.post("/api/model/pull")
async def model_pull(inp: ModelIn):
    """一键拉模型（新机器首装）。进度事件推给时间线。"""
    exe = CONFIG.get("ollama_path") or (OLLAMA_EXE if os.path.isfile(OLLAMA_EXE) else "ollama")

    def _pull():
        try:
            r = subprocess.Popen([exe, "pull", inp.model], stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True,
                                 encoding="utf-8", errors="replace",
                                 creationflags=NO_WINDOW)
            last = ""
            for line in r.stdout:
                m = re.search(r"(\d+)%", line)
                if m and line.strip() != last:
                    last = line.strip()
                    hub.emit({"type": "pull_progress",
                              "payload": f"拉取 {inp.model} {m.group(1)}%"})
            r.wait()
            hub.emit({"type": "pull_progress",
                      "payload": f"{'完成' if r.returncode == 0 else '失败'}：{inp.model}"})
            hub.emit({"type": "models_changed"})
        except Exception as e:
            hub.emit({"type": "pull_progress", "payload": f"拉取失败: {str(e)[:120]}"})

    threading.Thread(target=_pull, daemon=True).start()
    return {"ok": True, "message": f"开始拉取 {inp.model}"}


@app.get("/api/autoconfig")
async def autoconfig():
    """按本机硬件给出推荐生成参数（显存→上下文/输出长度/天团轮数）。"""
    v = vram_info()
    gb = round(v["total_mb"] / 1024, 1) if v else 0
    if not v:
        rec = {"context": 6, "maxtok": 1024, "maxrounds": 3, "temp": 0.5}
        note = "未检测到独立显卡：纯 CPU 推理较慢，已调小上下文与输出，天团轮数收窄到 3 轮防久等"
    elif gb <= 6:
        rec = {"context": 8, "maxtok": 1536, "maxrounds": 4, "temp": 0.5}
        note = f"{gb}G 显存：中小模型可整卡驻留，参数已按紧凑档配置"
    elif gb <= 8:
        rec = {"context": 12, "maxtok": 2048, "maxrounds": 6, "temp": 0.7}
        note = f"{gb}G 显存：14B 级需换装（每换一个模型约 30 秒），标准档参数；跑天团前建议预热"
    elif gb <= 12:
        rec = {"context": 16, "maxtok": 3072, "maxrounds": 6, "temp": 0.7}
        note = f"{gb}G 显存：可同时驻留两个中型模型，放宽了上下文与输出"
    else:
        rec = {"context": 24, "maxtok": 4096, "maxrounds": 8, "temp": 0.7}
        note = f"{gb}G 显存：余量充足，全部放开"
    return {"vram": v, "vram_gb": gb, "recommend": rec, "note": note}


@app.post("/api/open")
async def open_folder(data: dict):
    """一键打开本地目录（白名单：内部目录 + 项目根下的路径）。"""
    what = data.get("what", "")
    if what == "path":
        path = os.path.abspath(os.path.expanduser(data.get("path", "")))
        allowed = False
        for _root in project_roots():
            try:
                _root_abs = os.path.abspath(_root)
                if path == _root_abs or os.path.commonpath([path, _root_abs]) == _root_abs:
                    allowed = True
                    break
            except ValueError:
                continue
        if not allowed:
            raise HTTPException(403, "只允许打开项目根目录下的路径")
        if not os.path.isdir(path):
            raise HTTPException(404, "目录不存在")
        os.startfile(path)
        return {"ok": True}
    target = {"reports": REPORT_DIR, "outputs": OUTPUT_DIR, "data": DATA_DIR}.get(what)
    if not target:
        raise HTTPException(400, "unknown dir")
    os.makedirs(target, exist_ok=True)
    try:
        os.startfile(target)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))

# ---------------------------------------------------------------- 兼容旧任务队列（修复版）

def process_task(task_id):
    with sqlite3.connect(DATABASE) as conn:
        row = conn.execute("SELECT command FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not row:
        return
    command = row[0]

    def set_status(status, result_path=None, error=None):
        with sqlite3.connect(DATABASE) as conn:
            conn.execute("UPDATE tasks SET status=?, result_path=?, error=? WHERE id=?",
                         (status, result_path, error, task_id))
            if status in ("done", "failed", "cancelled"):
                conn.execute("UPDATE tasks SET finished_at=CURRENT_TIMESTAMP WHERE id=?",
                             (task_id,))
            conn.commit()
        hub.emit({"type": "task_update", "payload": {"id": task_id, "status": status}})

    set_status("picking")
    model, how = route_model(command)
    hub.emit({"type": "router_pick", "payload": {"task_id": task_id, "model": model, "how": how}})
    set_status("running")
    log_path = os.path.join(LOG_DIR, f"task_{task_id}.log")
    os.makedirs(LOG_DIR, exist_ok=True)
    gen_id = f"task-{task_id}"
    ACTIVE[gen_id] = {"cancel": False, "session_id": None}
    try:
        content, _, stats, _ = generate(
            gen_id, model, [{"role": "user", "content": command}], 2048,
            {}, -1, -1, f"任务#{task_id}")
        if content:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(content)
            set_status("done", result_path=log_path)
        else:
            set_status("failed", error="空输出")
    except Exception as e:
        set_status("failed" if "已取消" not in str(e) else "cancelled", error=str(e)[:300])


@app.post("/api/task")
async def create_task(task: TaskCreate):
    if not task.command.strip():
        raise HTTPException(400, "command 不能为空")
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.execute("INSERT INTO tasks (command) VALUES (?)", (task.command,))
        task_id = cur.lastrowid
        conn.commit()
    threading.Thread(target=process_task, args=(task_id,), daemon=True).start()
    return {"task_id": task_id, "status": "queued"}


@app.get("/api/tasks")
async def get_tasks():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM tasks ORDER BY id DESC LIMIT 100").fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- 记忆库

@app.post("/api/memory")
async def store_memory(data: MemoryIn):
    if not data.project.strip() or not data.entry.strip():
        raise HTTPException(400, "project 和 entry 不能为空")
    try:
        r = subprocess.run([os.path.join(HOME, "AppData", "Local", "Programs", "Python",
                                     "Python312", "python.exe")
                        if os.path.isfile(os.path.join(HOME, "AppData", "Local", "Programs",
                                                       "Python", "Python312", "python.exe"))
                        else "python",
                        MEMORY_SCRIPT, "save", data.project, data.entry],
                       capture_output=True, text=True, timeout=60,
                       creationflags=NO_WINDOW)
          # if r.returncode != 0:
              # raise RuntimeError((r.stderr or r.stdout or "返回码 " + str(r.returncode))[:300])
        hub.emit({"type": "memory_saved", "payload": data.project})
        return {"message": f"已存入记忆库 [{data.project}]"}
    except Exception as e:
        raise HTTPException(500, str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8777)
