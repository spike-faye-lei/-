"""全局配置：DeepSeek API"""
import json
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

# ---------- API 用量统计（成本控制：看板展示累计调用与估算成本） ----------
# deepseek-chat 官方刊例价（元/百万 token）：输入 2 元，输出 8 元
PRICE_IN_PER_M = 2.0
PRICE_OUT_PER_M = 8.0
_usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0}


def _record_usage(messages, reply_text):
    """估算并累计 token 用量（本地按字符数粗估，精确值以 API usage 字段为准）"""
    in_chars = sum(len(str(m.get("content", ""))) for m in messages)
    out_chars = len(reply_text or "")
    _usage["calls"] += 1
    _usage["input_tokens"] += int(in_chars * 1.2)  # 中文≈1.2 token/字符（粗估）
    _usage["output_tokens"] += int(out_chars * 1.2)


def get_api_usage():
    """用量统计：调用次数 / 估算 token / 估算成本（元）"""
    cost = _usage["input_tokens"] / 1e6 * PRICE_IN_PER_M + _usage["output_tokens"] / 1e6 * PRICE_OUT_PER_M
    return {
        "calls": _usage["calls"],
        "input_tokens": _usage["input_tokens"],
        "output_tokens": _usage["output_tokens"],
        "estimated_cost_yuan": round(cost, 4),
    }


def chat(messages, temperature=0.7, max_tokens=2000, retries=3):
    """调用 DeepSeek 对话接口，返回回复文本。网络抖动/限流自动重试（指数退避，最多 retries 次）。"""
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
                reply = resp.json()["choices"][0]["message"]["content"]
                _record_usage(messages, reply)
                return reply
            last_err = RuntimeError(f"API 调用失败 ({resp.status_code}): {resp.text[:300]}")
            # 限流/服务端错误可重试；4xx 业务错误（如鉴权失败）直接抛出
            if resp.status_code not in (429, 500, 502, 503, 504):
                raise last_err
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = RuntimeError(f"网络错误（{type(e).__name__}），请检查网络后重试")
        if attempt < retries - 1:
            time.sleep(2 ** attempt)  # 1s, 2s, 4s 指数退避
    raise last_err


def chat_stream(messages, temperature=0.7, max_tokens=2000):
    """流式调用 DeepSeek 对话接口（SSE）。

    返回 generator，逐块 yield 文本增量（打字机效果）；出错时 yield 错误提示后结束。
    """
    import requests

    if not API_KEY:
        yield "（错误：缺少 DEEPSEEK_API_KEY，请在 .env 文件中配置）"
        return
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
                "stream": True,
            },
            stream=True,
            timeout=(30, 180),
        )
        if resp.status_code != 200:
            yield f"（错误：API 调用失败 {resp.status_code}：{resp.text[:200]}）"
            return
        parts = []
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                delta = json.loads(data)["choices"][0]["delta"].get("content", "")
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
            if delta:
                parts.append(delta)
                yield delta
        if parts:
            _record_usage(messages, "".join(parts))
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        yield f"（网络错误：{type(e).__name__}，流式响应中断）"
