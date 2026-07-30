"""QuickActions 按钮生成器 - 根据对话内容自动生成交互按钮"""
from typing import List, Dict, Optional, Any


def build_quick_actions(
    assistant_text: str = "",
    user_query: str = "",
    wiki_hits: Optional[List[dict]] = None,
    web_results: Optional[List[dict]] = None,
) -> List[Dict[str, Any]]:
    """根据上下文自动生成 QuickAction 按钮

    调用时机: send_message_complete 之前，将结果放入 keyboard 字段

    Args:
        assistant_text: AI 回复文本
        user_query: 用户原始查询
        wiki_hits: 知识库搜索结果
        web_results: 联网搜索结果

    Returns:
        [{"id": str, "label": str, "type": str, "icon": str, "style": str}, ...]
    """
    wiki_hits = wiki_hits or []
    web_results = web_results or []
    actions: List[Dict[str, Any]] = []

    # 1. Wiki 搜索结果按钮
    for hit in wiki_hits[:3]:
        title = hit.get("title", hit.get("slug", ""))
        slug = hit.get("slug", "")
        if title and slug:
            actions.append({
                "id": f"view:{slug}",
                "label": f" {title[:20]}",
                "type": f"view:{slug}",
                "icon": "",
                "style": "secondary",
            })

    # 2. 联网搜索结果按钮
    if web_results:
        web_count = len(web_results)
        search_url = _build_search_url(user_query)
        actions.append({
            "id": "web_results",
            "label": f" {web_count} 条搜索结果",
            "type": f"open_url:{search_url}",
            "icon": "",
            "style": "secondary",
        })

    # 3. 存入知识库按钮
    if wiki_hits or _is_worth_saving(assistant_text):
        content_preview = assistant_text[:200].replace("\n", " ")
        actions.append({
            "id": "save_kb",
            "label": " 存入知识库",
            "type": f"save_kb:{content_preview}",
            "icon": "",
            "style": "primary",
        })

    # 4. 问候/引导类按钮 (对话开始时)
    if _is_greeting(assistant_text) or not actions:
        actions.extend([
            {
                "id": "search_kb",
                "label": " 搜索知识库",
                "type": "search:",
                "icon": "",
                "style": "primary",
            },
            {
                "id": "upload_file",
                "label": " 上传文件",
                "type": "upload_file",
                "icon": "",
                "style": "secondary",
            },
            {
                "id": "open_wiki",
                "label": " 打开 Wiki",
                "type": "open:wiki",
                "icon": "",
                "style": "secondary",
            },
        ])

    # 5. 默认兜底按钮
    if not actions:
        actions = [
            {
                "id": "search_kb",
                "label": " 搜索知识库",
                "type": "search:",
                "icon": "",
                "style": "primary",
            },
            {
                "id": "web_search",
                "label": " 联网搜索",
                "type": "web_search:",
                "icon": "",
                "style": "secondary",
            },
            {
                "id": "open_wiki",
                "label": " 打开 Wiki",
                "type": "open:wiki",
                "icon": "",
                "style": "secondary",
            },
        ]

    return actions[:6]  # 最多6个按钮


def _is_greeting(text: str) -> bool:
    """判断是否为问候/介绍性回复"""
    greeting_patterns = [
        "你好", "您好", "欢迎", "我能帮你", "如何帮助你",
        "hello", "hi ", "hey", "greetings",
        "我是", "我叫", "我可以",
    ]
    text_lower = text.lower()[:200]
    return any(p.lower() in text_lower for p in greeting_patterns)


def _is_worth_saving(text: str) -> bool:
    """判断回复是否值得保存到知识库"""
    return len(text) > 100 and any(kw in text for kw in [
        "##", "步骤", "方法", "总结", "定义", "概念",
        "学习", "教程", "指南", "参考",
    ])


def _build_search_url(query: str) -> str:
    """构建搜索结果 URL"""
    from urllib.parse import quote
    return f"https://html.duckduckgo.com/html/?q={quote(query)}"


# ============================================================
# 前端 QuickAction 数据流说明
# ============================================================
#
# 后端生成 buttons → send_message_complete(keyboard=buttons)
#   → 前端 MessageItem.vue 渲染 QuickActions.vue
#     → 点击触发 emit('action', data)
#       → ChatWindow.handleQuickAction(data):
#
#   'open:wiki'       → router.push('/wiki')
#   'view:{slug}'     → wikiApi.getEntry(slug) → WikiViewer 弹窗
#   'open_url:{url}'  → window.open(url)
#   'save_kb:{text}'  → wikiApi.compile(text) → 确认 → 存入
#   'upload_file'     → 文件对话框 → wikiApi.upload(file)
#   'search:{query}'  → WebSocket.send({type:'message', content:query})
#   'web_search:{q}'  → WebSocket.send({type:'message', content:'搜索 '+q})
# ============================================================
