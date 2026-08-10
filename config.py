"""全局配置：DeepSeek API"""
import os

# 读取 .env 文件（简单实现，避免额外依赖）
def load_dotenv(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

load_dotenv()

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")


def chat(messages, temperature=0.7, max_tokens=2000, retries=3):
    """调用 DeepSeek 对话接口，返回回复文本。网络抖动/限流自动重试（指数退避）。"""
    import time

    import requests

    if not API_KEY:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY，请在 .env 文件中配置")
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.post(
                BASE_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=120,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            last_err = RuntimeError(f"API 调用失败 ({resp.status_code}): {resp.text[:300]}")
            # 限流/服务端错误可重试；4xx 业务错误（如鉴权失败）直接抛出
            if resp.status_code not in (429, 500, 502, 503, 504):
                raise last_err
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = RuntimeError(f"网络错误（{type(e).__name__}），请检查网络后重试")
        if attempt < retries - 1:
            time.sleep(2 ** attempt)  # 1s, 2s, 4s 指数退避
    raise last_err
