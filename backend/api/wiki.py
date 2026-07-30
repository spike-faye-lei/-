"""Wiki API 端点 - 基于模块化 Wiki 服务"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from loguru import logger

from backend.modules.config.loader import config_loader
from backend.modules.wiki.service import WikiService
from backend.utils.paths import WORKSPACE_DIR

router = APIRouter(
    prefix="/api/wiki",
    tags=["wiki"],
    dependencies=[],
)

# ============================================================================
# 全局服务实例
# ============================================================================

_wiki_service: Optional[WikiService] = None


def get_wiki_service() -> WikiService:
    """获取 Wiki 服务实例（单例）"""
    global _wiki_service
    if _wiki_service is None:
        config = config_loader.config
        wiki_dir = Path(config.workspace.path) / "wiki" if config.workspace.path else WORKSPACE_DIR / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        _wiki_service = WikiService(wiki_dir)
        logger.info(f"Wiki service initialized: {wiki_dir}")
    return _wiki_service


def _check_kb_locked():
    """检查知识库是否被 FaceGuard 锁定 (HTTP 423)"""
    service = get_wiki_service()
    if hasattr(service, '_kb_guard') and service._kb_guard is not None:
        if service._kb_guard.is_locked:
            raise HTTPException(
                status_code=423,
                detail="知识库已被人脸守护锁定，请通过人脸认证解锁",
            )


# ============================================================================
# Request/Response Models
# ============================================================================


class WikiEntryResponse(BaseModel):
    """Wiki 条目响应"""
    slug: str = Field(..., description="条目唯一标识")
    title: str = Field(..., description="条目标题")
    content: str = Field(..., description="条目内容")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    summary: str = Field("", description="摘要")


class WikiSearchResult(BaseModel):
    """Wiki 搜索结果"""
    slug: str = Field(..., description="条目唯一标识")
    title: str = Field(..., description="条目标题")
    summary: str = Field("", description="摘要")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class WikiSearchResponse(BaseModel):
    """Wiki 搜索响应"""
    query: str = Field(..., description="搜索查询")
    results: List[WikiSearchResult] = Field(default_factory=list, description="搜索结果")
    total: int = Field(..., description="结果总数")


class WikiListResponse(BaseModel):
    """Wiki 列表响应"""
    entries: List[Dict[str, Any]] = Field(default_factory=list, description="条目列表")
    total: int = Field(..., description="条目总数")


class WikiAskRequest(BaseModel):
    """Wiki 问答请求"""
    question: str = Field(..., description="问题", min_length=1)


class WikiAskResponse(BaseModel):
    """Wiki 问答响应"""
    answer: str = Field(..., description="回答")
    sources: List[Dict[str, str]] = Field(default_factory=list, description="参考来源")
    from_web: bool = Field(default=False, description="是否来自联网搜索")
    entry_url: str = Field(default="", description="已保存的 Wiki 条目链接")


class WikiStatsResponse(BaseModel):
    """Wiki 统计响应"""
    articles: int = Field(..., description="文章总数")
    indexed_count: int = Field(..., description="已索引数")
    unique_terms: int = Field(..., description="唯一术语数")


class WikiEntryCreate(BaseModel):
    """Wiki 条目创建请求"""
    title: str = Field(..., description="条目标题", min_length=1, max_length=200)
    content: str = Field(..., description="条目内容", min_length=1)
    tags: List[str] = Field(default_factory=list, description="标签列表")
    summary: Optional[str] = Field(None, description="摘要")


class WikiEntryUpdate(BaseModel):
    """Wiki 条目更新请求"""
    title: Optional[str] = Field(None, description="条目标题", max_length=200)
    content: Optional[str] = Field(None, description="条目内容")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class WikiCompileRequest(BaseModel):
    """Wiki 编译请求"""
    content: str = Field(..., description="原始内容", min_length=1)
    source_type: str = Field(default="article", description="来源类型")
    title_hint: Optional[str] = Field(None, description="标题提示")


class WikiCompileResponse(BaseModel):
    """Wiki 编译响应"""
    success: bool = Field(..., description="是否成功")
    title: Optional[str] = Field(None, description="编译后的标题")
    content: Optional[str] = Field(None, description="编译后的内容")
    tags: List[str] = Field(default_factory=list, description="建议标签")


# ============================================================================
# Helper Functions
# ============================================================================


def _generate_slug(title: str) -> str:
    """生成 URL 友好的 slug"""
    import re
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    return slug[:100] or "untitled"


def _get_concepts_dir() -> Path:
    """获取 concepts 目录"""
    config = config_loader.config
    wiki_dir = Path(config.workspace.path) / "wiki" if config.workspace.path else WORKSPACE_DIR / "wiki"
    concepts = wiki_dir / "concepts"
    concepts.mkdir(parents=True, exist_ok=True)
    return concepts


# ============================================================================
# Wiki Endpoints
# ============================================================================


@router.get("", response_model=WikiListResponse)
async def list_wiki_entries(
    tag: Optional[str] = None,
    limit: int = 100,
) -> WikiListResponse:
    """列出所有 Wiki 条目"""
    try:
        service = get_wiki_service()
        articles = service.list_documents(tag)[:limit]
        return WikiListResponse(entries=articles, total=len(articles))
    except Exception as e:
        logger.exception(f"Failed to list wiki entries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list wiki entries: {str(e)}"
        )


@router.get("/search", response_model=WikiSearchResponse)
async def search_wiki_entries(
    query: str,
    limit: int = 20,
) -> WikiSearchResponse:
    """搜索 Wiki 条目（BM25 + 上下文片段）"""
    try:
        service = get_wiki_service()
        results = service.search_with_snippets(query, top_k=limit)

        search_results = []
        for result in results:
            search_results.append(WikiSearchResult(
                slug=result["slug"],
                title=result["title"],
                summary=result.get("snippet", ""),
                tags=result.get("tags", []),
            ))

        return WikiSearchResponse(
            query=query,
            results=search_results,
            total=len(search_results),
        )
    except Exception as e:
        logger.exception(f"Failed to search wiki entries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search wiki entries: {str(e)}"
        )


@router.get("/stats", response_model=WikiStatsResponse)
async def get_wiki_stats() -> WikiStatsResponse:
    """获取 Wiki 统计信息"""
    try:
        service = get_wiki_service()
        stats = service.get_stats()
        return WikiStatsResponse(
            articles=stats["article_count"],
            indexed_count=stats["indexed_count"],
            unique_terms=stats["unique_terms"],
        )
    except Exception as e:
        logger.exception(f"Failed to get wiki stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get wiki stats: {str(e)}"
        )


@router.get("/export", status_code=status.HTTP_200_OK)
async def export_wiki() -> Dict[str, Any]:
    """导出所有 Wiki 条目为 JSON"""
    try:
        service = get_wiki_service()
        articles = service.list_documents()

        # 获取完整内容
        full_data = []
        for article in articles:
            doc = service.get_document(article["slug"])
            if doc:
                full_data.append(doc)

        return {
            "success": True,
            "count": len(full_data),
            "entries": full_data,
        }
    except Exception as e:
        logger.exception(f"Failed to export wiki: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export wiki: {str(e)}"
        )


@router.get("/{slug}", response_model=WikiEntryResponse)
async def get_wiki_entry(slug: str) -> WikiEntryResponse:
    """获取 Wiki 条目详情"""
    try:
        service = get_wiki_service()
        article = service.get_document(slug)

        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wiki entry '{slug}' not found"
            )

        return WikiEntryResponse(
            slug=article["slug"],
            title=article["title"],
            content=article["content"],
            tags=article.get("tags", []),
            summary=article.get("summary", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get wiki entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get wiki entry: {str(e)}"
        )


@router.get("/{slug}/backlinks")
async def get_wiki_backlinks(slug: str) -> Dict[str, Any]:
    """获取 Wiki 条目的反向链接"""
    try:
        service = get_wiki_service()

        # 检查条目是否存在
        article = service.get_document(slug)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wiki entry '{slug}' not found"
            )

        backlinks = service.get_backlinks(slug)
        return {
            "slug": slug,
            "title": article["title"],
            "backlinks": backlinks,
            "count": len(backlinks),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get backlinks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get backlinks: {str(e)}"
        )


@router.post("/ask", response_model=WikiAskResponse)
async def ask_wiki(request: WikiAskRequest):
    """Wiki 问答 — 本地搜索 + 联网回退

    流程:
    1. BM25+FAISS 本地搜索
    2. 结果不足 → 自动联网搜索 (DuckDuckGo → Bing → Google)
    3. LLM 整合回答 + 附参考来源链接
    """
    try:
        service = get_wiki_service()
        results = service.search(request.question, top_k=3)
        sources = []
        from_web = False

        # 本地知识库搜索
        if results and results[0][1] > 0.5:
            context_parts = []
            for doc_id, score in results:
                doc = service.get_document(doc_id)
                if doc:
                    sources.append({"title": doc["title"], "url": f"/wiki/read/{doc_id}"})
                    context_parts.append(f"### {doc['title']}\n{doc['content']}")
            context = "\n\n".join(context_parts)
        else:
            # 本地无结果或得分过低 → 联网搜索
            context = ""
            from_web = True
            try:
                from backend.modules.tools.web_search import web_search
                web_results = await web_search(request.question, max_results=5)
                if web_results:
                    parts = []
                    for r in web_results:
                        sources.append({"title": r["title"], "url": r["url"]})
                        parts.append(f"### {r['title']}\n{r['snippet']}\n来源: {r['url']}")
                    context = "\n\n".join(parts)
            except Exception as e:
                logger.warning(f"Web search failed: {e}")

        if not context:
            return WikiAskResponse(
                answer="未能找到相关信息，请尝试其他关键词。",
                sources=[], from_web=False,
            )

        # LLM 整合回答
        entry_url = ""
        try:
            from backend.app import get_shared_provider
            provider = get_shared_provider()
            if provider:
                source_type = "联网搜索" if from_web else "本地知识库"
                source_links = "\n".join(f"- [{s['title']}]({s['url']})" for s in sources[:5])
                prompt = f"""请根据以下{source_type}结果，用中文写一篇简明的知识文章。

问题：{request.question}

参考内容：
{context[:4000]}

参考链接：
{source_links}

要求：
- 文章简洁完整，300-800字
- 使用 Markdown 格式（标题、列表、加粗）
- 末尾列出参考来源
- 不要编造信息"""
                answer = await provider.chat_completion(prompt, max_tokens=1500, temperature=0.3)

                # 自动保存为 Wiki 条目
                slug = _generate_slug(request.question[:50])
                tags = []
                if from_web:
                    tags.append("联网搜索")
                md_content = f"---\ntitle: \"{request.question[:80]}\"\nslug: {slug}\ntags: {tags}\n---\n\n{answer}\n\n## 参考来源\n\n{source_links}"
                concepts_dir = _get_concepts_dir()
                md_file = concepts_dir / f"{slug}.md"
                md_file.write_text(md_content, encoding="utf-8")
                service.force_sync()
                entry_url = f"/wiki/read/{slug}"
                logger.info(f"Wiki entry saved: {slug}")

                # 返回简洁摘要 + 链接，不浪费对话长度
                summary = await provider.chat_completion(
                    f"用1-2句话总结以下文章的核心内容:\n{answer[:1000]}",
                    max_tokens=200, temperature=0.3,
                )
                return WikiAskResponse(
                    answer=f"{summary}\n\n📄 完整文章: {entry_url}",
                    sources=sources, from_web=from_web, entry_url=entry_url,
                )
        except Exception:
            pass

        # LLM不可用时的回退
        if from_web:
            lines = ["以下是联网搜索结果：\n"]
            for s in sources[:5]:
                lines.append(f"- [{s['title']}]({s['url']})")
            return WikiAskResponse(answer="\n".join(lines), sources=sources, from_web=True)
        else:
            lines = ["本地知识库找到以下内容：\n"]
            for doc_id, score in results[:3]:
                doc = service.get_document(doc_id)
                if doc:
                    lines.append(f"**{doc['title']}**\n{doc['content'][:300]}")
            return WikiAskResponse(answer="\n".join(lines), sources=sources, from_web=False)

    except Exception as e:
        logger.exception(f"Failed to ask wiki: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ask wiki: {str(e)}"
        )


@router.post("/sync", status_code=status.HTTP_200_OK)
async def sync_wiki_index() -> Dict[str, Any]:
    """强制同步 Wiki 索引（检测文件变更）"""
    _check_kb_locked()
    try:
        service = get_wiki_service()
        stats = service.force_sync()
        return {
            "success": True,
            "message": f"Index synced: +{stats['added']} ~{stats['updated']} -{stats['deleted']}",
            "stats": stats,
        }
    except Exception as e:
        logger.exception(f"Failed to sync wiki index: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync wiki index: {str(e)}"
        )


@router.post("/batch/delete", status_code=status.HTTP_200_OK)
async def batch_delete_entries(slugs: List[str]) -> Dict[str, Any]:
    """批量删除 Wiki 条目"""
    try:
        service = get_wiki_service()
        concepts_dir = _get_concepts_dir()

        deleted = []
        failed = []

        for slug in slugs:
            md_file = concepts_dir / f"{slug}.md"
            if md_file.exists():
                try:
                    md_file.unlink()
                    service.remove_document(slug)
                    deleted.append(slug)
                except Exception as e:
                    logger.warning(f"Failed to delete {slug}: {e}")
                    failed.append({"slug": slug, "error": str(e)})
            else:
                failed.append({"slug": slug, "error": "Not found"})

        return {
            "success": True,
            "deleted": deleted,
            "failed": failed,
            "total": len(slugs),
        }
    except Exception as e:
        logger.exception(f"Failed to batch delete: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch delete: {str(e)}"
        )


@router.post("/batch/tag", status_code=status.HTTP_200_OK)
async def batch_update_tags(request: Dict[str, Any]) -> Dict[str, Any]:
    """批量更新标签"""
    try:
        import frontmatter
        from datetime import datetime

        slugs = request.get("slugs", [])
        add_tags = request.get("add_tags", [])
        remove_tags = request.get("remove_tags", [])

        service = get_wiki_service()
        concepts_dir = _get_concepts_dir()

        updated = []
        failed = []

        for slug in slugs:
            md_file = concepts_dir / f"{slug}.md"
            if not md_file.exists():
                failed.append({"slug": slug, "error": "Not found"})
                continue

            try:
                post = frontmatter.load(str(md_file))
                current_tags = set(post.metadata.get("tags", []))

                # 添加标签
                for tag in add_tags:
                    current_tags.add(tag)

                # 移除标签
                for tag in remove_tags:
                    current_tags.discard(tag)

                post.metadata["tags"] = list(current_tags)
                post.metadata["updated"] = datetime.now().isoformat()

                md_content = frontmatter.dumps(post, encoding="utf-8")
                md_file.write_text(md_content, encoding="utf-8")

                # 更新索引
                service.add_document(
                    slug,
                    post.metadata.get("title", slug),
                    post.content,
                    list(current_tags)
                )

                updated.append(slug)
            except Exception as e:
                logger.warning(f"Failed to update tags for {slug}: {e}")
                failed.append({"slug": slug, "error": str(e)})

        return {
            "success": True,
            "updated": updated,
            "failed": failed,
            "total": len(slugs),
        }
    except Exception as e:
        logger.exception(f"Failed to batch update tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch update tags: {str(e)}"
        )


@router.post("/import", status_code=status.HTTP_200_OK)
async def import_wiki(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """批量导入 Wiki 条目"""
    try:
        import frontmatter
        from datetime import datetime

        service = get_wiki_service()
        concepts_dir = _get_concepts_dir()

        imported = []
        skipped = []
        failed = []

        for entry in entries:
            slug = entry.get("slug")
            title = entry.get("title")
            content = entry.get("content")
            tags = entry.get("tags", [])

            if not slug or not title or not content:
                failed.append({"entry": entry, "error": "Missing required fields"})
                continue

            md_file = concepts_dir / f"{slug}.md"
            if md_file.exists():
                skipped.append(slug)
                continue

            try:
                now = datetime.now().isoformat()
                post = frontmatter.Post(content)
                post.metadata["title"] = title
                post.metadata["tags"] = tags
                post.metadata["summary"] = entry.get("summary", content[:200].strip())
                post.metadata["created"] = entry.get("created", now)
                post.metadata["updated"] = entry.get("updated", now)

                md_content = frontmatter.dumps(post, encoding="utf-8")
                md_file.write_text(md_content, encoding="utf-8")

                # 更新索引
                service.add_document(slug, title, content, tags)
                imported.append(slug)
            except Exception as e:
                logger.warning(f"Failed to import {slug}: {e}")
                failed.append({"slug": slug, "error": str(e)})

        return {
            "success": True,
            "imported": imported,
            "skipped": skipped,
            "failed": failed,
            "total": len(entries),
        }
    except Exception as e:
        logger.exception(f"Failed to import wiki: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import wiki: {str(e)}"
        )


@router.post("", response_model=WikiEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_wiki_entry(request: WikiEntryCreate) -> WikiEntryResponse:
    """创建 Wiki 条目"""
    _check_kb_locked()
    import frontmatter
    from datetime import datetime
    
    try:
        concepts_dir = _get_concepts_dir()
        slug = _generate_slug(request.title)
        md_file = concepts_dir / f"{slug}.md"
        
        if md_file.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Wiki entry '{slug}' already exists"
            )
        
        now = datetime.now().isoformat()
        
        post = frontmatter.Post(request.content)
        post.metadata["title"] = request.title
        post.metadata["tags"] = request.tags
        post.metadata["summary"] = request.summary or request.content[:200].strip()
        post.metadata["created"] = now
        post.metadata["updated"] = now
        
        md_content = frontmatter.dumps(post, encoding="utf-8")
        md_file.write_text(md_content, encoding="utf-8")
        
        # 更新索引
        service = get_wiki_service()
        service.add_document(slug, request.title, request.content, request.tags)
        
        logger.info(f"Created wiki entry: {slug}")
        
        return WikiEntryResponse(
            slug=slug,
            title=request.title,
            content=request.content,
            tags=request.tags,
            summary=request.summary or request.content[:200].strip(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to create wiki entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create wiki entry: {str(e)}"
        )


@router.put("/{slug}", response_model=WikiEntryResponse)
async def update_wiki_entry(
    slug: str,
    request: WikiEntryUpdate,
) -> WikiEntryResponse:
    """更新 Wiki 条目"""
    _check_kb_locked()
    """更新 Wiki 条目"""
    import frontmatter
    from datetime import datetime
    
    try:
        concepts_dir = _get_concepts_dir()
        md_file = concepts_dir / f"{slug}.md"
        
        if not md_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wiki entry '{slug}' not found"
            )
        
        post = frontmatter.load(str(md_file))
        
        if request.title:
            post.metadata["title"] = request.title
        if request.tags is not None:
            post.metadata["tags"] = request.tags
        if request.content is not None:
            post.content = request.content
        
        post.metadata["updated"] = datetime.now().isoformat()
        
        md_content = frontmatter.dumps(post, encoding="utf-8")
        md_file.write_text(md_content, encoding="utf-8")
        
        # 更新索引
        service = get_wiki_service()
        service.add_document(
            slug,
            post.metadata.get("title", slug),
            post.content,
            post.metadata.get("tags", [])
        )
        
        logger.info(f"Updated wiki entry: {slug}")
        
        return WikiEntryResponse(
            slug=slug,
            title=post.metadata.get("title", slug),
            content=post.content,
            tags=post.metadata.get("tags", []),
            summary=post.metadata.get("summary", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update wiki entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update wiki entry: {str(e)}"
        )


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wiki_entry(slug: str) -> None:
    """删除 Wiki 条目"""
    _check_kb_locked()
    try:
        concepts_dir = _get_concepts_dir()
        md_file = concepts_dir / f"{slug}.md"
        
        if not md_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wiki entry '{slug}' not found"
            )
        
        md_file.unlink()
        
        # 更新索引
        service = get_wiki_service()
        service.remove_document(slug)
        
        logger.info(f"Deleted wiki entry: {slug}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete wiki entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete wiki entry: {str(e)}"
        )


@router.post("/compile", response_model=WikiCompileResponse)
async def compile_wiki_entry(request: WikiCompileRequest) -> WikiCompileResponse:
    """使用 LLM 编译原始内容为 Wiki 条目"""
    _check_kb_locked()
    try:
        from backend.app import get_shared_provider
        provider = get_shared_provider()

        if not provider:
            return WikiCompileResponse(
                success=True,
                title=request.title_hint or "未命名知识",
                content=request.content,
                tags=[],
            )

        prompt = f"""请将以下内容编译成结构化的知识条目。

来源类型：{request.source_type}
{f'建议标题方向：{request.title_hint}' if request.title_hint else ''}

原始内容：
{request.content}

请分析内容并返回 JSON 格式（只返回 JSON，不要其他文字）：
{{
  "title": "简洁的标题（10字以内）",
  "tags": ["标签1", "标签2", "标签3"],
  "content": "使用 Markdown 格式编写的结构化内容，包含：\\n## 简介\\n简要说明\\n\\n## 详细内容\\n详细展开\\n\\n## 要点总结\\n- 要点1\\n- 要点2"
}}

要求：
1. 标题要简洁准确，体现核心概念
2. 标签3-5个，涵盖主题、领域、类型
3. 内容要结构化，使用 Markdown 格式
4. 提取关键信息，去除冗余
5. 保持客观准确"""

        response = await provider.chat_completion(
            prompt,
            max_tokens=3000,
            temperature=0.3,
        )

        # 解析 JSON 响应
        try:
            import json
            import re

            # 提取 JSON（可能被包裹在代码块中）
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = response.strip()

            data = json.loads(json_str)

            return WikiCompileResponse(
                success=True,
                title=data.get("title", request.title_hint or "编译的知识"),
                content=data.get("content", request.content),
                tags=data.get("tags", []),
            )
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from LLM response: {response[:200]}")
            # 回退到简单处理
            return WikiCompileResponse(
                success=True,
                title=request.title_hint or "编译的知识",
                content=response,
                tags=[],
            )
    except Exception as e:
        logger.exception(f"Failed to compile wiki entry: {e}")
        return WikiCompileResponse(
            success=False,
            title=request.title_hint or "编译失败",
            content=request.content,
            tags=[],
        )


# ============================================================================
# 文件上传
# ============================================================================


@router.post("/upload", response_model=WikiEntryResponse)
async def upload_file_to_wiki(
    file: UploadFile = File(..., description="上传的文件（PDF/DOCX/TXT/MD等）"),
    title: str = Form("", description="条目标题（留空则使用文件名）"),
    tags: str = Form("", description="标签，用逗号分隔"),
):
    """上传文件并解析为 Wiki 条目

    支持 PDF、DOCX、TXT、MD 等常见格式。
    文件内容会被自动提取为文本并保存为 Wiki 词条。
    """
    _check_kb_locked()
    import tempfile
    from backend.utils.file_parser import parse_file_to_text

    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    concepts_dir = _get_concepts_dir()
    service = get_wiki_service()

    # 确定标题
    entry_title = title.strip() if title.strip() else Path(file.filename).stem

    # 保存文件到临时目录并解析
    suffix = Path(file.filename).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        text_content = parse_file_to_text(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not text_content:
        raise HTTPException(status_code=400, detail="无法从文件中提取文本内容")

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    # 保存为 wiki 条目
    slug = _generate_slug(entry_title)
    md_content = f"---\ntitle: \"{entry_title}\"\nslug: {slug}\ntags: {tag_list}\n---\n\n{text_content}"

    md_file = concepts_dir / f"{slug}.md"
    md_file.write_text(md_content, encoding="utf-8")

    # 重建索引
    service.force_sync()

    logger.info(f"File uploaded as wiki entry: {slug}, title={entry_title}")

    return WikiEntryResponse(
        slug=slug,
        title=entry_title,
        content=text_content,
        tags=tag_list,
    )


# ============================================================================
# 知识库恢复 (FaceGuard 解锁用)
# ============================================================================


@router.post("/admin/restore")
async def restore_knowledge_base():
    """从备份恢复知识库 (FaceGuard 锁定后管理员恢复)"""
    from backend.modules.face_auth.router import get_guard
    guard = get_guard()
    if guard is None:
        raise HTTPException(400, "FaceGuard not available")

    kb_guard = guard.kb_guard
    if not kb_guard.is_locked:
        return {"status": "not_locked", "message": "知识库未被锁定"}

    result = await kb_guard.unlock(restore=True)
    service = get_wiki_service()
    service.force_sync()
    return {"status": result, "message": f"知识库已从备份恢复"}
