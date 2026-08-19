# 天团控制台 · 本地模型群聊指挥台

对着本地模型天团**直接下命令**的桌面 App：像群聊一样发消息，像 Codex 一样实时看到
每个模型什么时候在干什么、干得怎么样。**100% 本地算力**（Ollama @ 127.0.0.1），零外网模型调用。

## 启动

- **桌面 App**：双击桌面快捷方式「天团控制台」（或 `dist\TeamConsole.exe`）—— 独立原生窗口
- 开发态：`py app.py`；或 `py backend/main.py` 后开 http://127.0.0.1:8777

依赖：`pip install -r requirements.txt`（FastAPI + uvicorn + pywebview）。
Ollama 不在线时后端会自动拉起 `ollama serve`（等最多 30 秒）。

## 重新打包 exe

```bash
pip install pyinstaller pillow
py -m PyInstaller --noconfirm --onefile --windowed --name TeamConsole --icon icon.ico ^
  --add-data "backend;backend" --add-data "frontend;frontend" --paths . ^
  --hidden-import backend.main --collect-submodules uvicorn ^
  --hidden-import webview.platforms.edgechromium --hidden-import webview.platforms.winforms app.py
```
打包后数据（tasks.db / outputs）存 `%LOCALAPPDATA%\TeamConsole`。

## 界面（参考聊天软件 + Codex）

- **左栏**：会话列表 / 天团模型面板（岗位·状态·显存）/ **技能库（全机资产）** / 用量统计 + proj-memory 记忆库
- **中栏群聊**：你发命令 → 模型像群成员一样**流式回复**（带岗位头像、思维链折叠、
  `300 tok · 77 tok/s · 4.3s` 完成度指标）；多轮上下文自动带入
- **右栏时间线（Codex 式）**：实时直播 `路由器选模型 → 谁开工 → 产出多少 tok → 完成/出错`，
  天团模式下还有 1/4 步进度条
- **输入栏**：模型下拉（🤖自动路由 / 指定模型）、👤角色下拉、🧩技能勾选、🤝天团模式、发送/停止

## 全机技能/角色资产（都是 agentskills.io 开放标准，注入即用）

发消息前可给本地模型**带技能、扮角色**（等价 local-llm.py 的 --skill/--agent）：

- 技能 **690 个**：`~/.agents/skills`(568) + `~/.claude/skills`(78) + **Hermes** `D:\Hermes\skills`(21)
  + 官方插件(23)，skills-repos 兜底查找；左栏「技能」页可搜索勾选
- 角色 **124 个**：`~/.claude/agents`（local-coder/local-clerk 等天团岗位）+ 官方插件 agents
  （code-architect/pr-reviewer 等）+ `agents-backup`(83)，同名去重
- 选中后注入 prompt：`--- 技能 [名] 方法论 ---` + `--- 角色 [名] ---`，聊天和天团模式都生效

## 两种指挥方式

1. **单模型对话**（默认）：qwen3:4b 七分类路由 → 按岗位派单（代码→代码师、数学→数学王、
   推理→推理师…），失败按关键词兜底
2. **🤝 天团模式**：四步流水线，四个人依次在群里发言，全程直播
   1. 代码师 qwen2.5-coder:14b 产出初稿
   2. 推理师 deepseek-r1:14b 审查挑刺
   3. 算法王 deepseek-coder-v2:16b 代码复审
   4. 主审 qwen3:14b 合并意见定稿 → 落盘 `outputs/team-<id>/04-final.txt`

## 后端 API（127.0.0.1:8777）

| 接口 | 说明 |
|---|---|
| `WS /ws` | 实时事件：chat_delta/thinking/done、team_step/done、models_changed… |
| `GET /api/skills` | 全机资产清单：690 技能 + 124 角色（含 Hermes/插件） |
| `POST /api/chat` | 聊天 `{session_id?, message, model="auto", skills?, agent?, tools?, permission?}`，流式推送；`permission` 取 `readonly/plan/ask/yolo` |
| `POST /api/chat/cancel` | 停止生成 |
| `POST /api/team` | 天团四步流水线 `{session_id?, task}` |
| `GET /api/models` | 花名册状态（busy/驻留显存/空闲） |
| `GET /api/sessions` `GET /api/sessions/{id}/messages` | 会话与历史 |
| `GET /api/stats` | 按模型 token/调用统计（读 `~/.claude/logs/local-usage.csv`） |
| `POST /api/task` | 兼容旧任务队列（已修路径 bug） |
| `POST /api/memory` | 存 proj-memory 项目记忆 |

## 与天团工具链的关系

- 调用直连 Ollama `/api/chat`（不再依赖 LiteLLM 桥 4000 端口，省一层常驻进程）
- 用量记账与 `~/.claude/scripts/local-llm.py` 同一 CSV 格式，`daily-report.py` 继续可用
- 编排逻辑对齐 `~/.claude/scripts/team-run.py`（产出→双审→兜底）与 `router.py`（七分类）

## 2026-08-17 v2 补全记录（修复清单）

- 修复 `select_model()` router 路径解析错误（原指向不存在的 `D:\.claude\scripts\router.py`）
- 修复 router.py 输出被误当模型名（它打印的是任务结果）——路由改为后端内实现
- 去掉硬编码 Python 路径依赖；聊天/天团不再 subprocess 起子进程
- WebSocket 从 ping/pong 占位升级为真实事件推送（原来靠 5 秒轮询）
- 新增：多轮会话、流式输出、思维链、取消生成、天团进度、活动时间线、自动拉起 Ollama
- 新增：全机技能/角色资产接入（690 技能 + 124 角色，Hermes/插件/backup 全收）
- 新增：PyInstaller 打包桌面 App + 图标 + 桌面快捷方式
- 前端去 CDN（Vue CDN → 原生 JS），完全离线可用


## 2026-08-18 v3 修复（本次会话）

- 会话列表改为行级直接绑定点击，删除按钮不冒泡；加载会话失败时不再白屏。
- 修复工具调用：支持中文方括号/带项目符号/CRLF 的 LS/READ/WRITE/RUN 解析；路径支持 ~、环境变量与引号/括号清洗。
- 权限梯度贯穿聊天与天团模式：只读 / 计划 / 询问 / 自动 四档；选择会持久化到本机。
- 工具批准卡片在批准/拒绝/超时后会自动消失；停止生成会清理未决批准。
- 修复天团模式权限参数未传入各步骤的问题。
- 修复项目目录打开白名单的前缀绕过；记忆库写入现在检查子进程返回码。
- 桌面壳增加启动日志 `%LOCALAPPDATA%\TeamConsole\startup.log`、失败弹窗、单实例检测与浏览器兜底，解决“点快捷方式没反应”的问题。