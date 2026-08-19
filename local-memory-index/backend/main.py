import os
import sqlite3
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import re
from typing import List

app = FastAPI()

# 数据库初始化
DATABASE_URL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.db")

def init_db():
    try:
        with sqlite3.connect(DATABASE_URL) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS docs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT,
                    name TEXT,
                    ext TEXT,
                    preview TEXT,
                    mtime TEXT,
                    keywords TEXT,
                    embedding TEXT
                )
            ''')
            conn.commit()
            try:
                cursor.execute("ALTER TABLE docs ADD COLUMN embedding TEXT")
            except sqlite3.OperationalError:
                pass
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize database: {e}")

init_db()

# 模型参数
MODEL_URL = "http://127.0.0.1:11434/api/embed"
MODEL_NAME = "bge-m3"

class IndexRequest(BaseModel):
    paths: List[str]
    extensions: List[str]

@app.post("/api/index")
async def index(paths: IndexRequest):
    try:
        with sqlite3.connect(DATABASE_URL) as conn:
            cursor = conn.cursor()
            count = 0
            
            for path in paths.paths:
                if os.path.isdir(path):
                    for root, _, files in os.walk(os.path.abspath(path)):
                        for file in files:
                            ext = os.path.splitext(file)[1].strip('.')
                            if ext in paths.extensions and ".." not in os.path.relpath(root, start=path):
                                full_path = os.path.join(root, file)
                                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                                    content = f.read(500)
                                
                                name, preview, mtime = file, content, str(os.path.getmtime(full_path))
                                keywords = ', '.join(re.findall(r'\b\w+\b', content.lower()))
                                
                                # 获取嵌入向量
                                async with httpx.AsyncClient() as client:
                                    response = await client.post(
                                        MODEL_URL,
                                        json={"model": MODEL_NAME, "input": [content]},
                                        timeout=10.0
                                    )
                                    
                                    if response.status_code != 200:
                                        raise HTTPException(status_code=response.status_code, detail="Failed to get embedding")
                                    
                                    embedding = response.json().get("embeddings", [[]])[0]
                                
                                cursor.execute('''
                                    INSERT INTO docs (path, name, ext, preview, mtime, keywords, embedding) 
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                ''', (full_path, name, ext, preview, mtime, keywords, str(embedding)))
                                count += 1
        return {"status": "success", "indexed": count}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.get("/api/search")
async def search(q: str):
    try:
        with sqlite3.connect(DATABASE_URL) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT path, name, preview 
                FROM docs 
                WHERE name LIKE ? OR preview LIKE ? OR keywords LIKE ?
            ''', ('%' + q.lower() + '%', '%' + q.lower() + '%', '%' + q.lower() + '%'))
            
            results = cursor.fetchall()
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    
    return [{"path": r[0], "name": r[1], "preview": r[2]} for r in results]

@app.get("/api/search/semantic")
async def semantic_search(q: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                MODEL_URL,
                json={"model": MODEL_NAME, "input": [q]},
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to get embedding")
            
            query_embedding = response.json().get("embeddings", [[]])[0]
        
        with sqlite3.connect(DATABASE_URL) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT path, name, preview, embedding FROM docs')
            docs = cursor.fetchall()
            results = []
            
            for doc in docs:
                # 计算余弦相似度
                similarity = calculate_cosine_similarity(query_embedding, json.loads(doc[3]) if doc[3] else [0.0])
                results.append((doc, similarity))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return [{"path": r[0][0], "name": r[0][1], "preview": r[0][2]} for r in results[:5]]
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.get("/api/stats")
async def stats():
    try:
        with sqlite3.connect(DATABASE_URL) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM docs')
            total_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT ext, COUNT(*) FROM docs GROUP BY ext')
            type_distribution = cursor.fetchall()
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    
    return {"total": total_count, "type_distribution": {ext: count for ext, count in type_distribution}}

def calculate_cosine_similarity(vec1, vec2):
    # 实现余弦相似度计算
    if not vec1 or not vec2:
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    na = sum(a * a for a in vec1) ** 0.5
    nb = sum(b * b for b in vec2) ** 0.5
    return dot / (na * nb) if na and nb else 0.0
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def get_embedding_from_db(path):
    # 从数据库中获取文件的嵌入向量
    try:
        with sqlite3.connect(DATABASE_URL) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT embedding FROM docs WHERE path = ?', (path,))
            result = cursor.fetchone()
        if result:
            return json.loads(result[0]) if result[0] else []
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")