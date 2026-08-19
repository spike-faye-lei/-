from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import json
from collections import defaultdict
import requests

app = FastAPI()

# 内置评测集
builtin_test_cases = [
    {"query": "提取 PDF 表格", "expected_skills": ["paper-*"]},
    {"query": "翻译英文文档", "expected_skills": ["language-translation"]},
    {"query": "数据分析报告", "expected_skills": ["data-analysis"]},
    # 添加更多评测用例
]

# 用于存储最近一次评测报告
last_report = None

class Skill(BaseModel):
    name: str
    description: str

class TestCase(BaseModel):
    query: str
    expected_skills: list[str]

class EvaluateRequest(BaseModel):
    skills: list[Skill]
    test_cases: list[TestCase]

class RunRequest(BaseModel):
    path: str = os.getenv("SKILL_PATH", "D:/spike-faye-lei-dsh-skills/skills")

@app.post("/api/evaluate", tags=["Evaluation"])
async def evaluate(request: EvaluateRequest):
    results = []
    for test_case in request.test_cases:
        query = test_case.query
        expected_skills = set(test_case.expected_skills)
        
        # 计算每个技能的匹配度
        matches = []
        for skill in request.skills:
            if not query:
                match_score = 0.0
            else:
                try:
                    response = requests.post(
                        os.getenv("EMBED_API_URL", "http://127.0.0.1:11434/api/embed"), 
                        json={
                            "input": [query, f"{skill.name} {skill.description}"]
                        },
                        timeout=5  # 设置请求超时时间
                    )
                    response.raise_for_status()  # 检查HTTP错误
                    embeddings = response.json().get("embeddings", [])
                    if len(embeddings) < 2:
                        match_score = 0.0
                    else:
                        query_embedding = embeddings[0]
                        skill_embedding = embeddings[1]
                        
                        # 计算余弦相似度
                        dot_product = sum(q * s for q, s in zip(query_embedding, skill_embedding))
                        norm_query = (sum(q**2 for q in query_embedding)) ** 0.5
                        norm_skill = (sum(s**2 for s in skill_embedding)) ** 0.5
                        if norm_query == 0 or norm_skill == 0:
                            match_score = 0.0
                        else:
                            match_score = dot_product / (norm_query * norm_skill)
                except Exception:
                    # 请求失败时设置匹配分为0
                    match_score = 0.0
            matches.append((skill, match_score))
        
        # 获取 top-3 预测
        top_3_skills = sorted(matches, key=lambda x: x[1], reverse=True)[:3]
        predicted_skills = [skill.name for skill, score in top_3_skills]
        
        # 计算 recall@3 和 precision
        if expected_skills:
            recall = len(set(predicted_skills) & expected_skills) / len(expected_skills)
        else:
            recall = 0.0
        precision = len(set(predicted_skills) & expected_skills) / len(predicted_skills) if predicted_skills else 0.0
        
        results.append({
            "query": query,
            "predicted": predicted_skills,
            "expected": list(expected_skills),
            "recall": recall,
            "precision": precision
        })
    
    # 计算平均 recall 和 precision
    avg_recall = sum(result["recall"] for result in results) / len(results) if results else 0.0
    avg_precision = sum(result["precision"] for result in results) / len(results) if results else 0.0
    
    return {
        "results": results,
        "avg_recall": avg_recall,
        "avg_precision": avg_precision
    }

@app.post("/api/run", tags=["Evaluation"])
async def run(request: RunRequest):
    global last_report
    
    # 检查路径有效性
    if not os.path.exists(request.path):
        raise HTTPException(status_code=404, detail="Path does not exist")
    
    # 检查空目录
    if not os.listdir(request.path):
        raise HTTPException(status_code=404, detail="Directory is empty")
    
    # 读取技能文件
    skills = []
    for root, _, files in os.walk(request.path):
        for file in files:
            if file.endswith("SKILL.md"):
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        content = f.read()
                    # 这里可以进一步解析文件内容，但根据需求仅读取文件名
                    skill_name = os.path.splitext(file)[0]
                    skill_description = content  # 取全文作为描述
                    skills.append(Skill(name=skill_name, description=skill_description))
                except Exception:
                    # 忽略读取错误的文件
                    continue
    
    # 构建评估请求
    evaluation_request = EvaluateRequest(skills=skills, test_cases=builtin_test_cases)
    result = await evaluate(evaluation_request)
    last_report = result
    
    return result

@app.get("/api/report", tags=["Evaluation"])
async def get_report():
    if last_report is None:
        raise HTTPException(status_code=404, detail="No evaluation report available")
    return last_report