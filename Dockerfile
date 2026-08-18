# AI 招聘官 —— 生产部署镜像（Python 3.12 slim）
FROM python:3.12-slim

WORKDIR /app

# 依赖层单独复制（利用镜像缓存：依赖不变时不重装）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY . .

# 简历文件与数据库数据目录
RUN mkdir -p /app/resumes /app/backups

# .env 由 docker-compose / 部署平台注入（API Key 不写入镜像）
ENV PYTHONUNBUFFERED=1

EXPOSE 7860 7861

CMD ["python", "app.py"]
