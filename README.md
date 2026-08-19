# AI 应用开发作品集

> 计算机科学与技术专业 · 2026 届本科在读
> 毕设「SmartKitchen 智能厨房」+ 开源鸿蒙参赛项目 + AI 智能体 Demo，全部源码开源于此仓库（一仓多分支）。

##  项目一览

| 项目 | 一句话介绍 | 分支 | 技术栈 |
|---|---|---|---|
| **SmartKitchen 后端** | CLIP 迁移学习 + 知识蒸馏的食材识别（15 类 92.69%），营养分析 + 菜谱推荐 | `smartkitchen`（见下方 Gitee 仓库） | Python · FastAPI · PyTorch · CLIP · SQLite |
| **SmartKitchen 鸿蒙端** | HarmonyOS NEXT 食材识别 APP：拍照识别、营养、菜谱、饮食记录、人脸识别 | `harmonyos-app` | ArkTS · HarmonyOS NEXT (API 24) |
| **AI 招聘官** | 多考官证据链评分 + AI 互聊面试 + 联网爬虫 + HR 审核闸门，全流程可演示 | `recruit-agent` | Python · Gradio · LangChain 风格 · DeepSeek API · matplotlib |
| **CountBot 定制版** | 人脸识别计数机器人（答辩演示项目） | `countbot` | Python · OpenCV |
| **天团控制台** | 本地 Ollama 多模型群聊指挥台：七分类路由 + 四步天团流水线，桌面 App 全离线 | `team-console` | Python · FastAPI · pywebview · Ollama |
| **AI 项目集 2026（Demo）** | 天团交付的 6 个可演示小项目：工单 Agent / NFC 安全验证 / NFC 智能感知 / 防遗忘盾牌 / 刷题计划 / 算法可视化 | `ai-projects-2026-demo` | Python · FastAPI · Vue3 · DeepSeek API |
| **AI 项目集 2026（WIP）** | 天团交付的 7 个探索性原型：Agent 调试器 / 数据清洗 Copilot / Skill Hub / 文件瘦身 / 记忆索引 / 录制回放 / Skill 评测 | `ai-projects-2026-wip` | Python · FastAPI · SQLite · pandas |

> 各分支内有各自项目的详细 README（功能说明、架构、启动步骤）。SmartKitchen 后端源码在 Gitee 同名仓库的 `smartkitchen` 分支（见文末链接）。

##  核心亮点

**SmartKitchen（毕设 · 参赛）**
- 食材识别：CLIP 视觉模型迁移学习 + 知识蒸馏（teacher→student CNN），15 类食材 **92.69%** 准确率，手机端可部署
- 数据：Fruits-360 + 真实厨房场景自采数据，含噪声数据清洗流程
- 全链路：识别 → 营养分析 → 菜谱推荐 → 饮食记录统计

**AI 招聘官（智能体 Demo）**
- 多考官证据链评分：技术/文化双考官按维度评分并引用候选人原话，**加权总分由代码计算**（不信任 LLM 算数），低 temperature 保证可复现
- AI 互聊：招聘官 AI 与候选人 AI 全程自动面试，动态追问难度，流式打字机效果
- 合规爬虫：V2EX 公开招聘帖（真实 JD）+ Gitee 公开开发者档案（真实候选人简历），失败自动回退，随机轮换
- HR 审核闸门：**AI 只建议、人决定**——报告先过人工审核才发线下面邀，符合 PIPL 合规叙事
- 数据分析看板：雷达图 + 维度条形图 + 考官分组对比 + 总分（matplotlib）
- 批量初筛 / 候选人对比 / JD 生成 / 面试题库生成
- **68 个自动化测试**（pytest）全部通过

**天团控制台（本地模型编排）**
- 像群聊一样指挥本地 Ollama 多模型：流式回复、思维链折叠、Codex 式活动时间线
- 单模型对话七分类意图路由；**天团模式**四步流水线（产出 → 双审 → 兜底定稿）全程直播
- 技能 / 角色 prompt 注入（agentskills.io 开放标准）、工具调用、四档权限梯度
- 直连 Ollama，零外网模型调用；PyInstaller 打包桌面 App

##  快速开始

每个项目分支的 README 里都有独立启动步骤，例如：

```bash
# AI 招聘官
git clone https://github.com/spike-faye-lei/-.git -b recruit-agent
cd - && pip install -r requirements.txt
python app.py   # 浏览器打开 http://localhost:7860
```

```bash
# SmartKitchen 鸿蒙端：用 DevEco Studio 打开 harmonyos-app 分支
```

##  技术栈

`Python` `FastAPI` `PyTorch` `CLIP` `LangChain 风格编排` `DeepSeek API` `Gradio` `matplotlib` `SQLite` `HarmonyOS NEXT (ArkTS)` `Ollama` `pywebview` `pytest`

##  联系

- 邮箱：2250461965@qq.com
- Gitee（SmartKitchen 后端）：https://gitee.com/H2250461965/hongmeng-c/tree/smartkitchen
- 本仓库各分支：countbot / harmonyos-app / recruit-agent / team-console / ai-projects-2026-demo / ai-projects-2026-wip
