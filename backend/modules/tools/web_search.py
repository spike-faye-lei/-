"""多引擎联网搜索回退 - DuckDuckGo → Bing 自动切换"""
import asyncio
import re
from typing import List, Dict, Optional
from urllib.parse import quote

import httpx
from loguru import logger

# 搜索引擎配置 - 多引擎自动回退
SEARCH_ENGINES = [
    {
        "name": "DuckDuckGo",
        "url": "https://html.duckduckgo.com/html/?q={query}",
        "selector": ".result",
        "title_sel": ".result__title",
        "snippet_sel": ".result__snippet",
        "link_sel": ".result__url",
    },
    {
        "name": "Bing",
        "url": "https://www.bing.com/search?q={query}",
        "selector": "li.b_algo",
        "title_sel": "h2",
        "snippet_sel": ".b_caption p",
        "link_sel": "a",
    },
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

TIMEOUT = 10.0


async def web_search(
    query: str,
    max_results: int = 5,
    timeout: float = TIMEOUT,
) -> List[Dict[str, str]]:
    """联网搜索 - 多引擎自动回退

    Args:
        query: 搜索关键词
        max_results: 最大结果数
        timeout: 单引擎超时秒数

    Returns:
        [{"title": ..., "snippet": ..., "url": ...}, ...]
    """
    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        for engine in SEARCH_ENGINES:
            try:
                url = engine["url"].format(query=quote(query))
                resp = await client.get(url)
                resp.raise_for_status()

                results = _parse_results(resp.text, engine, max_results)
                if results:
                    logger.debug(
                        f"Web search '{query[:50]}' via {engine['name']}: "
                        f"{len(results)} results"
                    )
                    return results
                else:
                    logger.debug(f"No results from {engine['name']}, trying next...")

            except Exception as e:
                logger.warning(f"{engine['name']} search failed: {e}")
                continue

    logger.warning(f"All search engines failed for query: {query[:50]}")
    return []


def _parse_results(html: str, engine: dict, max_results: int) -> List[Dict[str, str]]:
    """解析搜索引擎 HTML 结果"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(engine["selector"])

    results = []
    for item in items[:max_results * 2]:  # 多取一些备用
        title_el = item.select_one(engine["title_sel"])
        snippet_el = item.select_one(engine["snippet_sel"])
        link_el = item.select_one(engine["link_sel"])

        title = title_el.get_text(strip=True) if title_el else ""
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        url = link_el.get("href", "") if link_el else ""

        # 过滤无效结果
        if not title or not url:
            continue
        if any(skip in url.lower() for skip in ("javascript:", "#", "void(0)")):
            continue

        # Bing 链接可能是相对路径
        if url.startswith("/"):
            url = "https://www.bing.com" + url

        # 清理标题和摘要
        title = re.sub(r'\s+', ' ', title).strip()
        snippet = re.sub(r'\s+', ' ', snippet).strip()

        if title and len(title) > 3:
            results.append({
                "title": title[:200],
                "snippet": snippet[:500],
                "url": url,
            })

    return results[:max_results]


def web_search_sync(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """同步版联网搜索 (用于非异步上下文)"""
    return asyncio.run(web_search(query, max_results))
