"""FaceGuard - 人脸安全守护, 持续监控 + 自动KB锁定"""
import asyncio
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

from loguru import logger

from .pipeline import FacePipeline


class KnowledgeBaseGuard:
    """知识库守护 - 检测未授权访问时自动锁定"""

    def __init__(self, wiki_dir: Path, backup_dir: Optional[Path] = None):
        self.wiki_dir = Path(wiki_dir)
        self.backup_dir = backup_dir or self.wiki_dir.parent / "wiki_backups"
        self._locked = False
        self._lock_callbacks: list[Callable] = []

    @property
    def is_locked(self) -> bool:
        return self._locked

    def on_lock(self, callback: Callable):
        """注册锁定回调"""
        self._lock_callbacks.append(callback)

    async def lock(self) -> str:
        """锁定知识库: 备份 → 清除 → 设置标志"""
        if self._locked:
            return "already_locked"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"wiki_backup_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)

        # 备份所有 .md 文件
        backed_up = 0
        for md_file in self.wiki_dir.glob("**/*.md"):
            rel = md_file.relative_to(self.wiki_dir)
            dest = backup_path / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(md_file), str(dest))
            backed_up += 1

        # 删除原文件
        for md_file in self.wiki_dir.glob("**/*.md"):
            md_file.unlink()

        self._locked = True
        logger.warning(f"KB locked: {backed_up} files backed up to {backup_path}")

        # 触发回调
        for cb in self._lock_callbacks:
            try:
                cb()
            except Exception as e:
                logger.error(f"Lock callback failed: {e}")

        return str(backup_path)

    async def unlock(self, restore: bool = True) -> str:
        """解锁: 从最新备份恢复"""
        if not self._locked:
            return "not_locked"

        if restore:
            backups = sorted(self.backup_dir.glob("wiki_backup_*"), reverse=True)
            if backups:
                latest = backups[0]
                for md_file in latest.glob("**/*.md"):
                    rel = md_file.relative_to(latest)
                    dest = self.wiki_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(md_file), str(dest))
                logger.info(f"KB restored from {latest}")

        self._locked = False
        return "unlocked"


class FaceGuard:
    """人脸安全守护

    后台持续监控摄像头, 检测到未授权人脸时累加计数,
    达到阈值后触发 KB 锁定。
    """

    def __init__(
        self,
        pipeline: FacePipeline,
        kb_guard: KnowledgeBaseGuard,
        authorized_user: str,
        scan_interval: float = 3.0,
        unauthorized_threshold: int = 10,
        frame_capture: Optional[Callable] = None,
    ):
        self.pipeline = pipeline
        self.kb_guard = kb_guard
        self.authorized_user = authorized_user
        self.scan_interval = scan_interval
        self.unauthorized_threshold = unauthorized_threshold
        self.frame_capture = frame_capture  # async () → base64 str

        self.unauthorized_count = 0
        self._active = False
        self._task: Optional[asyncio.Task] = None

    @property
    def is_active(self) -> bool:
        return self._active

    async def start(self):
        """启动后台监控"""
        if self._active:
            return
        self._active = True
        self.unauthorized_count = 0
        self._task = asyncio.create_task(self._run())
        logger.info(f"FaceGuard started for user: {self.authorized_user}")

    async def stop(self):
        """停止监控"""
        self._active = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("FaceGuard stopped")

    async def _run(self):
        """主循环"""
        if self.frame_capture is None:
            logger.warning("FaceGuard: no frame_capture provided, running in dummy mode")
            return

        while self._active:
            try:
                await asyncio.sleep(self.scan_interval)

                # 捕获帧
                b64_frame = await self.frame_capture()
                if not b64_frame:
                    continue

                # 检测人脸
                result = self.pipeline.process_frame(b64_frame)
                if not result.get("success") or not result.get("faces"):
                    continue  # 无人脸

                # 识别身份
                any_authorized = False
                any_unauthorized = False
                for face in result["faces"]:
                    if face.get("identified"):
                        if face.get("username") == self.authorized_user:
                            any_authorized = True
                        else:
                            any_unauthorized = True

                if any_authorized and not any_unauthorized:
                    # 仅看到授权用户 → 重置计数
                    if self.unauthorized_count > 0:
                        logger.debug(f"Authorized user detected, reset count")
                    self.unauthorized_count = 0
                elif any_unauthorized:
                    self.unauthorized_count += 1
                    logger.warning(
                        f"Unauthorized face #{self.unauthorized_count}/"
                        f"{self.unauthorized_threshold}"
                    )

                # 达到阈值 → 锁定
                if self.unauthorized_count >= self.unauthorized_threshold:
                    backup_path = await self.kb_guard.lock()
                    logger.critical(
                        f"FaceGuard triggered KB lock! Backup: {backup_path}"
                    )
                    self._active = False

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"FaceGuard error: {e}")

    def reset(self):
        """重置计数 (授权用户重新认证后调用)"""
        self.unauthorized_count = 0
        logger.info("FaceGuard count reset")

    def get_status(self) -> dict:
        return {
            "active": self._active,
            "authorized_user": self.authorized_user,
            "unauthorized_count": self.unauthorized_count,
            "threshold": self.unauthorized_threshold,
            "kb_locked": self.kb_guard.is_locked,
        }
