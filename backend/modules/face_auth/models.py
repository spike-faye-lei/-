"""Face Auth 数据模型 — 用户特征向量存储"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EnrolledUser:
    """注册用户记录"""
    username: str
    embedding: np.ndarray  # 128维 L2归一化向量
    enrolled_at: str = field(default_factory=lambda: datetime.now().isoformat())
    frame_count: int = 10
    version: int = 1

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "enrolled_at": self.enrolled_at,
            "frame_count": self.frame_count,
            "version": self.version,
        }


class FaceStorage:
    """人脸数据持久化管理

    存储格式:
    - face_data/username.npy → 嵌入向量 (float32[128])
    - face_data/metadata.json → 用户元信息
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_path = self.data_dir / "metadata.json"

    def save_embedding(self, username: str, embedding: np.ndarray):
        """保存嵌入向量"""
        np.save(str(self.data_dir / f"{username}.npy"), embedding)

    def load_embedding(self, username: str) -> Optional[np.ndarray]:
        """加载嵌入向量"""
        fpath = self.data_dir / f"{username}.npy"
        if fpath.exists():
            return np.load(str(fpath))
        return None

    def load_all_embeddings(self) -> Dict[str, np.ndarray]:
        """加载所有注册用户的嵌入向量"""
        result = {}
        for npy_file in self.data_dir.glob("*.npy"):
            result[npy_file.stem] = np.load(str(npy_file))
        return result

    def remove_user(self, username: str):
        """删除用户"""
        fpath = self.data_dir / f"{username}.npy"
        if fpath.exists():
            fpath.unlink()

    def list_users(self) -> List[str]:
        """列出所有用户"""
        return [f.stem for f in self.data_dir.glob("*.npy")]

    def user_count(self) -> int:
        return len(self.list_users())

    def save_metadata(self, users: List[EnrolledUser]):
        """保存用户元信息"""
        data = {u.username: u.to_dict() for u in users}
        self._metadata_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load_metadata(self) -> Dict[str, dict]:
        """加载用户元信息"""
        if not self._metadata_path.exists():
            return {}
        return json.loads(self._metadata_path.read_text())


class SimilarityMatcher:
    """相似度匹配器 — 余弦相似度 + 防模糊匹配"""

    def __init__(self, threshold: float = 0.60, margin: float = 0.10):
        self.threshold = threshold
        self.margin = margin  # 最高分与次高分最小差值

    def match(self, embedding: np.ndarray, gallery: Dict[str, np.ndarray]) -> Tuple[Optional[str], float, Dict[str, float]]:
        """匹配身份

        Args:
            embedding: 128维 L2归一化查询向量
            gallery: {username: 128维L2归一化向量}

        Returns:
            (best_match, best_score, all_scores)
        """
        scores: Dict[str, float] = {}
        for username, enrolled in gallery.items():
            scores[username] = float(np.dot(embedding, enrolled))  # L2 归一化后点积=余弦

        if not scores:
            return None, 0.0, {}

        sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
        best_user, best_score = sorted_scores[0]
        second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0

        # 阈值检查 + 防模糊匹配
        if best_score < self.threshold:
            return None, best_score, scores
        if best_score - second_score < self.margin and second_score > 0:
            return None, best_score, scores

        return best_user, best_score, scores
