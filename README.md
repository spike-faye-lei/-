# 天团控制台 · 本地模型群聊指挥台

像群聊一样指挥本地 Ollama 多模型的桌面 App：发消息 → 模型像群成员一样流式回复；
像 Codex 一样实时看到每个模型什么时候在干什么、产出多少 token。**100% 本地算力，
零外网模型调用**（Ollama @ 127.0.0.1）。

## 功能

- **群聊式界面**：左栏会话列表 / 模型状态面板（岗位·状态·显存）/ 技能库 / 用量统计；中栏流式群聊（思维链折叠、token 速率、耗时指标）；右栏 Codex 式活动时间线（选模型 → 开工 → 产出 → 完成/出错）
- **两种指挥方式**：
  - **单模型对话**：七分类意图路由 → 按岗位派单（代码→代码师、数学→数学王、推理→推理师…），失败按关键词兜底
  - **🤝 天团模式**：四步流水线，四个人依次在群里发言，全程直播：代码师产出初稿 → 推理师审查挑刺 → 算法王代码复审 → 主审合并意见定稿 → 落盘
- **多轮上下文**：会话历史自动带入，可随时切换模型继续聊
- **技能 / 角色注入**：给本地模型带上 agentskills.io 开放标准的技能与角色 prompt，聊天和天团模式都生效
- **工具调用**：LS / READ / WRITE / RUN 四类工具，支持中文方括号、`~` 与环境变量路径
- **四档权限梯度**：只读 / 计划 / 询问 / 自动，贯穿聊天与天团模式
- **全离线前端**：原生 JS，无 CDN 依赖

## 快速开始

依赖：Python 3.10+，本机已安装 [Ollama](https://ollama.com) 并拉好模型。

```bash
pip install -r requirements.txt
py app.py                 # 桌面 App（pywebview 原生窗口）
# 或
py backend/main.py        # 纯后端，浏览器开 http://127.0.0.1:8777
```

Ollama 不在线时后端会自动拉起 `ollama serve`（最多等 30 秒）。

推荐模型配置（Ollama 拉取）：

```bash
ollama pull qwen2.5-coder:14b   # 代码师
ollama pull deepseek-r1:14b     # 推理师
ollama pull deepseek-coder-v2:16b  # 算法王
ollama pull qwen3:14b           # 主审
ollama pull qwen3:4b            # 路由
```

## 界面布局

```
┌──────────┬──────────────────────────┬──────────────┐
│ 会话列表  │                          │ 活动时间线    │
│ 模型面板  │    群聊（流式回复）        │ 实时直播：    │
│ 技能库    │    思维链折叠             │ 路由→开工→   │
│ 用量统计  │    工具批准卡片           │ 产出→完成    │
│ 记忆库    │                          │              │
└──────────┴──────────────────────────┴──────────────┘
```

## 后端 API（127.0.0.1:8777）

| 接口 | 说明 |
|---|---|
| `WS /ws` | 实时事件：chat_delta / thinking / done、team_step / done、models_changed… |
| `GET /api/skills` | 全机技能与角色资产清单 |
| `POST /api/chat` | 聊天 `{session_id?, message, model="auto", skills?, agent?, tools?, permission?}`，流式推送；`permission` 取 `readonly/plan/ask/yolo` |
| `POST /api/chat/cancel` | 停止生成 |
| `POST /api/team` | 天团四步流水线 `{session_id?, task}` |
| `GET /api/models` | 模型花名册状态（busy / 驻留显存 / 空闲） |
| `GET /api/sessions` · `GET /api/sessions/{id}/messages` | 会话与历史 |
| `GET /api/stats` | 按模型 token / 调用统计 |
| `POST /api/task` | 兼容旧任务队列 |
| `POST /api/memory` | 项目记忆存取 |

## 打包桌面 App

```bash
pip install pyinstaller pillow
py -m PyInstaller --noconfirm --onefile --windowed --name TeamConsole --icon icon.ico ^
  --add-data "backend;backend" --add-data "frontend;frontend" --paths . ^
  --hidden-import backend.main --collect-submodules uvicorn ^
  --hidden-import webview.platforms.edgechromium --hidden-import webview.platforms.winforms app.py
```

打包后运行时数据（tasks.db / outputs）存 `%LOCALAPPDATA%\TeamConsole`。

## 技术栈

Python 3.12 · FastAPI · uvicorn · pywebview · 原生 JS 前端（零 CDN）· PyInstaller

## 设计说明

- 直连 Ollama `/api/chat`，不依赖 LiteLLM 等额外桥接层，少一层常驻进程
- 用量记账与 `local-llm.py` 同一 CSV 格式，可接入每日用量报告
- 编排逻辑对齐 `team-run.py`（产出 → 双审 → 兜底）与 `router.py`（七分类路由）
