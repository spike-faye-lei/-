import io
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
import requests
import json
import re

app = FastAPI()

class AnalyzeRequest(BaseModel):
    csv: str

class Issue(BaseModel):
    type: str
    column: str
    count: int
    example: str

class SuggestRequest(BaseModel):
    issues: List[Issue]

class Step(BaseModel):
    action: str
    column: str
    params: Optional[dict] = None

class DryRunRequest(BaseModel):
    csv: str
    steps: List[Step]

class ApplyRequest(BaseModel):
    csv: str
    steps: List[Step]

# 假设默认建议的清洗步骤
default_suggestions = [
    {
        "action": "dropna",
        "column": "",
        "params": {"axis": 0, "inplace": True}
    },
    {
        "action": "drop_duplicates",
        "column": "",
        "params": {"inplace": True}
    }
]

# POST /api/analyze
@app.post("/api/analyze", response_model=List[Issue])
async def analyze(request: AnalyzeRequest):
    try:
        # 读取 CSV 数据
        df = pd.read_csv(io.StringIO(request.csv), encoding='utf-8')
        
        issues = []
        
        # 检查缺失值列
        missing_values = df.isnull().sum()
        for column, count in missing_values.items():
            if count > 0:
                example = df[column].iloc[0] if not df[column].isna().all() else ""
                issues.append(Issue(type="missing_value", column=column, count=count, example=str(example)))
        
        # 检查重复行
        duplicate_count = df.duplicated().sum()
        if duplicate_count > 0:
            example = df.iloc[df.duplicated(keep=False)].drop_duplicates(subset=df.columns.difference(['id'])).iloc[0].to_dict() if not df.duplicated(keep=False).any() else ""
            issues.append(Issue(type="duplicate", column="", count=duplicate_count, example=str(example)))
        
        # 检查异常格式（如数字列含非数字）
        for column in df.select_dtypes(include='object').columns:
            try:
                pd.to_numeric(df[column])
            except ValueError:
                issues.append(Issue(type="invalid_format", column=column, count=df[column].nunique(), example=df[column].iloc[0]))
        
        # 检查明显错误值（负数年龄之类）
        for column in df.select_dtypes(include=[int, float]).columns:
            if column.lower() in ["age", "ages"] and (df[column] < 0).any():
                issues.append(Issue(type="invalid_value", column=column, count=(df[column] < 0).sum(), example=df[column][df[column] < 0].iloc[0]))
        
        return issues
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# POST /api/suggest
@app.post("/api/suggest", response_model=List[Step])
async def suggest(request: SuggestRequest):
    try:
        # 调用本地 LLM 生成清洗步骤建议
        response = requests.post(
            "http://127.0.0.1:4000/v1/chat/completions",
            headers={"Authorization": "Bearer sk-local"},
            json={
                "model": "ollama/qwen3:8b",
                "messages": [
                    {"role": "system", "content": "You are a data cleaning assistant."},
                    {"role": "user", "content": f"Based on the following issues, provide a list of cleaning steps:\n{request.issues}"}
                ]
            }
        )
        
        response.raise_for_status()
        
        content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "[]")
        try:
            text = (content or "").strip()
            start, end = text.find("{"), text.rfind("}")
            if start < 0 or end < start:
                start, end = text.find("["), text.rfind("]")
            suggestions = json.loads(text[start:end + 1]) if start >= 0 and end >= start else []
            return [Step(**step) for step in suggestions]
        except json.JSONDecodeError:
            return default_suggestions
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# POST /api/dry-run
@app.post("/api/dry-run")
async def dry_run(request: DryRunRequest):
    try:
        df = pd.read_csv(io.StringIO(request.csv))
        for step in request.steps:
            if step.action == "dropna":
                df = df.dropna(**(step.params or {}))
            elif step.action == "drop_duplicates":
                df = df.drop_duplicates(**(step.params or {}))
        return {"result": df.to_string(max_rows=None, max_cols=None)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# POST /api/apply
@app.post("/api/apply")
async def apply(request: ApplyRequest):
    try:
        df = pd.read_csv(io.StringIO(request.csv))
        for step in request.steps:
            if step.action == "dropna":
                df = df.dropna(**(step.params or {}))
            elif step.action == "drop_duplicates":
                df = df.drop_duplicates(**(step.params or {}))
        return {"result": df.to_string(max_rows=None, max_cols=None)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def to_string_with_max(df):
    return df.to_string(max_rows=None, max_cols=None)