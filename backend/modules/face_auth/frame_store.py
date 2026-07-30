"""帧存储 - 为 FaceGuard 提供最新的摄像头帧"""
import asyncio
from typing import Optional


class FrameStore:
    """线程安全的帧缓冲区，存储最新一帧供 FaceGuard 拉取"""

    def __init__(self):
        self._frame: Optional[str] = None
        self._lock = asyncio.Lock()

    async def push(self, b64_frame: str) -> None:
        """存入最新帧"""
        async with self._lock:
            self._frame = b64_frame

    async def latest(self) -> Optional[str]:
        """获取最新帧，不阻塞"""
        async with self._lock:
            return self._frame

    async def clear(self) -> None:
        """清空缓冲区"""
        async with self._lock:
            self._frame = None


# 全局单例
_frame_store: Optional[FrameStore] = None


def get_frame_store() -> FrameStore:
    global _frame_store
    if _frame_store is None:
        _frame_store = FrameStore()
    return _frame_store
