# AI 项目集 · 2026（原型 / WIP · 7 个）

> 2026-08-15 天团流水线同批交付的 7 个探索性原型，完成度低于 Demo 批（见 `ai-projects-2026-demo` 分支）。
> 多为纯 FastAPI 后端、无前端、无测试，以记录思路为主，可继续迭代。仅供学习参考。

## 项目一览

| # | 项目 | 目录 | 端口 | 定位 | 状态 |
|---|---|---|---|---|---|
| 1 | Agent 调试器 | `agent-debugger` | 8701 | 记录 agent 多步调用链（输入/输出/耗时/决策），SQLite 回放分析 | 后端骨架 |
| 2 | 数据清洗 Copilot | `data-cleaning-copilot` | 8702 | 上传 CSV → 分析数据问题 → 建议清洗步骤 → dry-run → apply | 后端骨架 |
| 3 | DSH Skill Hub | `dsh-skill-hub` | 8693 | 扫描 SKILL.md 仓库 → SQLite 索引 → 搜索/详情/统计 | 后端+前端骨架 |
| 4 | 文件瘦身 | `file-declutter` | 8704 | 扫描目录：重复文件(MD5)/大文件/截图/安装包 → 清理计划 | 后端骨架 |
| 5 | 本地记忆索引 | `local-memory-index` | 8705 | 文档扫描 → SQLite + embedding 向量检索（接 bge-m3） | 后端骨架 |
| 6 | 操作录制回放 Agent | `record-replay-agent` | 8706 | 录制 UI 操作序列 → 回放风险评估 | 后端骨架 |
| 7 | Skill 评测 CI | `skill-eval-ci` | 8707 | 内置评测集测 skill 匹配准确率 | 后端骨架 |

## 快速开始

原型阶段未单独维护 requirements.txt，先装公共依赖：

```bash
pip install fastapi uvicorn pydantic httpx requests
# 个别项目额外依赖：
#   data-cleaning-copilot → pandas
#   file-declutter        → Pillow
#   record-replay-agent   → aiohttp

cd <项目目录>/backend
uvicorn main:app --port <端口>
```

> `dsh-skill-hub` 有前端：浏览器打开 `dsh-skill-hub/frontend/index.html`。

## 已知局限

- 仅后端骨架，多数无前端页面、无自动化测试
- 数据存内存或本地 SQLite，无鉴权、无持久化设计
- 部分项目（`dsh-skill-hub` / `skill-eval-ci` / `local-memory-index`）内部硬编码了 `D:\spike-faye-lei-dsh-skills` 等本机路径，跑之前需按自己环境改 `main.py` 里的路径常量

## 技术栈

`Python` `FastAPI` `SQLite` `pandas` `Pillow` `Ollama embedding`
