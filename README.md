# AI 项目集 · 2026（可演示 Demo · 6 个）

> 2026-08-15 由本地模型天团（Ollama 多模型自治流水线：产出 → 双审查 → 主审兜底）交付的 6 个可演示项目。
> 统一技术栈：**FastAPI 后端 + 纯静态 Vue3 前端**，数据内存存储（演示级），开箱即跑。

## 项目一览

| # | 项目 | 目录 | 端口 | 一句话说明 |
|---|---|---|---|---|
| 1 | 工单 Agent | `ticket-agent` | 8687 | 自然语言生成工单：意图识别 + 知识库检索 + 政策审核（接 DeepSeek） |
| 2 | NFC 安全验证 | `nfc-ai-auth` | 8688 | 写卡 AI 校验 + 挑战-响应 HMAC 认证 + 篡改检测（接 DeepSeek） |
| 3 | NFC 智能感知 | `nfc-sense-agent` | 8690 | 刷卡模式分析（连续加班 / 异常频次）→ LLM 提醒（接 DeepSeek） |
| 4 | 防遗忘盾牌 | `anti-forget-shield` | 8691 | 艾宾浩斯复习计划 + 打卡推进 + 遗忘风险分级 |
| 5 | 刷题计划生成器 | `leetcode-planner` | 8692 | 刷题计划分配 + 难度递进 + 打卡进度统计 |
| 6 | 算法可视化 | `algo-visualizer` | 无后端 | 冒泡 / 快排 / 归并动画，步进 / 速度 / 暂停 / 重置 |

## 快速开始

项目 1-5（FastAPI 后端）：

```bash
cd <项目目录>/backend
pip install -r requirements.txt
uvicorn main:app --port <端口>
```

前端：浏览器直接打开 `<项目目录>/frontend/index.html`。

项目 6 `algo-visualizer` 无后端，直接双击打开 `algo-visualizer/index.html`。

## 依赖 LLM 的项目（1 / 2 / 3）

项目 1 / 2 / 3 调用 DeepSeek API（Anthropic 兼容端点），需先在 `backend/` 下创建 `.env`：

```bash
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE=https://api.deepseek.com/anthropic/v1/messages
DEEPSEEK_MODEL=deepseek-v4-pro
```

> `.env` 已被 `.gitignore` 排除，不会提交；不配置 key 也能本地起服务，只是调用 LLM 的接口会返回缺 key 提示。

## 技术栈

`Python` `FastAPI` `Vue3` `DeepSeek API` `HMAC 认证` `艾宾浩斯记忆曲线` `排序算法可视化`
