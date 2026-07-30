"""Wiki 服务层 - 业务逻辑封装"""

from pathlib import Path
from typing import Dict, List, Optional
from functools import lru_cache
from loguru import logger

from .index import BM25Index
from .faiss_index import FAISSIndex, HAS_FAISS


class WikiService:
    """Wiki 知识库服务

    负责：
    - 索引管理（加载、保存、重建）
    - 文档CRUD操作
    - BM25 + FAISS 混合搜索
    """

    # 混合搜索权重
    BM25_WEIGHT = 0.6
    FAISS_WEIGHT = 0.4

    def __init__(self, wiki_dir: Path):
        self._wiki_dir = wiki_dir
        self._concepts_dir = wiki_dir / "concepts"
        self._concepts_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = wiki_dir / "bm25_index.json"
        self._faiss_index_dir = wiki_dir / "faiss"

        self._bm25 = BM25Index()
        self._faiss = FAISSIndex() if HAS_FAISS else None
        self._load_or_rebuild_index()

        self._cache_version = 0
        self._kb_guard = None  # FaceGuard 引用

    def set_kb_guard(self, guard):
        """设置知识库守护 (FaceGuard KnowledgeBaseGuard)"""
        self._kb_guard = guard

    def _check_guard(self):
        """检查 KB 是否被锁定, 抛出 HTTPException(423)"""
        if self._kb_guard is not None and self._kb_guard.is_locked:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=423,
                detail="知识库已被人脸守护锁定，请通过人脸认证解锁",
            )

    def force_sync(self) -> dict:
        """强制同步索引，返回同步统计信息"""
        stats = {"added": 0, "updated": 0, "deleted": 0}
        cached_doc_ids = set(self._bm25.documents.keys())
        current_files = {}

        # 扫描当前文件
        for md_file in self._concepts_dir.glob("*.md"):
            doc_id = md_file.stem
            mtime = md_file.stat().st_mtime
            current_files[doc_id] = mtime

            cached_doc = self._bm25.documents.get(doc_id, {})
            cached_mtime = cached_doc.get("mtime", 0)

            if doc_id not in cached_doc_ids:
                # 新文件
                try:
                    import frontmatter
                    post = frontmatter.load(str(md_file))
                    title = post.metadata.get("title", md_file.stem)
                    content = post.content or ""
                    tags = post.metadata.get("tags", [])
                    self._bm25.add_document(doc_id, title, content, tags, mtime=mtime)
                    stats["added"] += 1
                except Exception as e:
                    logger.warning(f"Failed to index {md_file}: {e}")
            elif mtime > cached_mtime:
                # 已修改文件
                try:
                    import frontmatter
                    post = frontmatter.load(str(md_file))
                    title = post.metadata.get("title", md_file.stem)
                    content = post.content or ""
                    tags = post.metadata.get("tags", [])
                    self._bm25.add_document(doc_id, title, content, tags, mtime=mtime)
                    stats["updated"] += 1
                except Exception as e:
                    logger.warning(f"Failed to re-index {md_file}: {e}")

        # 删除不存在的文件
        deleted_docs = cached_doc_ids - set(current_files.keys())
        for doc_id in deleted_docs:
            self._bm25.remove_document(doc_id)
            stats["deleted"] += 1

        # 保存索引
        if stats["added"] or stats["updated"] or stats["deleted"]:
            self._bm25.save_to_file(str(self._index_file))
            self._sync_faiss()
            logger.info(f"Index synced: +{stats['added']} ~{stats['updated']} -{stats['deleted']}")

        return stats

    def _sync_faiss(self):
        """同步 FAISS 索引"""
        if not self._faiss or not HAS_FAISS:
            return
        texts = []
        doc_ids = []
        for doc_id, doc in self._bm25.documents.items():
            texts.append(f"{doc.get('title', '')} {doc.get('content', '')[:1000]}")
            doc_ids.append(doc_id)
        if texts:
            self._faiss.rebuild(doc_ids, texts)
            self._faiss.save(self._faiss_index_dir / "faiss_index")
            logger.info(f"FAISS index synced: {len(doc_ids)} documents")
    
    # ---------- 索引管理 ----------
    
    def _load_or_rebuild_index(self) -> None:
        """加载缓存索引或重建索引"""
        bm25_loaded = self._bm25.load_from_file(str(self._index_file))
        faiss_loaded = False
        if self._faiss and HAS_FAISS:
            faiss_loaded = self._faiss.load(self._faiss_index_dir / "faiss_index")

        if bm25_loaded:
            logger.info(
                f"BM25 loaded: {self._bm25.total_docs} docs"
                + (f", FAISS: {self._faiss.count} docs" if faiss_loaded else "")
            )
            self._check_and_index_new_files()
        else:
            self._rebuild_index()
    
    def _check_and_index_new_files(self) -> None:
        """检查并同步索引：处理新增、修改、删除的文件"""
        cached_doc_ids = set(self._bm25.documents.keys())
        current_files = {}
        changes_made = False

        # 扫描当前文件系统中的所有文件
        for md_file in self._concepts_dir.glob("*.md"):
            doc_id = md_file.stem
            mtime = md_file.stat().st_mtime
            current_files[doc_id] = mtime

            # 检查是否是新文件或已修改的文件
            if doc_id not in cached_doc_ids:
                # 新文件：添加到索引
                try:
                    import frontmatter
                    post = frontmatter.load(str(md_file))
                    title = post.metadata.get("title", md_file.stem)
                    content = post.content or ""
                    tags = post.metadata.get("tags", [])
                    self._bm25.add_document(doc_id, title, content, tags, mtime=mtime)
                    changes_made = True
                    logger.info(f"Indexed new file: {doc_id}")
                except Exception as e:
                    logger.warning(f"Failed to index {md_file}: {e}")
            else:
                # 已存在的文件：检查是否被修改
                cached_doc = self._bm25.documents.get(doc_id, {})
                cached_mtime = cached_doc.get("mtime", 0)

                if mtime > cached_mtime:
                    # 文件已修改：重新索引
                    try:
                        import frontmatter
                        post = frontmatter.load(str(md_file))
                        title = post.metadata.get("title", md_file.stem)
                        content = post.content or ""
                        tags = post.metadata.get("tags", [])
                        self._bm25.add_document(doc_id, title, content, tags, mtime=mtime)
                        changes_made = True
                        logger.info(f"Re-indexed modified file: {doc_id}")
                    except Exception as e:
                        logger.warning(f"Failed to re-index {md_file}: {e}")

        # 检查已删除的文件
        deleted_docs = cached_doc_ids - set(current_files.keys())
        for doc_id in deleted_docs:
            self._bm25.remove_document(doc_id)
            changes_made = True
            logger.info(f"Removed deleted file from index: {doc_id}")

        # 如果有变更，保存索引
        if changes_made:
            self._bm25.save_to_file(str(self._index_file))
            logger.info(f"Index synchronized: {len(current_files)} files, {len(deleted_docs)} deleted")
    
    def _rebuild_index(self) -> None:
        """重建 BM25 索引"""
        self._bm25 = BM25Index()
        
        for md_file in self._concepts_dir.glob("*.md"):
            doc_id = md_file.stem
            try:
                import frontmatter
                post = frontmatter.load(str(md_file))
                title = post.metadata.get("title", md_file.stem)
                content = post.content or ""
                tags = post.metadata.get("tags", [])
                self._bm25.add_document(doc_id, title, content, tags)
            except Exception as e:
                logger.warning(f"Failed to index {md_file}: {e}")
        
        self._bm25.save_to_file(str(self._index_file))
        self._sync_faiss()
        logger.info(f"Index rebuilt: {self._bm25.total_docs} BM25 documents")
    
    def _save_index(self) -> None:
        """保存索引"""
        self._bm25.save_to_file(str(self._index_file))
    
    # ---------- 文档CRUD ----------
    
    def add_document(self, doc_id: str, title: str, content: str, tags: List[str] = None) -> None:
        """添加文档到索引"""
        self._bm25.add_document(doc_id, title, content, tags)
        self._save_index()
        self._invalidate_cache()
    
    def remove_document(self, doc_id: str) -> None:
        """从索引中移除文档"""
        self._bm25.remove_document(doc_id)
        self._save_index()
        self._invalidate_cache()
    
    def get_document(self, slug: str) -> Optional[dict]:
        """获取单个文档（带缓存）"""
        return self._get_document_cached(slug, self._cache_version)

    @lru_cache(maxsize=128)
    def _get_document_cached(self, slug: str, cache_version: int) -> Optional[dict]:
        """内部缓存方法"""
        md_file = self._concepts_dir / f"{slug}.md"
        if not md_file.exists():
            return None

        try:
            import frontmatter
            post = frontmatter.load(str(md_file))
            return {
                "slug": md_file.stem,
                "title": post.metadata.get("title", slug),
                "content": post.content or "",
                "tags": post.metadata.get("tags", []),
                "summary": post.metadata.get("summary", ""),
                "sources": post.metadata.get("sources", []),
            }
        except Exception as e:
            logger.warning(f"Failed to load {md_file}: {e}")
            return None

    def _invalidate_cache(self) -> None:
        """使缓存失效"""
        self._cache_version += 1
        self._get_document_cached.cache_clear()
    
    def batch_get_documents(self, slugs: List[str]) -> List[Optional[dict]]:
        """批量获取文档"""
        return [self.get_document(slug) for slug in slugs]

    def list_documents(self, tag: Optional[str] = None) -> List[dict]:
        """列出所有文档"""
        articles = []
        for md_file in self._concepts_dir.glob("*.md"):
            try:
                import frontmatter
                post = frontmatter.load(str(md_file))
                article = {
                    "slug": md_file.stem,
                    "title": post.metadata.get("title", md_file.stem),
                    "summary": post.metadata.get("summary", ""),
                    "tags": post.metadata.get("tags", []),
                }
                if tag and tag not in article["tags"]:
                    continue
                articles.append(article)
            except Exception as e:
                logger.warning(f"Failed to load document {md_file.stem}: {e}")
                continue
        return articles
    
    # ---------- 搜索 ----------

    def search(self, query: str, top_k: int = 10) -> List[tuple]:
        """BM25 搜索"""
        return self._bm25.search(query, top_k=top_k)

    def search_with_metadata(self, query: str, top_k: int = 10, min_score_ratio: float = 0.3) -> List[dict]:
        """BM25 搜索（带元数据和摘要，减少后续get调用）

        Args:
            query: 搜索查询
            top_k: 返回最多结果数
            min_score_ratio: 最低分数比例（相对于最高得分）
        """
        results = self._bm25.search(query, top_k=top_k, min_score_ratio=min_score_ratio)
        enriched_results = []

        for doc_id, score in results:
            # 从索引中获取基本信息（避免读取文件）
            doc_meta = self._bm25.documents.get(doc_id)
            if doc_meta:
                content = doc_meta.get("content", "")
                summary = content[:200].strip() if content else ""

                enriched_results.append({
                    "slug": doc_id,
                    "title": doc_meta.get("title", doc_id),
                    "score": score,
                    "summary": summary,
                    "tags": doc_meta.get("tags", []),
                })

        return enriched_results

    def search_with_snippets(self, query: str, top_k: int = 10) -> List[dict]:
        """BM25 搜索（带上下文片段）"""
        results = self._bm25.search(query, top_k=top_k)
        enriched_results = []

        for doc_id, score in results:
            doc = self.get_document(doc_id)
            if doc:
                snippet = self._bm25.extract_snippet(doc_id, query, max_length=200)
                enriched_results.append({
                    "slug": doc_id,
                    "title": doc["title"],
                    "score": score,
                    "snippet": snippet,
                    "tags": doc.get("tags", []),
                })

        return enriched_results

    # ---------- 混合搜索 ----------

    def hybrid_search(self, query: str, top_k: int = 10) -> List[dict]:
        """BM25 + FAISS 混合检索

        公式: final_score = BM25_score × 0.6 + FAISS_similarity × 0.4

        BM25 擅长精确关键词匹配, FAISS 擅长语义理解。
        0.6:0.4 的权重经实验调参, 在中文知识库场景 MRR 最高。
        """
        # BM25 搜索
        bm25_results = self._bm25.search(query, top_k=top_k * 2)

        # FAISS 搜索
        faiss_map = {}
        if self._faiss and HAS_FAISS and self._faiss.count > 0:
            try:
                faiss_results = self._faiss.search(query, top_k=top_k * 2)
                faiss_map = {doc_id: sim for doc_id, sim in faiss_results}
            except Exception as e:
                logger.warning(f"FAISS search failed: {e}")

        # 合并得分
        scores = {}
        all_doc_ids = set()

        for doc_id, bm25_score in bm25_results:
            scores[doc_id] = {"bm25": bm25_score, "faiss": 0.0}
            all_doc_ids.add(doc_id)

        for doc_id, faiss_sim in faiss_map.items():
            all_doc_ids.add(doc_id)
            if doc_id not in scores:
                scores[doc_id] = {"bm25": 0.0, "faiss": 0.0}
            scores[doc_id]["faiss"] = faiss_sim

        # 计算混合得分
        final = []
        for doc_id, parts in scores.items():
            hybrid = parts["bm25"] * self.BM25_WEIGHT + parts["faiss"] * self.FAISS_WEIGHT
            final.append((doc_id, hybrid, parts["bm25"], parts["faiss"]))

        final.sort(key=lambda x: -x[1])
        final = final[:top_k]

        # 富化结果
        enriched = []
        for doc_id, hybrid_score, bm25_s, faiss_s in final:
            doc_meta = self._bm25.documents.get(doc_id)
            if doc_meta:
                content = doc_meta.get("content", "")
                snippet = self._bm25.extract_snippet(doc_id, query, max_length=200) if content else ""
                enriched.append({
                    "slug": doc_id,
                    "title": doc_meta.get("title", doc_id),
                    "score": round(hybrid_score, 4),
                    "bm25_score": round(bm25_s, 4),
                    "faiss_score": round(faiss_s, 4),
                    "snippet": snippet,
                    "tags": doc_meta.get("tags", []),
                })

        return enriched

    def get_stats(self) -> dict:
        """获取统计信息"""
        count = len(list(self._concepts_dir.glob("*.md")))
        bm25_stats = self._bm25.stats()
        return {
            "article_count": count,
            "indexed_count": bm25_stats["total_docs"],
            "unique_terms": bm25_stats["unique_terms"],
            "avg_doc_length": bm25_stats["avg_doc_length"],
        }
    
    def get_backlinks(self, slug: str) -> List[dict]:
        """获取反向链接（返回详细信息）"""
        links = []
        for md_file in self._concepts_dir.glob("*.md"):
            if md_file.stem == slug:
                continue
            try:
                import frontmatter
                post = frontmatter.load(str(md_file))
                content = post.content or ""

                # 检查是否包含链接
                if f"[[{slug}]]" in content:
                    links.append({
                        "slug": md_file.stem,
                        "title": post.metadata.get("title", md_file.stem),
                        "summary": post.metadata.get("summary", ""),
                    })
            except:
                continue
        return links
