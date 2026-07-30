"""FAISS 向量索引 - 语义相似度搜索"""
import json
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
from loguru import logger

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    logger.warning("faiss not installed, vector search disabled")


class FAISSIndex:
    """FAISS 向量搜索引擎

    使用 sentence-transformers 生成文档嵌入向量，
    通过 faiss.IndexFlatIP (内积) 进行语义相似度搜索。
    L2 归一化后内积等价于余弦相似度。
    """

    def __init__(self, dimension: int = 384, index_path: Optional[Path] = None):
        self.dimension = dimension
        self.index_path = index_path

        self._model = None
        self._index = None
        self._doc_ids: List[str] = []
        self._embeddings: Optional[np.ndarray] = None

        if HAS_FAISS:
            self._index = faiss.IndexFlatIP(dimension)

    # ---- 嵌入模型 ----

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(
                    'all-MiniLM-L6-v2',
                    device='cuda' if self._gpu_available() else 'cpu',
                )
                logger.info("Loaded sentence-transformers: all-MiniLM-L6-v2")
            except ImportError:
                logger.error("sentence_transformers not installed")
                raise
        return self._model

    @staticmethod
    def _gpu_available() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def encode(self, texts: List[str]) -> np.ndarray:
        """将文本列表编码为嵌入向量"""
        model = self._get_model()
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,  # L2 归一化
            show_progress_bar=False,
            batch_size=32,
        )
        return np.array(embeddings, dtype=np.float32)

    # ---- 索引操作 ----

    def add(self, doc_ids: List[str], texts: List[str]):
        """添加文档向量到索引"""
        if not texts:
            return
        embeddings = self.encode(texts)
        self._doc_ids.extend(doc_ids)
        self._index.add(embeddings)

        if self._embeddings is None:
            self._embeddings = embeddings
        else:
            self._embeddings = np.vstack([self._embeddings, embeddings])

    def remove(self, doc_id: str):
        """移除文档 (FAISS IndexFlatIP 不支持删除，重建)"""
        if doc_id in self._doc_ids:
            idx = self._doc_ids.index(doc_id)
            self._doc_ids.pop(idx)
            if self._embeddings is not None and idx < len(self._embeddings):
                self._embeddings = np.delete(self._embeddings, idx, axis=0)
                self._index = faiss.IndexFlatIP(self.dimension)
                if len(self._embeddings) > 0:
                    self._index.add(self._embeddings)

    def clear(self):
        """清空索引"""
        self._doc_ids = []
        self._embeddings = None
        self._index = faiss.IndexFlatIP(self.dimension)

    def rebuild(self, doc_ids: List[str], texts: List[str]):
        """完全重建索引"""
        self.clear()
        self.add(doc_ids, texts)

    # ---- 搜索 ----

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """语义搜索 - 返回 (doc_id, similarity)

        余弦相似度 = dot(归一化(query_emb), 归一化(doc_emb))
        L2归一化后直接内积即可
        """
        if not self._doc_ids or self._index.ntotal == 0:
            return []

        query_emb = self.encode([query])
        distances, indices = self._index.search(query_emb, min(top_k, self._index.ntotal))

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx < len(self._doc_ids):
                results.append((self._doc_ids[idx], float(dist)))

        return results

    # ---- 持久化 ----

    def save(self, path: Path):
        """保存索引到文件"""
        path.parent.mkdir(parents=True, exist_ok=True)

        # 保存 doc_ids 映射
        meta = {"doc_ids": self._doc_ids, "dimension": self.dimension}
        with open(str(path) + ".meta.json", 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False)

        # 保存 FAISS 索引
        if self._index.ntotal > 0:
            faiss.write_index(self._index, str(path) + ".faiss")

    def load(self, path: Path) -> bool:
        """从文件加载索引"""
        meta_path = str(path) + ".meta.json"
        faiss_path = str(path) + ".faiss"

        if not Path(meta_path).exists():
            return False

        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)

            self._doc_ids = meta.get("doc_ids", [])
            self.dimension = meta.get("dimension", 384)

            if Path(faiss_path).exists():
                self._index = faiss.read_index(faiss_path)
            else:
                self._index = faiss.IndexFlatIP(self.dimension)

            return True
        except Exception as e:
            logger.warning(f"Failed to load FAISS index: {e}")
            self._index = faiss.IndexFlatIP(self.dimension)
            self._doc_ids = []
            return False

    @property
    def count(self) -> int:
        return len(self._doc_ids)
