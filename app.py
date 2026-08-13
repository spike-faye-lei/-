"""招聘智能体 Demo：入口（界面装配 + 启动，含可选登录鉴权）

运行：双击 start.bat 或执行 python app.py，浏览器打开 http://localhost:7860

模块划分：
- ui_theme.py — 全局样式 token / 合规声明 / 静态资源路径
- handlers.py — 全部事件处理函数（业务接线）
- ui.py       — Gradio 界面装配（4 个 Tab 的组件与事件绑定）
- app.py      — 本文件：初始化数据库 + 启动（含可选登录鉴权）
"""
import logging
import os

import gradio as gr

import config  # noqa: F401  触发 .env 加载（API Key / ADMIN_USERNAME / ADMIN_PASSWORD）
from db import init_db
from ui import build_ui
from ui_theme import CSS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("recruit")

init_db()  # 启动时初始化 SQLite


def build_auth():
    """登录鉴权：.env 中同时设置 ADMIN_USERNAME / ADMIN_PASSWORD 才启用。

    未配置时保持免登录（本机演示模式），启动时打印提醒；
    对外部署前务必配置，否则任何人都能访问招聘数据。
    """
    user = os.environ.get("ADMIN_USERNAME", "").strip()
    pwd = os.environ.get("ADMIN_PASSWORD", "").strip()
    if user and pwd:
        logger.info("已启用登录鉴权（账号：%s）", user)
        # Gradio 6 要求 list[tuple[str, str]]：传列表，避免被按单字符迭代
        return [(user, pwd)]
    logger.warning(
        "未配置 ADMIN_USERNAME / ADMIN_PASSWORD，运行于免登录演示模式；"
        "对外部署前请在 .env 中配置（见 README「登录鉴权」一节）"
    )
    return None


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(
        theme=gr.themes.Soft(),
        css=CSS,
        auth=build_auth(),
        auth_message="招聘数据仅限内部访问，请输入访问账号密码",
    )
