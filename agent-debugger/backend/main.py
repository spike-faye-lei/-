from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import requests
from typing import List, Optional
import sqlite3
import json
import itertools

app = FastAPI()

# 内存存储调用记录
class Trace(BaseModel):
    step: int
    agent: str
    input: str
    output: str
    duration_ms: int
    decision: str

traces: List[Trace] = []

# 初始化数据库连接和创建表
def init_db():
    conn = sqlite3.connect('traces.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS traces (
                    step INTEGER,
                    agent TEXT,
                    input TEXT,
                    output TEXT,
                    duration_ms INTEGER,
                    decision TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

@app.post("/api/trace")
async def add_trace(trace: Trace):
    if len(traces) > 1000:  # 假设最大长度限制为1000
        traces.pop(0)
    traces.append(trace)
    # 持久化到SQLite
    with sqlite3.connect('traces.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO traces (step, agent, input, output, duration_ms, decision) VALUES (?, ?, ?, ?, ?, ?)",
                  (trace.step, trace.agent, trace.input, trace.output, trace.duration_ms, trace.decision))
        conn.commit()
    return {"message": "Trace added successfully"}

@app.get("/api/traces", response_model=List[Trace])
async def get_traces(agent: Optional[str] = Query(None)):
    if agent:
        return [t for t in traces if t.agent == agent]
    return traces

@app.post("/api/replay/{id}")
async def replay_trace(id: int):
    if id < 0 or id >= len(traces):
        raise HTTPException(status_code=404, detail='Trace not found')
    trace = traces[id]
    return {
        "input": trace.input,
        "output": trace.output,
        "decision": trace.decision
    }

@app.post("/api/analyze")
async def analyze_traces():
    # 获取最近20步
    recent_traces = traces[-20:]
    
    # 调用本地LLM进行分析
    response = requests.post(
        "http://127.0.0.1:4000/v1/chat/completions",
        headers={
            "Authorization": "Bearer sk-local"
        },
        json={
            "model": "ollama/qwen3:14b",
            "messages": [
                {
                    "role": "system",
                    "content": "分析最近20步的调用记录，找出异常决策（超时/重复/错误），输出 [{step, issue, suggestion}]"
                },
                {
                    "role": "user",
                    "content": json.dumps([t.model_dump() for t in recent_traces])
                }
            ]
        },
        timeout=10
    )
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="LLM analysis failed")
    
    return response.json()

@app.get("/api/diff")
async def diff_traces():
    # 假设我们有两个trace列表 trace1 和 trace2
    trace1 = traces[:10]
    trace2 = traces[10:20]
    
    if len(traces) < 20:
        return []
    
    diff_results = []
    for t1, t2 in itertools.zip_longest(trace1, trace2):
        if t1 and t2 and t1.input == t2.input and t1.decision != t2.decision:
            diff_results.append({
                "step": t1.step,
                "decision1": t1.decision,
                "decision2": t2.decision
            })
    
    return diff_results