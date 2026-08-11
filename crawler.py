"""候选人/岗位主动检索爬虫（合规版）

法律边界（PIPL 合规）：
1. 只采集用户在公开平台【自愿公开发布】的信息（V2EX 酷工作帖子 = 发帖即公开授权）
2. 走平台公开 API，不绕过任何反爬机制（不碰 Cloudflare 挑战、不加密参数）
3. 礼貌抓取：限速 1 秒/请求，单次抓取量小，不采集联系方式等敏感字段
4. 生产环境扩展：接入平台官方授权接口（BOSS 开放平台 / 猎聘 API 等），适配器模式

用法：
    from crawler import fetch_jobs, match_profile, fetch_seekers
    jobs = fetch_jobs(pages=3)          # 抓取 V2EX 酷工作公开招聘帖（岗位 JD）
    pid = match_profile(jd_text)        # JD 关键词 → 自动匹配内置岗位 rubric
    seekers = fetch_seekers(limit=3)    # 抓取公开求职帖（量少），不足返回 []
"""
import html as html_mod
import re
import time

import requests

V2EX_API = "https://www.v2ex.com/api/topics/show.json"
V2EX_LATEST = "https://www.v2ex.com/api/topics/latest.json"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 recruit-agent-demo"
)
REQUEST_INTERVAL = 1.0  # 礼貌抓取：每秒最多 1 个请求
TIMEOUT = 12


def _clean_html(text: str) -> str:
    """去 HTML 标签，压缩空白"""
    text = re.sub(r"<[^>]+>", " ", text or "")
    return html_mod.unescape(re.sub(r"\s+", " ", text)).strip()


def _fetch_page(url: str, params: dict) -> list:
    resp = requests.get(
        url,
        params=params,
        headers={"User-Agent": UA, "Accept": "application/json"},
        timeout=TIMEOUT,
    )
    if resp.status_code != 200 or not resp.content:
        return []
    return resp.json()


def fetch_jobs(pages: int = 3) -> list:
    """抓取 V2EX 酷工作公开招聘帖（岗位 JD 采集）。

    返回 [{title, url, member, content, replies}]；任何失败返回 []（调用方回退内置岗位）。
    """
    posts = []
    for page in range(1, pages + 1):
        try:
            posts += _fetch_page(V2EX_API, {"node_name": "jobs", "page": page})
        except (requests.exceptions.RequestException, ValueError):
            break  # 网络不可用/解析失败：停止抓取，用已抓到的
        time.sleep(REQUEST_INTERVAL)
    jobs = []
    for p in posts:
        if p.get("deleted"):
            continue
        jobs.append(
            {
                "title": p.get("title", ""),
                "url": p.get("url", ""),
                "member": p.get("member", {}).get("username", ""),
                "content": _clean_html(p.get("content", "")),
                "replies": p.get("replies", 0),
            }
        )
    return jobs


# JD 关键词 → 内置岗位 rubric 的映射（自动匹配用）
JOB_KEYWORDS = {
    "ai-dev": [
        "ai", "agent", "大模型", "llm", "rag", "langchain", "prompt",
        "python", "算法", "机器学习", "深度学习", "向量", "gpt", "模型", "embedding",
    ],
    "backend": [
        "java", "golang", "后端", "微服务", "spring", "mysql", "redis",
        "kafka", "分布式", "高并发", "服务端", "架构",
    ],
    "frontend": [
        "前端", "vue", "react", "小程序", "css", "typescript", "h5", "web",
    ],
}


def match_profile(jd_text: str) -> str:
    """根据 JD 文本关键词自动匹配内置岗位 rubric，返回 profile_id。

    找不到任何关键词时回退 "ai-dev"。
    """
    text = (jd_text or "").lower()
    scores = {}
    for pid, kws in JOB_KEYWORDS.items():
        scores[pid] = sum(1 for k in kws if k in text)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "ai-dev"


SEEK_TITLE_PATTERN = re.compile(r"求职|求一份|找工作中|求内推|找工作")


def fetch_seekers(limit: int = 3) -> list:
    """抓取 V2EX 公开求职帖（候选人自愿公开发布），转成候选人结构。

    返回 [{label, source, profile, resume}]；找不到返回 []（调用方用内置简历库补齐）。
    求职帖是稀缺资源（酷工作板块以招聘帖为主），会翻多页尽力找，找不到是常态。
    """
    posts = []
    try:
        for page in range(1, 6):  # 酷工作翻 5 页
            posts += _fetch_page(V2EX_API, {"node_name": "jobs", "page": page})
            time.sleep(REQUEST_INTERVAL)
        posts += _fetch_page(V2EX_LATEST, {})  # 全站最新
        time.sleep(REQUEST_INTERVAL)
        posts += _fetch_page(V2EX_LATEST, {"p": 2})  # 全站最新第 2 页兜底
    except (requests.exceptions.RequestException, ValueError):
        pass
    seekers = []
    seen = set()
    for p in posts:
        title = p.get("title", "")
        if p.get("deleted") or not SEEK_TITLE_PATTERN.search(title):
            continue
        content = _clean_html(p.get("content", ""))
        if not content:
            continue
        url = p.get("url", "")
        if url in seen:
            continue
        seen.add(url)
        username = p.get("member", {}).get("username", "匿名")
        seekers.append(
            {
                "label": f"{title[:20]} · V2EX 公开求职帖",
                "source": "V2EX 酷工作 · 公开求职帖（自愿发布）",
                "profile": f"V2EX 用户 {username} · 公开自荐",
                "resume": (
                    f"姓名：V2EX 用户 {username}\n"
                    f"来源：{url}\n"
                    f"自荐内容：\n{content[:1500]}"
                ),
            }
        )
        if len(seekers) >= limit:
            break
    return seekers
