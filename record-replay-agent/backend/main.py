from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import os
import logging
import json
import re
import aiohttp

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 内存中存储操作序列
records = {}

class Step(BaseModel):
    action: str
    selector: str
    value: str

class Record(BaseModel):
    name: str
    steps: list[Step]

class ReplayResult(BaseModel):
    executable: bool
    risk: str
    suggestion: str

# 风险映射
risk_mapping = {
    "低": 1,
    "中": 2,
    "高": 3
}

# 1) POST /api/record——接收操作序列并存入内存
@app.post("/api/record")
async def record_operation(record: Record):
    # 输入验证
    if not record.name or not record.steps:
        logger.error("Invalid input data: name or steps is missing.")
        raise HTTPException(status_code=400, detail="Invalid input data: name or steps is missing.")
    
    records[record.name] = record.steps
    logger.info(f"Record added: {record.name}")
    return {"message": "Operation recorded successfully"}

# 2) GET /api/records——列出已录操作
@app.get("/api/records")
async def list_records():
    logger.info("Listing all records.")
    return records

# 3) POST /api/replay/{name}——模拟重放
@app.post("/api/replay/{name}")
async def replay_record(name: str, request: Request):
    # 输入验证
    if not name:
        logger.error("Invalid input data: name is missing.")
        raise HTTPException(status_code=400, detail="Invalid input data: name is missing.")
    
    if name not in records:
        logger.error(f"Record not found: {name}")
        raise HTTPException(status_code=404, detail="Record not found")
    
    steps = records[name]
    results = []
    
    # 从环境变量获取配置
    llm_url = os.getenv("LLM_URL", "http://127.0.0.1:4000/v1/chat/completions")
    llm_model = os.getenv("LLM_MODEL", "ollama/qwen3:8b")
    llm_token = os.getenv("LLM_TOKEN", "Bearer sk-local")
    
    async with aiohttp.ClientSession() as session:
        for step in steps:
            try:
                async with session.post(
                    llm_url,
                    headers={
                        "Authorization": f"{llm_token}"
                    },
                    json={
                        "model": llm_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": f"Can the following step be automated? {step.action} {step.selector} {step.value}"
                            }
                        ]
                    },
                    timeout=10
                ) as response:
                    if response.status != 200:
                        logger.error(f"LLM service error: {response.status}")
                        raise HTTPException(status_code=response.status, detail="LLM service error")
                    
                    data = await response.json()
                    content = data.get("choices", [{"message": {"content": "{}"}}])[0].get("message", {}).get("content", "{}")
                    
                    try:
                        text = (content or "").strip()
                        start, end = text.find("{"), text.rfind("}")
                        if start < 0 or end < start:
                            raise ValueError("no JSON")
                        analysis = json.loads(text[start:end + 1])
                        executable = analysis.get("executable", False)
                        risk = analysis.get("risk", "低")
                        suggestion = analysis.get("suggestion", "")
                    except Exception as e:
                        logger.error(f"Error parsing LLM response: {e}")
                        raise HTTPException(status_code=500, detail="Error parsing LLM response") from e
                    
                    results.append({
                        "action": step.action,
                        "selector": step.selector,
                        "value": step.value,
                        "executable": executable,
                        "risk": risk,
                        "suggestion": suggestion
                    })
            except Exception as e:
                logger.error(f"Exception during processing step: {e}")
                raise HTTPException(status_code=500, detail="Internal server error") from e
    
    try:
        overall_report = {
            "total_steps": len(steps),
            "automatable_count": sum(1 for result in results if result["executable"]),
            "average_risk": (sum(risk_mapping.get(result["risk"], 1) for result in results) / len(results)) if results else 0
        }
    except Exception as e:
        logger.error(f"Error generating overall report: {e}")
        raise HTTPException(status_code=500, detail="Error generating report") from e
    
    logger.info(f"Replay completed for record: {name}")
    return {
        "results": results,
        "overall_report": overall_report
    }

# 4) DELETE /api/records/{name}
@app.delete("/api/records/{name}")
async def delete_record(name: str):
    # 输入验证
    if not name:
        logger.error("Invalid input data: name is missing.")
        raise HTTPException(status_code=400, detail="Invalid input data: name is missing.")
    
    if name not in records:
        logger.error(f"Record not found: {name}")
        raise HTTPException(status_code=404, detail="Record not found")
    
    del records[name]
    logger.info(f"Record deleted: {name}")
    return {"message": "Record deleted successfully"}