# AI 多智能体对话 / 角色扮演 / Agent 面试模拟 研究报告

> 调研时间：2026-08-06，数据来自 GitHub Search API 与 GitHub 网页搜索实时结果（star 数为当时 approx 值）
> 调研目的：为招聘智能体 Demo（Python + Gradio + DeepSeek API，核心亮点"AI 招聘官和 AI 候选人互相自动聊天"）提供多智能体对话循环、角色约束、终止条件的设计参考
> 调研方式：9 组关键词（中英文）+ 4 大框架专项检索 + 3 个重点项目的 README/源码精读

## 一句话总结

**AI 多智能体对话的主流实现是「角色化 system prompt 双注入 + 共享对话历史 + 交替 turn-taking 循环 + 显式终止条件（题目列表耗尽 / 最大轮数 / 特殊结束标记）」，具体形态分三派：① 双 Agent 角色扮演循环（CAMEL 的 inception prompting 是鼻祖，`RolePlaying.step()` 让两个 agent 交替发言，各自维护独立记忆）；② 图状态机编排（LangGraph 把"出题→逐题问答→评估→报告"建模成有向图，循环节点由题目列表驱动）；③ 框架群聊/流水线（AutoGen GroupChat 广播式轮流发言、CrewAI sequential 流水线）。需要注意：市面上大量自称"multi-agent interview"的项目实际是「AI 提问 + 人类回答」的单边模式，真正 AI 互相对话的成熟开源项目以 CAMEL 和各类小型 demo 为主。**

---

## 一、项目总览表

### 1. 双 Agent 对话核心（与我们的 Demo 最相关）

| 仓库 | star | 语言 | 功能一句话 |
|---|---|---|---|
| [CAMEL-AI/CAMEL](https://github.com/CAMEL-AI/CAMEL) | 17.6k | Python | 双 Agent 角色扮演对话框架鼻祖：inception prompting 让 AI assistant 与 AI user 自主协作完成任务 |
| [Neph0s/awesome-llm-role-playing-with-persona](https://github.com/Neph0s/awesome-llm-role-playing-with-persona) | 1058 | - | LLM 角色扮演（persona）资源大全：论文、数据集、框架索引 |
| [choosewhatulike/trainable-agents](https://github.com/choosewhatulike/trainable-agents) | 642 | Python | Character-LLM 论文代码：把历史人物"训练"成可对话 agent（角色记忆 vs 事实一致性） |
| [InteractiveNLP-Team/RoleLLM-public](https://github.com/InteractiveNLP-Team/RoleLLM-public) | 528 | Python | RoleLLM：角色扮演能力评测 + 角色数据构建 + 微调增强 |
| [weiyifan1023/Neeko](https://github.com/weiyifan1023/Neeko) | 140 | Python | EMNLP 2024：动态 LoRA 实现单模型多角色扮演 |
| [howyoungchen/deepRolePlay](https://github.com/howyoungchen/deepRolePlay) | 118 | Python | 多 Agent 角色扮演系统：用 agent 协作机制解决 LLM 角色遗忘问题 |
| [Neph0s/InCharacter](https://github.com/Neph0s/InCharacter) | 100 | Python | 用"心理学访谈法"（问卷式提问）评估角色扮演 agent 的人格一致性 |
| [JohnnyRafael/chatting-agent](https://github.com/JohnnyRafael/chatting-agent) | 58 | Python | 两个本地 Ollama 模型互相聊天的最简实现（Streamlit，含角色重标注技巧） |
| [ruggsea/LLM-ABM-Chat](https://github.com/ruggsea/LLM-ABM-Chat) | 14 | Jupyter | 多智能体 LLM 对话模拟基础框架（agent-based model） |
| [Prajwal-Nagaraj/Chatbot-Simulation-Workflow](https://github.com/Prajwal-Nagaraj/Chatbot-Simulation-Workflow) | 6 | Python | 用"用户模拟 agent"自动测试聊天机器人：模拟多样人格用户对话 |
| [rantezPeperino/crewai_chat_web_two_agents](https://github.com/rantezPeperino/crewai_chat_web_two_agents) | 3 | HTML | 两个 CrewAI agent（搜索+总结）网页互聊的最小 demo |
| [Latha-Maguluri/AI_Interview_Autogen](https://github.com/Latha-Maguluri/AI_Interview_Autogen) | 1 | Python | AutoGen 纯 AI-AI 面试：面试官、候选人、职业教练三方终端对话（少见的"AI 面试 AI"实现） |

### 2. 多智能体对话框架 / 模拟环境

| 仓库 | star | 语言 | 功能一句话 |
|---|---|---|---|
| [geekan/MetaGPT](https://github.com/geekan/MetaGPT) | 69.7k | Python | 多智能体框架：`Code = SOP(Team)`，角色（PM/架构/工程师）按 SOP 流水线协作；无面试模块 |
| [microsoft/autogen](https://github.com/microsoft/autogen) | 60.3k | Python | 微软多智能体框架：AgentChat API 支持 two-agent chat 与 GroupChat；已进入维护模式，新项目官方建议用 Microsoft Agent Framework (MAF) |
| [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | 56.7k | Python | 角色扮演 agent 编排框架：role/goal/backstory 定义人设，sequential/hierarchical 流程 |
| [OpenBMB/AgentVerse](https://github.com/OpenBMB/AgentVerse) | 5.1k | Python | ICLR 2024：task-solving + simulation 双框架，环境驱动对话（NLP 教室 9 agent 轮流发言） |
| [google-deepmind/concordia](https://github.com/google-deepmind/concordia) | 1.6k | Python | 生成式社会模拟：Game Master 模拟环境，玩家用自然语言行动（TRPG 模式） |
| [chatarena/chatarena](https://github.com/chatarena/chatarena) | 1.6k | Python | 多智能体"语言游戏"环境（MDP 抽象：Arena 主循环 + Environment 状态）；2025-08 已弃用 |

### 3. 面试 / 招聘场景应用（AI-AI 或 AI-人）

| 仓库 | star | 语言 | 功能一句话 |
|---|---|---|---|
| [Tameyer41/liftoff](https://github.com/Tameyer41/liftoff) | 1521 | TypeScript | Mock Interview 模拟器：AI 语音面试官 + 实时反馈 |
| [adrianhajdin/ai_mock_interviews](https://github.com/adrianhajdin/ai_mock_interviews) | 566 | TypeScript | Next.js + Vapi AI 实时语音 mock interview 教程项目 |
| [tejpshah/interview-pilot-ai](https://github.com/tejpshah/interview-pilot-ai) | 124 | Python | Agent 角色扮演个性化面试官：针对你的背景模拟面试官语气追问 |
| [IliaLarchenko/Interviewer](https://github.com/IliaLarchenko/Interviewer) | 119 | Python | AI Mock Interviewer（终端式） |
| [lishuangqiang/AI-Meeting](https://github.com/lishuangqiang/AI-Meeting) | 862 | Java | Spring AI 会议系统，含 mock interview、语音转写、TTS |
| [zzzlip/langgraph-AI-interview-agent](https://github.com/zzzlip/langgraph-AI-interview-agent) | 58 | Java | LangGraph + LlamaIndex 招聘面试辅助系统 |
| [1624899/ai_interview](https://github.com/1624899/ai_interview) | 57 | TypeScript | "面面"AI 求职助手：LangGraph 状态机全真模拟面试 + 多智能体简历诊断（DeepSeek 可用） |
| [Ancastal/AI-Recruitment-Agent](https://github.com/Ancastal/AI-Recruitment-Agent) | 48 | Python | AutoGen 招聘多智能体：Screening/Interview/Data 三 agent 协作（已收录于 02 号报告） |
| [BMN-zyb/AI_InterviewerAgent](https://github.com/BMN-zyb/AI_InterviewerAgent) | 28 | Python | LangGraph 8-agent 面试系统：意图路由/DAG 编排/双引擎记忆/动态难度 |
| [ngoanpv/DeepInterview](https://github.com/ngoanpv/DeepInterview) | 19 | Python | 语音优先 AI mock 面试官：LiveKit 实时语音，自适应多语言 |
| [pigna90/ai-mock-interviewer](https://github.com/pigna90/ai-mock-interviewer) | 16 | Python | CrewAI 模拟面试：公司调研/出题/评估/追问四个 agent 流水线（人答 AI 评） |
| [roselle-luo/AiInterviewHelper](https://github.com/roselle-luo/AiInterviewHelper) | 10 | Kotlin | AI 多模态模拟面试评估 agent |
| [VIKAS9793/ai-interviewer-google-adk](https://github.com/VIKAS9793/ai-interviewer-google-adk) | 8 | Python | Google ADK 多智能体技术面试官：自适应出题 + 代码分析 |
| [KardelRuveyda/autogen-ai-interviewer](https://github.com/KardelRuveyda/autogen-ai-interviewer) | 7 | Python | AutoGen 土耳其语软件工程师面试模拟 |
| [ankitmalik84/AI_INTERVIEWER](https://github.com/ankitmalik84/AI_INTERVIEWER) | 3 | Python | AutoGen 多角色 AI 面试模拟（interviewer/candidate 等角色） |

### 4. 搜索过程说明（如实记录）

- `multi-agent interview`：801 条，相关度中等，大部分是"AI 面试官 + 人类候选人"，**纯 AI-AI 对话的很少**
- `AI mock interview` / `mock interview`：1.05w / 1.6w 条，但大量是题库类项目（full-stack-interview-questions 等），与多智能体无关
- `agent role play` / `llm role play`：288 / 221 条，学术向为主（Character-LLM、RoleLLM、Neeko、InCharacter），有成熟的人设一致性评估方法论
- `two agent chat`：187 条，多为小型 demo，chatting-agent 最有参考价值
- `agent conversation simulation`：72 条，相关项目少且小（LLM-ABM-Chat 等）
- 中文关键词：`多智能体面试`（121 条，少量相关：AiInterviewHelper、offer-digitalelf 等）、`AI模拟面试`（相关但多为大杂烩平台）、`角色扮演Agent`（46 条，多为主播/小说/游戏向）、`智能体对话`（801 条，几乎全不相关，被"智能体+对话"的通用词污染）
- 框架专项：`autogen interview`（44 条，均小项目，无官方面试示例）、`crewai recruit`（51 条，均小项目，CrewAI 官方无 recruit 示例）、`langgraph interview`（500 条，AgentGuide 7.9k 是教程向）、MetaGPT 官方仓库**确认无面试/招聘模块**

---

## 二、重点项目详细分析

### 1. CAMEL — 双 Agent 对话循环的教科书实现（17.6k★）

**为什么值得看**：`camel/societies/role_playing.py` 是"两个 AI 互相聊天"最经典、最被引用的实现（原始论文即提出 AI Society 双 agent 对话），我们 Demo 的双 agent 结构可以直接对标它。

**核心机制：Inception Prompting（三段式启动）**
1. **TaskSpecifyAgent 细化任务**：用户给一个粗糙任务（如"开发一个 Python 程序"），先用一个 agent 把它细化为具体任务描述（`_init_specified_task_prompt`）。对面试场景：把"面试候选人"细化为"针对 JD 出 5 道考察点问题，逐题追问"。
2. **SystemMessageGenerator 双注入**：`_get_sys_message_info` 为两个角色各自生成 system message，**任务描述同时注入双方 system prompt**——即"AI 候选人"也明确知道面试目标（这保证对话收敛，但对我们 Demo 有信息泄漏问题，见启发部分）。
3. **可选 TaskPlannerAgent**：把任务拆成步骤追加到 prompt，让对话分阶段推进。

**对话循环（`step()` 方法，核心代码逻辑）**：
```
assistant_msg(初始任务) → user_agent.step() 生成 user 回复
                       → assistant_agent.step() 生成 assistant 回复
                       → 返回 (assistant_response, user_response)，各带 terminated 标志
```
- 每次调用 `step()` 双方各说一轮，外部循环调用直到任一 agent 返回 `terminated=True`
- **终止条件由 ChatAgent 内部控制**：消息命中终止关键词（如 "exit" / "terminate"）或达到 max 轮数上限
- **记忆管理**：每个 ChatAgent 自带 memory，`step()` 中消息自动存入各自历史；多响应（n>1）时由调用方显式 `record_message` 记录（防止记忆缺漏，源码注释专门提到）
- **可选 Critic-in-the-loop**：`with_critic_in_the_loop=True` 时第三个 CriticAgent 评估每轮产出质量，不满足标准则让 assistant 重答——这是"对话质量闸门"的经典做法

**值得借鉴**：
- 双 agent 各自独立 system prompt + 独立 memory，而不是共享一份对话状态
- 任务指定（task specify）让对话有明确目标，避免两个 AI 聊跑题
- terminated 标志从 agent 内部返回，循环层只负责轮转——分层清晰

### 2. 1624899/ai_interview — LangGraph 面试状态机（57★，中文项目）

**为什么值得看**：功能最全、最贴近"AI 招聘官"的面试应用；FastAPI + Next.js + LangGraph，支持 DeepSeek API 配置（Demo 技术栈可对照）。

**面试对话流（LangGraph 状态机节点编排）**：
```
规划(简历+JD 生成个性化题目列表) → 模拟(逐题问答，过程中无即时反馈) → 可选提示(卡壳时 hint)
→ 逐题推进(AI 面试官自然引导对话) → 报告(五维评分+强弱点+录用建议)
```
- **终止条件**：题目列表耗尽 → 自动进入报告生成节点（评分维度：技术/沟通/问题解决/学习/团队协作，雷达图 + 技能标签 + 能力档案跨会话累积）
- **多轮面试机制**：一面/二面/三面轮次推理，简历与 JD 自动继承，**题目去重机制**防止跨轮重复提问；每题 3~10 题可配置
- **多智能体协作（简历诊断，圆桌会议模式）**：匹配分析师（JD 匹配率）+ 内容优化师（改写建议）+ HR 审核官（招聘方视角）三专家并行给建议，之后一个 **Quality Assurance (Reflector) 节点**对专家建议做二次审核与反思精炼——"先输出后反思"的两段式很有借鉴价值
- **工程细节**：全链路 SSE 流式输出；前端可配置 LLM（OpenAI/Azure/**DeepSeek**/Qwen）；文本面试可克隆为语音面试并保留完整历史
- **注意**：非商用 license；README 声称"用户配置 API key"，面试过程仍是"AI 面试官 + 人类候选人"模式（AI-AI 只用于简历诊断圆桌）

**值得借鉴**：
- 把"题目列表"当作状态机的终止判据——**模型不需要自己判断何时结束，列表耗尽即结束**，天然防死循环
- 报告节点独立于对话节点：评分 agent 只看完整记录，不实时干预对话
- 题目去重 + 轮次继承，适合我们做多轮面试 Demo

### 3. BMN-zyb/AI_InterviewerAgent — 8-Agent DAG + 双引擎记忆 + 动态难度（28★）

**为什么值得看**：工程级的多 agent 面试系统，架构最完整：8 个 agent、DAG 编排、RAG、MCP 全都有，且是"多 agent 各司其职"而非"单模型换 prompt"的范例。

**8 个 agent 分工（LangGraph StateGraph，共享 state 传参）**：

| Agent | 职责 |
|---|---|
| IntentRouter | 意图识别与路由分发（聊天/面试/技能请求） |
| JDAnalyzer | 解析 JD，提取技术栈与职级要求 |
| ResumeAnalyzer | 简历匹配，找优势与短板 |
| QuestionPlanner | 按 JD+简历规划题目分布 |
| Interviewer | 多轮面试 + 动态追问 |
| Evaluator | 逐题打分，生成评估报告 |
| StudyPlanner | 生成个性化复习计划 |
| ChatAgent | 闲聊与引导对话 |

**对话循环**：`ask` 节点循环执行直到 QuestionPlanner 的题目集耗尽，然后转报告节点 → 复习计划 → 记忆落库。面试中 Interviewer 会根据回答生成 follow-up 追问（不是死板读题）。

**动态难度状态机**（很妙的设计）：
```
[简单] —(连续 N 题答对)→ [中等] —(连续 N 题答对)→ [困难]
   ←(连续 N 题答错)—      ←(连续 N 题答错)—
```
连续答对/答错触发升降档，模拟真实面试官的追问策略。

**双引擎记忆**：
- Redis 短时记忆：滑动窗口会话上下文，O(1) 读写，实时管理
- MySQL 长时记忆：用户画像、弱点标签、历史面试记录；下次面试自动加载，**优先考上次的弱项**（个性化闭环）

**值得借鉴**：
- "规划者（QuestionPlanner）与执行者（Interviewer）分离"：出题不依赖对话过程，执行者只负责表达
- 难度状态机：对 AI-AI 对话同样适用（候选人答得越好，追问越深）
- 弱点标签跨会话积累——Demo 如果做多轮面试可以直接抄这个思路

### 4. 附加短评：JohnnyRafael/chatting-agent（58★）——最简双 Agent 轮替实现

197 行 Streamlit 代码，两个 Ollama 模型互聊。**关键技巧（角色重标注）**：
```python
for i, msg in enumerate(messages):
    role = "user" if i == len(messages) - 1 else "assistant"
    model_messages.append({"role": role, "content": msg["content"]})
```
传给每个模型的对话历史中，**最新一条标为 `user`（即"当前该我回的话"），历史全部标为 `assistant`**——让模型始终以"回应对方"的姿态生成，避免模型在长历史中混淆自己的身份。轮替逻辑就是消息数奇偶判断 `len(messages) % 2`。终止条件：时间上限、手动停止、空响应即停。这对我们用 Gradio 做双 agent 聊天有直接参考价值。

---

## 三、对我们 Demo 的启发（落地清单）

1. **双 agent 轮替用"角色重标注"喂上下文**：按 chatting-agent 的技巧，给招聘官模型的历史中最新一条标 user、其余标 assistant，给候选人模型同样处理；配合独立 system prompt（招聘官含 JD + 评分标准，候选人含简历内容），两个模型各拿各的"视角"，对话才真实。DeepSeek 对 role 字段敏感，这个技巧能显著减少角色错乱。

2. **终止条件优先用"题目列表耗尽 + 最大轮数双保险"**：仿 ai_interview/BMN，开局由出题 agent 生成 N 道题（如 5 题），对话循环逐题消耗，列表耗尽即结束；同时在循环层硬性设置 max_rounds（如 20 轮）和单轮字数上限，防止模型自己"觉得聊完了还不结束"或陷入复读循环。不要在 prompt 里指望模型自觉终止。

3. **候选人信息隔离（和 CAMEL 反着来）**：CAMEL 把任务同时注入双方 system prompt，但那会泄漏 JD 给候选人。我们的设计应该是：招聘官知道 JD + 简历，候选人只知道简历 + 模糊岗位描述——候选人"不知道标准答案"才能产生真实回答，招聘官才有得评估。这也是 Demo 的戏剧性来源。

4. **评估 agent 只读记录、不实时干预**：对话结束后由独立的 evaluator agent（可复用现有 evaluator.py）读完整对话记录打分（仿 BMN 的 Evaluator 节点 / ai_interview 的报告节点）。评估 prompt 里要求"引用候选人原话作为证据"，避免评分 agent 凭空发挥。

5. **开局加"任务指定"一步（CAMEL inception prompting）**：正式对话前先用一次 LLM 调用把面试目标具体化——把"面试候选人"细化为"以 5 年经验技术主管口吻，重点考察项目深度与系统设计，逐题追问"——把这段指定文本注入招聘官 system prompt。低成本提升对话收敛度，防两个 AI 聊到星座运势。

6. **Gradio 流式渲染 + 空响应防护**：用 generator/yield 逐 chunk 输出当前说话 agent 的回复（仿 SSE 流式）；任一 agent 返回空内容或连续 3 轮无新信息时强制终止并提示，避免死循环卡死 UI。

7. **人设一致性检查（进阶）**：参考 InCharacter 的"心理访谈"思路，在评估阶段抽查候选人回答与简历的一致性（如"你简历写精通 K8s，但被问到 Pod 调度时答不上来"），作为评估维度之一写进报告。这是简历造假检测的弱化版，也是"AI 面试 AI"比人机面试更有趣的点。

8. **动态难度（进阶，可后置）**：按 BMN 的连续答对/答错状态机调节追问深度（如答对 2 题后追问 STAR 细节、技术深挖），让 Demo 看起来"面试官有策略"，代码量很小（一个计数器 + 一档 prompt）。

---

## 附：调研局限

- GitHub 匿名 API 限流（60 次/小时），部分搜索用网页搜索补足，star 数取搜索时刻 approx 值
- "两个 AI 自动对话"在开源世界里成熟产品极少，多数停留在论文实现（CAMEL/Character-LLM）和教学 demo；商业产品（如 AI 面试 SaaS）基本不开源，本报告已尽量覆盖可验证的开源样本
- LangChain 官方曾有的 "Agent Simulation"（AI interviewer vs AI candidate）教程页面已随文档改版下架（原 python.langchain.com 链接 404 且新站无对应页面），故未收录官方教程
