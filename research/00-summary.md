# AI 招聘智能体 · 全行业调研总报告

> 6 个并行研究 agent 产出（2026-08-07）：开源项目 4 份 + 商用产品 2 份
> 明细见：`01-ai-interviewers.md`（面试官开源）/ `02-recruiting-agents.md`（招聘Agent开源）/ `03-resume-parsing.md`（简历解析开源）/ `04-multi-agent.md`（多智能体框架）/ `05-commercial-cn.md`（国内商用）/ `06-commercial-global.md`（国外商用）

---

## 一、市场全景一句话

- **开源**：全球约 180 个相关仓库，最值得抄的是 `interviewstreet/hiring-agent`（6.8k★，HackerRank 官方，评分体系最严谨）和 `srbhr/Resume-Matcher`（28k★，简历匹配）；**中文开源赛道极弱**（"招聘智能体"仅 7 条结果且多为 0-5★ 个人作品）——差异化窗口。
- **商用（国内）**：平台自研 AI（猎聘 AI账号、BOSS DeepHire、智联 AI易面、58 神奇面试间）+ HR SaaS（北森、用友大易、Moka、多面）+ 垂直厂商（海纳AI、牛客）全链路竞争，海纳 AI 官方确认用 DeepSeek 底座（可作技术背书）。
- **商用（国外）**：三范式——文本聊天面试（Sapia/Paradox Olivia）、语音双向 AI 面试官（HireVue）、单向视频+转写评分（TestGorilla）。Paradox 已被 Workday 收购；HireVue 2020 年因面部分析被批伪科学而下架该功能。
- **最大空白**：国内外都没有"AI 招聘官 × AI 候选人**双向自由互相聊天**"的公开产品——我们 Demo 的形态就是差异化。

## 二、行业共识：主流架构（所有报告交叉验证）

```
简历获取 → 文本提取(MarkItDown/PyMuPDF) → LLM 按 JSON Schema 分节抽取(带证据)
→ 硬规则过滤 + LLM 评分(rubric 加权, 分数附理由) → AI 面试(题目清单驱动, 一次一问)
→ 独立评估 agent 出结构化报告 → 人工闸门(最终决定权在人)
```

关键设计共识（反复出现，可信度高）：
1. **评分必须带证据**：每条分数引用简历原文/对话原文，否则分数不可信
2. **rubric 配置化**：维度/权重/JD 分离成配置文件（role.json 式），不写死在 prompt 里
3. **一次只问一个问题** + 防重复提问（题目列表耗尽 + max_rounds 双保险）
4. **上下文隔离**：候选人模型只知道自己的简历，不知道 JD 和评分标准
5. **评估 agent 独立**：只读对话记录，不实时干预，避免"考官自问自评"
6. **AI 不决定，人决定**：算法给建议 + 证据，HR 一键通过/驳回（Eightfold 原则，也是合规底线）

## 三、六大报告精华提炼

| 方向 | 最值得抄的项目/产品 | 一句话精华 |
|---|---|---|
| 面试官开源 | GPTInterviewer(262★) / AiInterview / DeepInterview | 回答含糊必须追问；评分按题 rubric + 证据引用；未答题不计分 |
| 招聘Agent开源 | hiring-agent(6.8k★) / AI-Recruitment-Agent | 角色化 rubric + JSON schema 强制输出；agent 间只传结构化 JSON 不传全文 |
| 简历解析开源 | Resume-Matcher(28k★) / zhipin-recruit | 三层管线：提文本→LLM抽取→规则修补（正则回填日期）；Flask+DeepSeek 单栈闭环证明 |
| 多智能体框架 | CAMEL(鼻祖) / LangGraph 状态机 | 双注入 system prompt + 角色重标注喂上下文；题目列表耗尽终止 |
| 国内商用 | 猎聘 AI账号 / BOSS DeepHire / 海纳AI | 全流程 Agent 叙事；AI 生成个性化邀约话术；反馈校准闭环（对标 Moka Eva） |
| 国外商用 | Sapia / HireVue / Paradox | 加权胜任力模型（JD→5-8 维度+权重）；评分卡+雷达图；合规设计（Consent 步骤、人审） |

## 四、对我们 Demo 的可落地升级清单（按优先级）

### P0 — 直接抄，改动小收益大
1. **评分附证据**：evaluator 每个维度的分数后加一句引用（"候选人原话：…"）——报告可信度质变
2. **回答含糊必须追问**：interviewer SYSTEM 加规则——回答只列要点/空洞时，最多连续追问 2 次再推进（对标 AiInterview 四维度信号）
3. **面试官上下文隔离**：候选人 AI 的 system 里只放简历（我们现在已经做到），招聘官侧不暴露候选人视角，用"角色重标注"喂历史（最新一条标 user）
4. **一次一问防重复**：SYSTEM 硬约束 + 结束双保险（我们已有 round 上限，加"题目列表耗尽"意识即可）

### P1 — 企业化观感
5. **rubric 配置化**：把评分维度/权重提成 `job_profile.json`（如 技术40/项目30/沟通20/匹配10），演示时现场改权重看报告变化——直接展示"企业可用性"
6. **人工闸门**：报告后加"HR 审核"按钮（通过/驳回 + 意见），展示 AI 不决定、人决定
7. **合规要素**：演示流中加一条"已获候选人授权同意，数据仅用于招聘评估"的提示（PIPL 观感）
8. **加权胜任力模型**：从 JD 自动生成 5-8 个评估维度及权重，报告渲染成雷达图（对标 Sapia，Gradio 可实现）

### P2 — 差异化深化
9. **防作弊观感**：同简历多次运行分数稳定性（temperature 调低 + ensemble 多次取均值）——hiring-agent 被社区实测打脸"分数波动 74-90"，我们提前解决
10. **多考官 profile**：评估时让"技术考官/文化考官"两个角色分别打分再加权（对标 ats-screener 多考官加权）

## 五、给演示/面试用的 3 句干货

1. "我们参考了 HackerRank 官方 hiring-agent 和 Resume-Matcher（28k★）的架构：三层解析 + rubric 评分 + 证据链，同时用 DeepSeek 把单次面试成本降到几分钱"
2. "全行业目前没有'AI 互相聊天筛选'的产品形态——猎聘 AI账号是话术模板批量邀约、Paradox 是模板问答，我们是双向自由对话，这是差异化"
3. "企业落地的核心不是模型，是数据合规和人工闸门：AI 只给建议+证据，最终决定权在人（Eightfold 原则，也是 PIPL 合规底线）"
