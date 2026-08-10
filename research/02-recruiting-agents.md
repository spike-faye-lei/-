# GitHub AI 招聘智能体开源项目研究报告

> 调研时间：2026-08-06，数据来自 GitHub Search API 实时结果（star 数为当时 approx 值）
> 调研目的：为招聘智能体 Demo（Python + Gradio + DeepSeek API，简历解析→AI 初筛→AI 互相聊天→筛选决策→面试邀约）提供参考学习

## 一句话总结

**这类项目的主流方案是「简历/岗位文档解析（PDF→Markdown→LLM 结构化 JSON）→ 规则/关键词硬过滤 + LLM 评分（角色化 rubric + 证据链）→ 多智能体协作（AutoGen/LangGraph/CrewAI 编排筛选、面试、数据管理 Agent）→ 可解释报告 + CSV/数据库台账」，头部项目（HackerRank hiring-agent 6.7k★、AIHawk 30k★）均已验证：评分必须带证据、多智能体适合做流程编排而非"聊天表演"、不可逆动作（拒人/约面）必须人工确认。**

---

## 一、项目总览表

### 1. 招聘方视角（HR/企业侧，与我们的 Demo 直接相关）

| 仓库 | star | 语言 | 功能一句话 |
|---|---|---|---|
| [interviewstreet/hiring-agent](https://github.com/interviewstreet/hiring-agent) | 6767 | Python | HackerRank 官方开源的"简历→评分"流水线：PDF 解析、GitHub 信号增强、角色化 rubric 可解释评分 |
| [stepanogil/autonomous-hr-chatbot](https://github.com/stepanogil/autonomous-hr-chatbot) | 458 | Python | 可工具调用的自主 HR agent，回答员工/候选人查询 |
| [jiatastic/GPTInterviewer](https://github.com/jiatastic/GPTInterviewer) | 262 | Python | 基于 JD + 简历的 AI 面试官（模拟面试提问，非闲聊） |
| [he-yufeng/FindJobs-Agent](https://github.com/he-yufeng/FindJobs-Agent) | 252 | Python | LLM 工具包：技能分析、AI 面试（自适应难度）、简历评分、岗位结构化 |
| [1146345502/aural-oss](https://github.com/1146345502/aural-oss) | 185 | TypeScript | 开源 AI 面试平台：语音/聊天/视频多模态面试 |
| [tonykipkemboi/resume-optimization-crew](https://github.com/tonykipkemboi/resume-optimization-crew) | 153 | Python | CrewAI 多智能体：分析 JD、简历匹配评分、给出优化建议 |
| [LQF-dev/smart-hr](https://github.com/LQF-dev/smart-hr) | 62 | Java | 智能招聘助手：Spring AI + Neo4j 知识图谱 + Milvus RAG |
| [FreeAiHR/FreeAiHR](https://github.com/FreeAiHR/FreeAiHR) | 57 | Python | 企业级 AI 招聘全流程：AI 一面、AI 简历、AI 考评、人才库、漏斗分析，支持私有化 |
| [Chandrika9906/AI-Resume-Screening](https://github.com/Chandrika9906/AI-Resume-Screening) | 57 | JavaScript | AI 简历筛选 Web 应用 |
| [Okes2024/AI-based-Resume-Screening-for-Cultural-Fit](https://github.com/Okes2024/AI-based-Resume-Screening-for-Cultural-Fit) | 51 | Python | 用 AI 筛"文化契合度"：价值观、工作风格、软技能匹配 |
| [312323205202/ai-resume-screening-system](https://github.com/312323205202/ai-resume-screening-system) | 50 | Python | 完整流水线：AWS S3 提取简历→LLM 按 HR 标准分类→SQLite 存储→邮件/WhatsApp 自动通知 |
| [Ancastal/AI-Recruitment-Agent](https://github.com/Ancastal/AI-Recruitment-Agent) | 48 | Python | Microsoft AutoGen 多智能体招聘助手：Screening/Interview/Data 三个 Agent 协作 |
| [tuanductran/hr-skills](https://github.com/tuanductran/hr-skills) | 43 | TypeScript | HR 技能包：AI 招聘知识与技术招聘 SOP（skill 形式） |
| [MonishRaman/Placify](https://github.com/MonishRaman/Placify-Smarter_Placements-Sharper_Talent) | 31 | JavaScript | 校招平台：简历筛选、自适应测评、个性化反馈 |
| [Viy1204/recruiting-copilot](https://github.com/Viy1204/recruiting-copilot) | 29 | Shell | 中文！HR/猎头 AI 招聘工作流：Boss直聘+猎聘双通道寻源初筛、简历评估、约面试、台账日报 |
| [bcefghj/smart-hiring-pipeline](https://github.com/bcefghj/smart-hiring-pipeline) | 23 | Python | 5-Agent 多智能体招聘管道（面试指南+八股文+STAR 法） |
| [1xiaoyueryuer/boss-hr-agent-toolkit](https://github.com/1xiaoyueryuer/boss-hr-agent-toolkit) | 20 | Python | BOSS 直聘 HR 智能体工具箱（中文招聘平台对接） |
| [umairalipathan1980/Resume-Screening-AI-Agent-with-Claude-s-Skills](https://github.com/umairalipathan1980/Resume-Screening-AI-Agent-with-Claude-s-Skills) | 19 | Python | Claude Agent SDK：extract→assess→validate→generate 简历筛选工作流 |
| [manthan89-py/AI-Based-Recruitment-System](https://github.com/manthan89-py/AI-Based-Recruitment-System) | 17 | Python | AI 招聘系统：加速 HR 和技术招聘的筛选流程 |
| [zubair-trabzada/ai-recruiter-claude](https://github.com/zubair-trabzada/ai-recruiter-claude) | 13 | Python | Claude Code 招聘引擎：14 个 skill、5 个并行 agent，JD 优化/批量筛选/面试框架 |
| [andrew-shwetzer/recruiter-plugin](https://github.com/andrew-shwetzer/recruiter-plugin) | 12 | Python | Claude Code 插件：22 个招聘 skill，候选人寻源/筛选/外联/管道跟踪，ATS 集成 |
| [NissonCX/smart-ats](https://github.com/NissonCX/smart-ats) | 11 | Java | 智能 ATS：AI 简历解析 + RAG 语义搜索 + 异步管道 + 招聘漏斗分析（智谱AI + Milvus） |
| [kk43994/bosszhipinzhushou](https://github.com/kk43994/bosszhipinzhushou) | 11 | JavaScript | Boss直聘筛选助手：自动分析简历、智能打分、智能回复 |
| [NehaBharti16/AI-Recruitment-Copilot](https://github.com/NehaBharti16/AI-Recruitment-Copilot) | 10 | Python | AI 招聘副驾 |
| [DomUmaru/recruit-agent](https://github.com/DomUmaru/recruit-agent) | 7 | Java | ToB 企业级智能招聘与面试辅助 Agent 系统 |
| [ahmedeltaher/Talent-Acquisition-Agent](https://github.com/ahmedeltaher/Talent-Acquisition-Agent) | 3 | Python | 自主多智能体平台：端到端招聘流程、最少人工干预 |
| [rookie-wy/HireFlow](https://github.com/rookie-wy/HireFlow) | 0 | Python | 多 Agent 招聘系统：简历解析→多维匹配→多专家精筛（辩论-仲裁）→面试调度→人才池，LangGraph + DeepSeek + Streamlit |

### 2. 中文关键词搜索结果（"AI招聘" 78 条、"招聘智能体" 7 条、"招聘Agent" 8 条、"人才筛选" 4 条）

| 仓库 | star | 语言 | 功能一句话 |
|---|---|---|---|
| [impengpong/jitou](https://github.com/impengpong/jitou) | 164 | - | 即投：BOSS 直聘 AI 自动投递助手（求职者侧） |
| [liangdabiao/resume-matcher-agent-cn](https://github.com/liangdabiao/resume-matcher-agent-cn) | 146 | HTML | "HR批评"简历智能体：模拟 HR 筛选简历，展示关键词/格式/洞察（求职者侧） |
| [heathcetide/zhipin-ai](https://github.com/heathcetide/zhipin-ai) | 12 | Java | 智聘通：Spring Boot + ChatGLM 在线 AI 招聘系统 |
| [FeixueCode/hound-system-v0.1](https://github.com/FeixueCode/hound-system-v0.1) | 3 | Python | 中文招聘助手：不打分只数命中，三层独立评估（任务/能力/事件）+ HR vs 用人部门双维议事 |
| [zhaoyangyang666/AIHR](https://github.com/zhaoyangyang666/AIHR) | 3 | Python | 自动评估简历 + 生成面试题 + AI 搜索简历 |
| [stonelight1/hr-interview-analysis](https://github.com/stonelight1/hr-interview-analysis) | 3 | Python | 从简历筛选→面试评估→录用建议的中文 AI 招聘辅助 |
| [yenns7/zhipin-recruit](https://github.com/yenns7/zhipin-recruit) | 2 | Python | 智聘：LangGraph ReAct 智能体，简历解析/匹配/AI 面试/Offer 子流程/BI 看板全闭环 |
| [steve-joking/offeragent](https://github.com/steve-joking/offeragent) | 0 | Python | 智能招聘智能体：自动搜索、筛选、投递职位 |
| [silverenternal/waibao](https://github.com/silverenternal/waibao) | 0 | Python | AI-native 招聘智能体：16 个智能体协同，服务求职者+用人单位双向匹配 |
| [2892480843/TrustHire-AI](https://github.com/2892480843/TrustHire-AI) | 0 | TypeScript | 可信招聘智能体：岗位能力解析、简历证据链分析、人岗匹配评分、AI 面试任务生成 |
| [siuserxiaowei/hr-agent-reading-hub](https://github.com/siuserxiaowei/hr-agent-reading-hub) | 2 | JavaScript | HR 招聘 Agent 阅读台：飞书、Agent 方法论与招聘自动化资料库 |
| [linruibang19-home/Recruitment-Agent](https://github.com/linruibang19-home/Recruitment-Agent) | 0 | Python | Boss直聘企业端自动化招聘 agent |

**说明**：中文关键词总体偏少——"招聘智能体"仅 7 条、"招聘Agent" 8 条、"人才筛选" 4 条，且多数是 0-5 star 的个人作品或介绍页（如 qiaozhoua/aling-recruit-agent 只是数字人宣传页，已排除）。中文赛道开源生态明显弱于英文，多数中文项目挂在"AI招聘"（78 条）和"智能招聘"（140 条，多为毕业设计）下。**这一空白对我们是有利的：Demo 做成中文场景（Boss直聘式候选人沟通）在开源领域几乎没有直接竞品。**

### 3. 求职者侧相关（主动外联/投递，架构可反向参考）

| 仓库 | star | 语言 | 功能一句话 |
|---|---|---|---|
| [feder-cr/Jobs_Applier_AI_Agent_AIHawk](https://github.com/feder-cr/Jobs_Applier_AI_Agent_AIHawk) | 30111 | Python | 全球最火的 AI 求职 Agent：自动搜索职位、定制简历、批量投递 |
| [srbhr/Resume-Matcher](https://github.com/srbhr/Resume-Matcher) | 28048 | TypeScript | 简历匹配器：本地 LLM 解析简历与 JD 计算匹配分 |
| [YIKUAIBANZI/job-hunter](https://github.com/YIKUAIBANZI/job-hunter) | 25 | Python | Claude Code skill：读简历、按分数匹配 JD、Boss直聘/鱼泡直聘批量投递 |
| [impengpong/jitou](https://github.com/impengpong/jitou) | 164 | - | 即投：BOSS 直聘 AI 自动投递 |
| [lastIndexOf/ai-boss](https://github.com/lastIndexOf/ai-boss) | 29 | TypeScript | GPT 根据简历+JD 自动生成问候语并投递的浏览器插件 |

---

## 二、重点项目深入分析

### 1. interviewstreet/hiring-agent（6767★，Python，MIT，HackerRank 官方）—「简历→评分」流水线的行业标杆

**背景**：HackerRank 每年收到 5-6 万份实习生简历，人力无法全部精读，此工具用于排序"先读谁的"。官方明确：它**不是** ATS、**不用**于筛选自家正式职位；分数低于 cutoff 才会被过滤，且 cutoff 故意设得很低，只剔除分布最末端的简历，绝大多数简历仍进入人工评审。生产环境用 Gemini 顶级模型，仓库默认用 `gemma4:latest`（本地 Ollama 可跑）。

**完整流水线（5 个阶段）**：

1. **PDF 提取**：`pymupdf_rag.py` 用 PyMuPDF 把 PDF 每页转成 Markdown 风格文本（处理标题、链接、表格）。
2. **分段解析**：`pdf.py` 按 section（basics/work/education/skills/projects/awards）分别调 LLM 提取，用 `prompts/templates/*.jinja` 模板约束输出，最后组装成 `JSONResume`（Pydantic 模型）——**逐段解析比整份一次性解析准确率高**。
3. **GitHub 信号增强**：`github.py` 从简历提取 GitHub 用户名 → 拉 profile 和 repos → LLM 给项目分类并精选恰好 7 个（要求作者 commit 数达到阈值）——**简历之外补外部证据**。
4. **评估**：`evaluator.py` 用**角色化 rubric** 打分。每个角色是一个目录 `roles/<role>/`，内含 `role.json`（类别+权重+分数界限）、`criteria.jinja`（评估标准提示词）、`system_message.jinja`（公平性规则）。默认的 `software_engineering_intern` 角色权重：
   - open_source（开源贡献）35 分、self_projects（个人项目）30 分、production（生产经验）25 分、technical_skills（技术栈）10 分；另有 bonus_max 20、分数区间 -20 ~ 120。
   - **关键实现**：调 LLM 时把 Pydantic 模型的 `model_json_schema()` 作为 `format` 参数做**结构化输出约束**（Ollama/Gemini 都支持），temperature 0.5，要求每项评分附 evidence。
5. **输出**：终端报告 + `DEVELOPMENT_MODE` 下缓存中间 JSON、追加 `resume_evaluations_<role>.csv`。

**值得借鉴**：
- 评分结构完全配置化：权重、类别、bonus、分数上下限都在 `role.json`，换岗位只换目录
- 提示词全部是 Jinja 模板与代码分离，且要求"prompts 保持声明式、provider 无关"
- 结构化输出用 JSON schema 而非自由文本解析

**社区暴露的问题（对我们极有参考价值）**：
- **LLM 评分方差大**：同一份简历跑 100 次得分 74-90 波动（Dan Kinsky 统计分析）；技术技能维度稳定、项目质量判断维度噪声大
- **安全漏洞**：PDF 里嵌隐形文字可以显著抬高分数（Pinggy 复现）→ 需要 PDF 内容审计
- **公平性**：GitHub 中心化 rubric 对私企仓库工程师不公平；rubric 公开后候选人会反向优化简历
- **合规**：GDPR Art 22 对"纯自动化决策"的限制（HN 讨论 200+ 楼）
- 社区建议的改进：标准化数据格式、版本化评估模型、**ensemble 多次评分**、可解释层

### 2. rookie-wy/HireFlow（0★，Python，MIT）— 与我们的 Demo 概念重合度最高的设计（技术栈同为 DeepSeek + Streamlit）

star 虽为 0，但它的设计蓝图几乎就是我们 Demo 的目标形态，且技术栈高度一致（LangGraph + LiteLLM(DeepSeek) + ChromaDB + MySQL + Streamlit + Celery），值得逐条对照。

**全链路流程**：
1. **解析层**：简历用 MinerU + pdfplumber 双链路提取（PDF/Word/图片），LLM 结构化输出候选人档案；JD 自动提取硬性条件、软性要求、技能图谱，生成标准化岗位画像
2. **混合粗筛**：HyDE 查询改写 + 稠密/稀疏双路召回 + RRF 融合 + Cross-Encoder 重排序 + Self-RAG 反思——传统 RAG 检索式粗筛，而非纯 LLM 打分
3. **多 Agent 精筛**：按岗位类别**动态激活**面试官/技能评估/文化契合等 Agent，支持**辩论-仲裁机制**（多个 Agent 各自评估后辩论，仲裁者给最终结论）
4. **可解释报告**：综合得分 + 维度小分 + 推荐理由 + **原文证据高亮**
5. **记忆与反馈**：短期记忆支持断点恢复；长期记忆跨岗位复用候选人；**HR 的合适/不合适/待定反馈实时调整个人排序权重**
6. **面试调度**：生成邀请草稿→确认后发邮件 + 同步日历（MCP 工具）
7. **多租户**：租户 ID 数据隔离 + RBAC

**API 设计**（非常干净的模块划分）：`POST /api/v1/jobs`（JD 解析）、`/candidates/upload`（简历解析）、`/screen`（智能筛选）、`/interview/send`（面试邀请）、`/feedback`（HR 反馈）。

**值得借鉴**：粗筛（检索式）+ 精筛（LLM）两段式、辩论-仲裁的多 Agent 协作模式（比让两个 agent 闲聊更有决策意义）、反馈权重闭环、异步任务队列（Celery 处理解析/发信/摘要）。

### 3. Ancastal/AI-Recruitment-Agent（48★，Python）— AutoGen 多智能体招聘的最简完整实现

**架构**：4 个 AutoGen agent（GPT-4o-mini）：
- `Screening Assistant`（简历 vs JD 关键词匹配 + AI 评估）
- `Interview Assistant`（根据技能缺口生成 5 个针对性面试问题）
- `Data Manager`（提取姓名/邮箱/电话，把筛选结论写入 CSV）
- `User Proxy`（人类代理，`human_input_mode="NEVER"` 全自动）

**核心实现（app.py 已读源码）**：三个任务用 `user_proxy.initiate_chat(...)` **串行编排**——先筛简历（max_turns=10）→ 把 screening 的 `summary` 作为输入传给 Data Manager 存档 → 再把 screening summary 传给 Interview Assistant 生成追问问题。每个 agent 的 system message 是独立 prompt 常量（config/agent_config.py），终止条件统一为消息含 "TERMINATE"，回复轮数上限 3-6 轮防止失控，工具函数（match_keywords/extract_text_from_pdf/save_candidate_data）通过 `register_functions` 注册。

**值得借鉴**：
- **agent 之间靠结构化文本传递上下文**（前一个 chat 的 summary 拼进下一个任务的 prompt）——轻量、可读、易调试
- 轮数上限 + TERMINATE 哨兵 = 防闲聊失控的最简单机制
- 它的"AI 互相聊天"是**流水线接力**而非自由辩论；我们的 Demo 的"AI 互相聊天"（面试官 vs 候选人 bot）可以在这套串行模式上扩展成双 agent 对谈，用 max_turns 和终止词控制长度

### 4. Viy1204/recruiting-copilot（29★，Shell）— 中文 HR 招聘工作流的工程化样板

给 HR/猎头的完整工作流（配合 Claude Code/Codex 等任何 AI 编程助手使用）：**逼问式岗位梳理 → 每日 Boss直聘+猎聘双通道寻源初筛 → 打招呼 → 约面试 → 候选人台账 → 日报**，另有市场人才盘点、本地简历评估、飞书邮箱简历收取。

**设计原则（最值得学）**：
- **本地文件是唯一事实源**：台账（dedup-ledger.csv）、JD、面试档案都是纯文本，换任何 AI 工具数据不丢
- **标准与执行分离**：初筛硬规则全在 `CONTEXT.md`（人写的），工作流文档不写死数字
- **对内对外分离**：寻源策略、排除信号、薪资带宽在 `_internal/` 不外发；对外 JD 干净可发布
- **不可逆动作必经确认**："AI 可以帮你筛一千份简历，但拒绝一个人、联系一个人，默认由你拍板"——打招呼/点不合适/通知候选人都先经 HR 确认
- **越用越准**：每轮从命中的真实简历反向提取搜索词，回填关键词迭代表，下一轮搜索更准
- **安全红线**：邮箱只读收取，不标已读、不移动/删除、不自动下载不可信附件

### 5. FreeAiHR/FreeAiHR（57★，Python/FastAPI + React）— 企业级 AI 招聘全流程产品

完整 HR 产品：简历上传/解析/去重、人才库（聚合简历版本+面试历史+标签+时间线）、岗位管理+人岗匹配、AI 批量生成题集、**候选人远程文本/语音面试自动评分出报告**、KPI/漏斗/评分分布分析、多角色权限（admin/hr/interviewer/hiring_manager/viewer）+ SSO + 审计。

**值得借鉴**：
- **LLM 默认 mock**：无 API key 也能跑通全流程（开发调试友好，我们 Demo 也应内置假模型便于演示）
- **功能位（feature flags）+ 配额驱动**的 License 机制：`resume.upload`/`interview.voice`/`match.evaluate` 等粒度
- OpenAI 兼容接口（OpenAI/通义/vLLM/Ollama 任意切换）——与我们用 DeepSeek 的接入方式一致

---

## 三、主流方案模式总结

| 环节 | 主流做法 | 代表项目 |
|---|---|---|
| 简历获取 | 本地上传 / 邮箱收取 / Boss直聘·猎聘等渠道 / GitHub API 增强 | recruiting-copilot、boss-hr-agent-toolkit、hiring-agent |
| 简历解析 | PyMuPDF/pdfplumber → Markdown → 按 section 逐段 LLM 提取 → JSONResume 结构化 | hiring-agent、HireFlow |
| 初筛 | 关键词硬过滤 + 检索式粗筛（向量/RRF）+ LLM 评分（rubric 权重、结构化输出、evidence） | hiring-agent、HireFlow、ai-resume-screening-system |
| 多智能体 | AutoGen 串行接力 / LangGraph 状态机 / CrewAI 角色分工；辩论-仲裁；轮数上限+TERMINATE 哨兵 | Ancastal、HireFlow、bcefghj/smart-hiring-pipeline |
| 决策输出 | 总分+维度分+证据引用；CSV/数据库台账；反馈闭环调权重 | hiring-agent、HireFlow |
| 面试邀约 | 生成话术草稿 → 人工确认 → 邮件/日历（MCP） | recruiting-copilot、HireFlow |
| 通用工程 | 配置化 prompt 模板、LLM mock、缓存、结构化输出 schema、不可逆动作人工确认 | hiring-agent、FreeAiHR |

---

## 四、对我们 Demo 的启发（可落地清单）

1. **评分模块抄 hiring-agent 的"角色化 rubric"设计**：把评估维度/权重/bonus/分数区间做成 `role.json` 式配置（如：硬性技能 40 / 项目经验 30 / 沟通表达 20 / 文化契合 10），评分 prompt 用 Jinja 模板与代码分离；调用 DeepSeek 时用 JSON schema 强制结构化输出，并要求**每条评分附简历原文证据**——这是"筛选决策"模块最直接可抄的参考。

2. **"AI 互相聊天"用"串行接力 + 轮数上限"而非自由辩论**：参考 Ancastal 的模式——recruiter agent 先对简历提问，把它的提问作为 candidate bot 的输入，candidate 回答后作为下一轮 context 传回，`max_turns`（如 5 轮）+ 终止哨兵控制对话长度，最后把整个对话 summary 喂给 evaluator。这比让两个 agent 无约束互聊稳定得多，也省 token。

3. **增加"硬过滤→LLM 精筛"两段式初筛**：先做规则/关键词硬过滤（学历、年限、必会技能，可配置），只让通过者进入 LLM 评分，避免对大量不合格简历烧 token——参考 ai-resume-screening-system（HR 定义标准分类）和 HireFlow 的粗筛/精筛分层。

4. **为每个候选人维护"证据链"数据模型**：候选人档案 = 解析出的 JSONResume + 各维度得分 + 证据原文引用 + 对话纪要 + HR 反馈标签。参考 hiring-agent 的 CSV 导出和 HireFlow 的 feedback 服务，实现"HR 标记合适/不合适后，后续排序自动加权"的闭环。

5. **不可逆动作加人工确认闸门**：面试邀约、拒绝候选人生成草稿后必须 HR 点击确认才发送（recruiting-copilot 的安全红线）。Demo 里"面试邀约"模块应做成"生成话术 → 预览 → 确认"三步。

6. **内置 LLM mock 模式 + 结果缓存**：无 API key 时用规则+预设话术跑通全流程（FreeAiHR 的做法），评分结果按简历 hash 缓存（hiring-agent 的 DEVELOPMENT_MODE），演示和开发调试体验会好很多。

7. **对话轮数、温度等参数显式控制**：hiring-agent 用 temperature 0.5 控制评分稳定性；评分类调用建议 temperature 偏低（0.3-0.5），聊天类调用可偏高（0.7+）。社区实测同一简历多次评分波动大，条件允许时对关键候选人多评 2-3 次取中位数（ensemble）。

8. **警惕评分攻击与公平性**：PDF 隐形文字可以刷分（hiring-agent 已踩坑），解析前先审计 PDF 文本层；纯 LLM 自动化筛选在现实世界有合规风险（GDPR Art 22），Demo 内保留"人工复核"入口并体现在文案上。

9. **中文场景差异化机会**：中文"招聘智能体"开源项目极少且质量低（多为 0-5★），而中文招聘渠道（Boss直聘等）的自动化需求旺盛（jitou、job-hunter、ai-boss 等求职者侧工具反而更火）。Demo 可主打"中文候选人沟通 + 多智能体对话"差异化定位。

---

## 附：搜索词与结果量（如实记录）

| 关键词 | total_count | 说明 |
|---|---|---|
| "AI recruiting" | 973 | 大量 Kaggle 比赛、demo 级项目混杂 |
| "recruiting agent" | 278 | 多为小项目 |
| "hiring agent" | 361 | 头部是 HackerRank 官方项目 |
| "talent acquisition" AI | 223 | 部分为纯博客/商业工具列表 |
| "recruitment copilot" | 76 | 多为课程作业 |
| "HR agent" | 866 | 大量是 HR 聊天机器人（FAQ 类），与招聘筛选无关的已剔除 |
| "AI recruiter" | 1728 | 同上，混杂度高 |
| "resume screening" AI | 8157 | 数量最大但 90% 是课程项目 |
| "AI interviewer" | 6328 | 大量是求职者练习/作弊工具（interview copilot 类），招聘向的已单列 |
| "AI hiring" | 1233 | 混杂 |
| "interview copilot" | 607 | 基本是求职者侧实时提示工具，与招聘智能体无关，未纳入 |
| "resume matcher" | 3785 | 求职者侧为主 |
| "job application" agent | 1552 | 求职者侧投递自动化 |
| "AI招聘" | 78 | 中文 |
| "智能招聘" | 140 | 中文，多为毕业设计 |
| "招聘智能体" | 7 | 中文，极少 |
| "招聘Agent" | 8 | 中文，极少 |
| "人才筛选" | 4 | 中文，极少 |

已排除：纯教程/纯博客、Kaggle 竞赛代码、求职者作弊类（interview copilot）、无关同名项目（如 AI trading agent、书籍收藏仓库等）。
