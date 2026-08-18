"""可配置简历数据源（P2）：统一接口，本地文件为默认实现，招聘平台为适配器占位

生产目标：系统每天自动从 BOSS 直聘/猎聘拉取新简历（官方 API + 企业授权），
HR 不需要手动上传。各平台接入细节见 docs/02-招聘平台对接技术方案与工时成本.md。

接口约定：
    fetch_new_resumes(since) -> [{"name", "resume_text", "source", "resume_file"}]
"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import os

from algorithms import extract_fields
from file_parser import extract_text

SOURCES = ["本地文件夹", "BOSS直聘（API 适配位）", "猎聘（API 适配位）", "智联招聘（API 适配位）"]


class ResumeDataSource(ABC):
    """简历数据源抽象接口：所有来源统一产出候选人 dict 列表"""

    @abstractmethod
    def fetch_new_resumes(self, since: datetime) -> list:
        """获取某时间点之后的新简历"""


class LocalFileSource(ResumeDataSource):
    """本地文件夹数据源（默认实现，演示/内推场景）"""

    def __init__(self, folder_path: str):
        self.folder_path = folder_path

    def fetch_new_resumes(self, since: datetime = None) -> list:
        exts = {".pdf", ".docx", ".txt", ".md"}
        out = []
        if not self.folder_path or not os.path.isdir(self.folder_path):
            return out
        for fn in sorted(os.listdir(self.folder_path)):
            path = os.path.join(self.folder_path, fn)
            if os.path.splitext(fn)[1].lower() not in exts:
                continue
            try:
                text = extract_text(path)
                if not text.strip():
                    continue
            except Exception:
                continue
            if since is not None and os.path.getmtime(path) < since.timestamp():
                continue  # 增量：只取 since 之后的文件
            name = extract_fields(text).get("name") or os.path.splitext(fn)[0]
            out.append({"name": name, "resume_text": text, "source": "本地文件夹", "resume_file": path})
        return out


class BossZhipinSource(ResumeDataSource):
    """BOSS 直聘数据源（适配器占位）——接入前需：企业认证 + 开放平台权限申请

    对接细节（docs/02）：拉取频率 2 小时/次、字段映射表、token 刷新、异常重试。
    """

    def fetch_new_resumes(self, since: datetime) -> list:
        raise NotImplementedError("BOSS 直聘官方 API 未接入（需企业资质与开放平台审批，方案见 docs/02）")


class LiepinSource(ResumeDataSource):
    """猎聘数据源（适配器占位）——企业版简历推送接口"""

    def fetch_new_resumes(self, since: datetime) -> list:
        raise NotImplementedError("猎聘官方 API 未接入（方案见 docs/02）")


def get_source(source_name: str, folder_path: str = "") -> ResumeDataSource:
    """按名称获取数据源实例（UI 下拉切换）"""
    if source_name == "本地文件夹":
        return LocalFileSource(folder_path)
    if source_name == "BOSS直聘（API 适配位）":
        return BossZhipinSource()
    if source_name == "猎聘（API 适配位）":
        return LiepinSource()
    return LocalFileSource(folder_path)
