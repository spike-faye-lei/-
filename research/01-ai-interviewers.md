# AI 面试官开源项目研究报告

> 调研日期：2026-08-06 ｜ 调研方式：GitHub Search API（8 组中英文关键词 + 8 个 topic 搜索，按 star 排序取前 15，共收集 180 个去重仓库）
> 目的：为招聘智能体 Demo（Python + Gradio + DeepSeek，简历解析 → AI 初筛 → AI 互相聊天 → 筛选决策）提供参考

## 一句话总结

**这类项目的主流方案是：单 Agent 或少 Agent 的「结构化面试循环」——用简历/JD 生成问题清单（或题库检索），AI 面试官逐轮提问、必要时追问，面试结束后用一个独立的评估 prompt 对全过程评分，输出结构化报告（分维度分数 + 结论），工程上的难点集中在追问质量控制、防重复提问和评分稳定性（结构化输出 + 确定性后处理）。**

---

## 一、搜索概况

| 关键词 | 结果数 | 说明 |
|--------|--------|------|
| "AI interviewer" / "ai-interviewer" | 3 万+ | 大量噪音（题库、教程），需人工筛选 |
| "llm interviewer" | 2396 | 混入大量面试题集仓库 |
| "virtual interviewer" | 298 | 有少量真实项目（Phantom-AI-Interview 等） |
| "interview copilot" | 607 | 绝大多数是「帮候选人答题」的作弊助手，与招聘方视角无关 |
| "AI面试官" | 71 | 最精准，多为中文技术面试模拟器 |
| "AI面试" | 357 | 混入题库和 copilot |
| "智能面试" | 155 | 有 1 个高质量项目（AI-Interview，Java） |
| topic:ai-interviewer / interview-copilot / mock-interview 等 | 少量 | 补充发现小众项目 |

结论：**中文关键词「AI面试官」精准度最高**；英文关键词必须人工过滤掉题库/教程类仓库（它们占了 star 大头，如 alirezadir/AIMLInterviews 8693⭐ 实为面试题指南）。

---

## 二、核心相关项目总表（按 star 排序）

### A 类：AI 面试官 / 模拟面试平台（与我们的 Demo 最相关）

| 项目 | Star | 语言 | 功能一句话 |
|------|------|------|-----------|
| [yuanzhongqiao/ai-interview-platform](https://github.com/yuanzhongqiao/ai-interview-platform)（聆悟 Lingwu，aural-oss 中文版） | 913 | TypeScript | 自然语言描述岗位 → AI 自动生成面试题+评分标准，候选人链接进入 AI 主持语音/文字面试，结束自动出分析报告，含防作弊、练习模式、REST API |
| [jiatastic/GPTInterviewer](https://github.com/jiatastic/GPTInterviewer) | 262 | Python | 最经典的开源 AI 面试官：上传简历+JD，AI 生成面试指南并逐轮提问，结束后按固定格式给 Pros/Cons/百分制分数/参考答案；Streamlit 实现 |
| [xgwangdl/AI-Interview](https://github.com/xgwangdl/AI-Interview) | 226 | Java | 「智能面试官」：Spring-Alibaba-AI 全流程技术面试系统，含代码实操评估（AST 解析+LLM 双引擎）、语音交互、人脸识别、自动更新题库 |
| [zixi-liu/interview-ai-prototype](https://github.com/zixi-liu/interview-ai-prototype) | 217 | Python | 行为面试 AI 教练（behavioral questions），提供 FAANG 级反馈，多轮追问 + 综合评分 |
| [1146345502/aural-oss](https://github.com/1146345502/aural-oss)（Aural） | 185 | TypeScript | 开源 AI 面试平台：语音/文字/视频三通道、Live Coding（Monaco）、白板（Excalidraw）、按题打分报告、防作弊（切屏监测/粘贴限制）、练习模式 |
| [iZiTTMarvin/MemCoach](https://github.com/iZiTTMarvin/MemCoach) | 110 | Python | AI 面试教练：简历面试 + GitHub 项目分析 + 持久化画像记忆，动态追问、源码证据驱动出题 |
| [nicobytes/interview-full-stack](https://github.com/nicobytes/interview-full-stack) | 95 | TypeScript | AI Interview Simulator 网页应用，面试准备训练 |
| [MakeFrog/TechTalk](https://github.com/MakeFrog/TechTalk) | 83 | Dart | 跨端（Flutter）AI 面试官应用 |
| [FreeAiHR/FreeAiHR](https://github.com/FreeAiHR/FreeAiHR) | 57 | Python | AI 面试+简历+陪练+考评+带教一体化 HR 工具 |
| [habout632/AI-InterviewMaster](https://github.com/habout632/AI-InterviewMaster) | 43 | JavaScript | AI 面试模拟平台：多岗位覆盖、即时反馈、表现分析 |
| [GodLeaveMe/AuraInterviewer](https://github.com/GodLeaveMe/AuraInterviewer) | 37 | Java | 在线 AI 面试练习平台，多模型接入（GPT/DeepSeek/SiliconFlow）、智能提问与语义评估 |
| [Altergom/AI_Interview](https://github.com/Altergom/AI_Interview) | 36 | Go | Go 实现的 AI 面试系统 |
| [DONTESCAPE/RAG-Agent-InterviewTutor-System](https://github.com/DONTESCAPE/RAG-Agent-InterviewTutor-System) | 26 | Python | 基于 RAG + Agent 的面试辅导：问答、模拟面试、工具调用、面试报告生成 |
| [videosdk-community/ai-agent](https://github.com/videosdk-community/ai-agent) | 25 | Python | 实时语音 AI 面试官 agent，可加入会议，演示 STT→LLM→TTS 全链路 |
| [GoDiao/ai-interview-agent](https://github.com/GoDiao/ai-interview-agent) | 23 | Python | AI 面试 agent |
| [penacristian/interview-agents](https://github.com/penacristian/interview-agents) | 22 | - | 5 个 AI agent 分工：coding / system design / behavioral 模拟面试 |
| [6Asmile/AI_interview](https://github.com/6Asmile/AI_interview)（iFaceOff） | 21 | Python | AI 驱动求职赋能平台 |
| [sahu-adarsh/intervyu](https://github.com/sahu-adarsh/intervyu) | 20 | TypeScript | 真实语音 AI 面试练习，编程题实时评估 |
| [manthan89-py/AI-Interview-System](https://github.com/manthan89-py/AI-Interview-System) | 19 | Python | 自动化面试平台：语音问答应答、实时转写 |
| [ngoanpv/DeepInterview](https://github.com/ngoanpv/DeepInterview) | 19 | Python | **评分体系最严谨的 voice-first AI 面试官**：上传 CV+JD → 多 agent 准备 → 语音面试 → rubric 按题评分 → 对抗性复审 → 辅导建议闭环；LangGraph+LiveKit，Apache-2.0 |
| [theeaashish/interview-ai](https://github.com/theeaashish/interview-ai) | 16 | TypeScript | 模拟面试 + 回答分析 + 打分 + 个性化反馈 |
| [M-Mowina/TalentTalk](https://github.com/M-Mowina/TalentTalk) | 16 | Jupyter | 简历动态分析 + 语音交互的技术面试系统 |
| [YaphetHayate/AiInterview](https://github.com/YaphetHayate/AiInterview) | 11 | Python | **双 Agent 架构**（Manager 编排 + Interviewer 执行），四阶段面试流程，支持 DeepSeek/GLM/千问，回答完整性判断 + 上下文隔离 |
| [heatnan/offerMaster](https://github.com/heatnan/offerMaster) | 9 | Python | LangGraph + DeepSeek + Whisper 多轮语音模拟面试 |
| [1935417243/GrillMind](https://github.com/1935417243/GrillMind) | 8 | JavaScript | 智面：上传简历选岗位，AI 面试官上线，文字+语音，结束自动生成评估报告 |
| [Muyu1uz/ai-java-interviewer](https://github.com/Muyu1uz/ai-java-interviewer) | 6 | Java | SpringAI Alibaba 实现的 AI 面试智能体 |
| [RezaSi/go-interview-practice](https://github.com/RezaSi/go-interview-practice) | 2432 | Go | 编程面试平台（30+ 题，即时反馈），含 AI 面试官模块，可作参考 |

### B 类：面试 Copilot / 助手（帮候选人答题，方向相反，仅列代表）

| 项目 | Star | 说明 |
|------|------|------|
| [Natively-AI-assistant/natively-cluely-ai-assistant](https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant) | 2138 | 会议/面试实时助手，转录+提示 |
| [JWM0203/MeetingCopilot](https://github.com/JWM0203/MeetingCopilot) | 152 | Windows 隐形面试 copilot，本地 ASR |
| [interview-copilot/Interview-Copilot](https://github.com/interview-copilot/Interview-Copilot) | 143 | GPT 辅助答题、写代码 |
| [SMACY2017/InterPilot](https://github.com/SMACY2017/InterPilot) | 133 | 从系统音频抓取面试官问题并生成答案 |
| [yechafengyun/interview_ai_win11](https://github.com/yechafengyun/interview_ai_win11) | 70 | Windows 11 免费面试助手 |

### 已排除的类别（搜索中出现但无关）
- 面试题库/八股文（alirezadir/AIMLInterviews 8693⭐、315386775/DeepLearing-Interview-Awesome-2024 2874⭐、jackaduma/awesome_LLMs_interview_notes 1318⭐ 等）——纯资料无代码
- 大杂烩仓库（JavaGuide、funNLP、IT_Book_pro 等）——关键词恰好命中，与 AI 面试无关

---

## 三、重点项目深入分析

### 1. jiatastic/GPTInterviewer（262⭐，Python/Streamlit）—— 经典单 Agent 面试循环

**核心架构**（读源码 `prompts/prompts.py`、`pages/Professional Screen.py`）：

```
JD/简历文本 → NLTK 分句 → OpenAIEmbeddings → FAISS 向量库
         → RetrievalQA 生成「面试指南」guideline（每个 topic 只生成 1 个问题）
         → 循环：ConversationChain 提问 → 候选人回答 → 继续
         → 点击结束 → feedback prompt 输出评价
```

**关键设计点：**

1. **问题生成与提问分离成两个 Prompt**：
   - 生成阶段（`da_template`/`swe_template`/`jd_template`）：基于简历/JD 生成面试指南，强调"题目要结合简历上下文、分 3 大主题（背景技能/工作经验/项目）"。
   - 提问阶段（ConversationChain prompt）：`strictly following the guideline`、`only one question at a time`、`Do not ask the same question`、`Do not repeat the question`、`Do ask follow-up questions if necessary`——**用 prompt 硬约束"每次只问一个、不许重复"**。
2. **防重复提问双保险**：prompt 约束 + FAISS 相似度检索（guideline 与候选回答都向量化，检索相关上下文注入）。其思路是：把对话历史作为检索源，避免 LLM 重复问已问过的问题。
3. **评分 prompt**（`feedback_template`，结构化输出但不是 JSON）：
   ```
   Summarization: 用一段话总结对话
   Pros: 正面反馈
   Cons: 可改进之处
   Score: 百分制评分
   Sample Answers: 每个问题的参考答案
   ```
   并强调 "the candidate has no idea what the interview guideline is"（防止 LLM 按指南暗示答案）。
4. 每轮把完整对话历史（`ConversationBufferMemory`）+ 当前输入拼进模板，自回归式生成下一个问题。
5. 语音支持：Whisper STT + AWS Polly TTS（可选）。

**可借鉴**：评分 prompt 的四段式结构（总结/优点/缺点/分数/参考答案）简单有效；"不许重复提问"这类 prompt 约束是必须写的。

---

### 2. YaphetHayate/AiInterview（11⭐，Python，LangChain+LangGraph）—— 双 Agent 架构，与我们的 Demo 最同源

**核心架构**（读源码 `agents/manager_agent.py`、`agents/interviewer_agent.py`、`skills/interviewManager/SKILL.md`）：

```
Manager Agent（流程编排，React Agent 带工具）
  ├─ 判断候选人回答是否完整
  ├─ 为 Interviewer 组装"干净"的 prompt（上下文隔离）
  └─ 工具：read_skill_md / read_stage_file / fetch_questions_from_bank(从题库取题)
Interviewer Agent（面试执行）
  └─ 只负责对话：每次问一个问题，按 Manager 给的 system_prompt + user_message 执行
```

**四阶段流程**：基础知识考察（从题库注入真实题目）→ 项目经历考察 → 岗位需求考察 → 面试总结。

**关键设计点（干货密度最高）：**

1. **Manager 输出两类 JSON 动作**：
   - 回答不完整 → `{"action": "await_continuation", "message_to_user": "请继续补充。"}`
   - 回答完整 → `{"action": "interview", "interviewer_prompt": {system_prompt, user_message, context_thread, instructions}}`
2. **回答完整性判断策略**（四维度）：
   - 语言特征："第一…""一方面…"没下文、结尾省略号 = 不完整；"以上是我的理解""完毕" = 完整
   - 内容深度：只列概念名没展开 = 不完整；有定义+原理+示例 = 完整
   - 上下文一致性：之前详细突然变短 = 不完整
   - 明确信号："回答完毕" = 完整
3. **追问话术按面试风格自适应**（professional/friendly/challenging/scenario/growth 五种风格 × 完整/不完整两种状态，SKILL.md 里有话术表，如 challenging 风格：完整也追问"还有吗？"）；**难度影响容忍度**（basic 宽容、hard 严格）。
4. **上下文隔离**：simulation 模式 Interviewer 只看到当前问题的对话线程，跨问题历史不传（防止模型被前面回答带偏）；Manager 持有全局摘要，每阶段结束生成阶段摘要（"阶段N：候选人表现[优秀/良好/一般/较差]…"）。
5. **回答整合**：候选人多条消息分散回答时，Manager 允许合并/按子问题对齐，但**明确禁止润色措辞、补充内容**（防幻觉篡改）。
6. **阶段 4 总结报告**（`references/stages/stage4_summary.md`）：三维度加权——基础知识 30% + 项目经验 40% + 岗位匹配 30%；5 级结论（9-10 强烈推荐 / 7-8 推荐 / 5-6 待定 / 3-4 不推荐 / 0-2 强烈不推荐）；报告模板含各阶段得分/表现/亮点/不足 + 录用建议 + 理由 + 发展建议。
7. LLM 工厂（`agents/modelFactory.py`）支持智谱 GLM / **DeepSeek** / 通义千问，一个环境变量切换。

**可借鉴**：回答完整性判断 + 追问控制是"AI 面试官不像人"的核心痛点，这套策略矩阵可直接落地到我们的 Demo（当前我们每轮固定推进，缺少"回答含糊必须追问"的机制）。

---

### 3. ngoanpv/DeepInterview（19⭐，Python + Next.js，LangGraph + LiveKit）—— 评分体系最严谨的 voice-first 面试官

**核心架构**（读源码 `apps/agent/src/deepinterview_agent/post/`）：

```
PREP（5 个 agent，面试前跑）：读 CV + 读 JD + 调研公司 + 差距分析 + Question Planner
  → 生成问题计划（含每题的 rubric 评分标准、难度曲线、目标能力维度 target_competency）
LIVE（3 个 agent + Director）：Interviewer / Coding / Behavioral(STAR)，STT→LLM→TTS 级联
POST（4 个 agent）：Scorer / Language Coach / Report / Skill Distiller
  → 按题评分 → 语言教练 → 报告 → 提炼技能画像
共享 InterviewContext "黑板"贯穿三阶段；跨语言 TS↔Pydantic 契约
```

**评分实现（`post/evaluator.py` + `post/prompts.py`）—— 这是全仓库最有价值的部分：**

1. **按题评分、rubric 驱动**：每个问题预先定义 rubric（`criterion + weight + description`），评分 prompt 要求按权重加权打分，0-5 分制（0=无关内容，3=扎实，5=出色），并要求在 `evidence` 字段引用回答中的具体证据。
2. **两个字段"钉死"不让模型决定**（这是最大的亮点）：
   - `competency` 强制等于问题的 `target_competency`（模型不能自创维度，评分卡才能映射回问题计划）
   - `level`（strong/solid/developing/weak）由分数确定性派生（>=4/>=3/>=2），分数与等级永远一致
3. **对抗性复审（adversarial score verification）**：低分/边缘分用第二个"怀疑型评审" prompt 复核，且**基于候选人的原始 transcript 而非第一轮评审自己写的 evidence**（避免"拿被审计的模型写的证据来审计模型"的循环论证）。
4. **未回答的问题跳过而非给 0 分**：没考察到的能力维度不算弱项，覆盖率单独用 `coverage_pct` 报告——避免"没问到的维度拉低总分"。
5. **失败隔离 + 并发**：单题评分失败只丢那一题（asyncio.Semaphore(4) 限并发），不会整个 stage 失败。
6. **数值字段确定性组装，文本字段 LLM 生成**：overall_score 由分数计算，strengths/weaknesses/next_steps/summary 才交给 LLM——报告数字永远自洽。
7. 附加模块：语言教练（fluency/clarity/填充词计数）、参考答案生成（STAR 结构 <180 词）、社区题库包（Markdown+YAML，版本化，可 lint）。

**可借鉴**：评分"确定性后处理 + 结构化输出 + 证据引用 + 二次复核"的完整链路，直接对标我们 evaluator.py 里"JSON 解析失败就 fallback"的脆弱处理。

---

### 4. aural-oss / ai-interview-platform（聆悟，913⭐+185⭐，TypeScript）—— 产品化最完整的开源平台

两个仓库是同一产品（聆悟是 aural-oss 的中文 fork/品牌版）。**产品流程**：自然语言描述岗位 → AI 生成完整面试（题目+评分标准+设置）→ 分享链接 → 候选人语音/文字参加 → 自动出分析报告。

**可借鉴的产品点：**
- **AI 出题 + 人工编辑并存**：生成后可手动编辑题目类型（开放式/单选/多选/Live Coding/白板）
- **防作弊体系**：切屏监测、粘贴限制、多屏检测、完整性日志（完整性日志很便宜，Gradio 也能做）
- **练习模式与正式面试分离**：候选人可先练，练习记录与正式成绩分开统计
- **面试官人格可配置**：AI personality、语气、追问深度、语言都可调
- **报告导出**：按题打分 + 亮点 + 改进建议，支持导出复盘
- **批量导入**：Excel 批量导入候选人、PDF 简历批量解析

---

## 四、对我们 Demo 的启发（可落地清单）

1. **补齐"回答完整性判断 + 追问控制"机制**：我们现在的 `next_message` 每轮固定推进，候选人答得含糊也照常进入下一问。可参照 AiInterview：在 interviewer.py 的 SYSTEM 里加判断指令（"回答含糊/只列要点时必须追问，最多追问 N 次后再进入下一阶段"），把 `CHAT_ROUNDS` 结构升级为"每阶段 N 轮 + 追问上限"。

2. **评分从"一次大 JSON"改为"按题评分 + 确定性后处理"**：当前 evaluator 把整个对话一次性喂给 LLM 求 JSON（有解析失败 fallback）。参照 DeepInterview：(a) 每题单独评分（0-5 + evidence 引用原话）；(b) 维度名在代码里钉死，不由模型自创；(c) 总分/等级由分数计算而非模型输出；(d) 未涉及维度不计入总分，单独显示覆盖率。这能把"决策报告数字自相矛盾"的 bug 消灭在结构上。

3. **评分 prompt 加"证据引用"要求**：evaluator 的 EVALUATOR_SYSTEM 里增加"每条分数必须引用对话中的原话作为 evidence"，并让 LLM 输出 `{"scores": {...}, "evidence": {...}, ...}` 结构——防止模型凭空打分，报告里也能展示"凭什么打这个分"。

4. **"【结论】"标记收口的做法是对的，可升级为结构化**：我们已用"【结论】"判断结束，可以再加一道程序化校验（如轮数硬上限后强制触发 CLOSING_PROMPT，无论模型是否给结论），并对"通过/不通过"做字符串级校验，不通过就重试一次，避免出现"没给结论的报告"。

5. **多 Agent 拆分不必上 LangGraph，但可以按"角色隔离上下文"**：AiInterview 的 Manager/Interviewer 隔离思路可以用最小成本复刻——初聊阶段和技术面试阶段用不同的 system prompt + 不同的历史窗口（技术面试阶段只带最近 N 轮对话），减少长历史干扰（我们 CLOSING_PROMPT 已经在用 `history[-6:]`，可以推广到全流程）。

6. **防重复提问**：在 interviewer prompt 里加"Do not ask the same question / Do not repeat the question"（GPTInterviewer 验证有效），纯文本方案可再叠加一道廉价检查：新问题与历史问题做字符/向量相似度，超阈值就重新生成。

7. **报告模板参照 AiInterview 的 stage4 格式升级**：当前报告是 4 个评分维度平铺，可升级为"分阶段小结（初聊表现/技术表现）+ 加权总分（如基础 30% / 项目 40% / 匹配 30%）+ 五级结论 + 发展建议"，并让邀请话术（invite 字段）继续保留——这是全流程最后落点，我们的"面试邀约"环节是多数开源项目没有的招聘方视角优势。

8. **面试风格/难度可配置化**：AiInterview 的 5 种风格 × 难度容忍度矩阵、aural 的可调人格，都是低成本高感知的功能。在 Gradio 界面加一个"面试风格"下拉（专业/友好/挑战/场景化），在 SYSTEM prompt 里按风格注入追问话术即可，能显著提升 Demo 演示效果。

9. **防作弊可做最小版**：参照 aural-oss，Gradio 前端监听 blur（失焦）事件记录"切屏次数 + 时间戳"，结束后写入报告的风险提示——纯前端十几行代码，但让 Demo 看起来专业。

10. **题库注入（可选增强）**：AiInterview 从 PostgreSQL 题库取题注入第一阶段的思路，对应我们可以内置一个 20-30 题的 JSON 题库（按技能标签索引），初筛阶段先问题库题、追问再走自由生成——既省钱又稳。

---

## 五、研究备注

- 数据来源：GitHub Search API，star 数为 2026-08-06 查询时的 approx 值。
- 深入阅读了 6 个仓库的 README + 关键源码（GPTInterviewer 的 prompts、AiInterview 的 SKILL.md/双 agent 源码/stage4 报告模板、DeepInterview 的 evaluator/prompts、aural-oss README、AI-Interview README）。
- 原始搜索结果缓存于 `research/_search_results.json`（180 个仓库完整数据），临时源码摘录在 `research/_repos/`。
- 局限：GitHub API 未认证限速 10 次/分钟，部分关键词结果数庞大，表格中已人工过滤题库/教程/噪音仓库；star 数偏低的仓库（<10）未列入主表，但 JSON 缓存中有完整列表。
