# 简历解析 / 筛选 / 评分 / 人才匹配开源项目研究报告

> 研究时间：2026-08-06 ｜ 数据来源：GitHub Search API（`sort=stars`，star 数为查询时 approx 值）
> 用途：为「招聘智能体 Demo」（Python + Gradio + DeepSeek API：简历解析 → AI 初筛 → AI 互相聊天 → 筛选决策）做参考学习

---

## 一句话总结

**这类项目的主流方案已经收敛**：用 `PyMuPDF / pdfplumber / pdfminer / MarkItDown` 等把 PDF/DOCX 转成纯文本或 Markdown，再用 **LLM 按 JSON Schema 做结构化抽取**（分节提取、输出校验、日期回填修补），评分阶段采用 **「JD 关键词提取 + 命中率/相似度」或「LLM 多维加权评分（维度权重 + 证据 + 加分扣分）」**，岗位匹配则用关键词命中、embedding 余弦相似度或 LLM 直接判分；传统 spaCy/NER/规则方案（2018-2020 年主流）已基本被 LLM 方案取代，仅在超轻量场景保留。

---

## 搜索情况说明（如实汇报）

- 共搜索 16 个关键词：`resume parser`、`resume screening`、`resume scoring`、`CV parser`、`resume summarizer`、`job matching`、`resume matcher`、`LLM resume parser`、`resume ATS checker`、`resume GPT`、`talent matching`、`招聘 智能体`、`简历解析`、`简历筛选`、`简历评分`、`智能简历`。
- **中文关键词结果大量被无关项目污染**（如 funNLP 等聚合库、政治类、书籍类仓库霸榜），真正做「简历解析/筛选」的中文开源项目极少，且 star 普遍很低（个位数到 280）。结论：**中文场景没有成熟的简历解析开源方案，做中文必须自研或基于 LLM 现搭**；已筛出的中文相关项目以「求职者侧优化工具」和「招聘管理系统」为主，详见下文。
- 已排除：纯教程/博客（如 `laxmimerit/CV-Parsing-using-Spacy-3`）、纯资料型（如 `caiquegaspar/ats-engineer`，本质是 PDF 手册 + LaTeX 模板）、与主题无关的搜索噪音（CVE、CVPR 论文、x86 示例等）。

---

## 一、项目总表（按类别）

### A. 简历解析类（PDF/DOCX → 结构化数据）

| 项目 | Star | 语言 | 功能一句话 |
|---|---|---|---|
| [xitanggg/open-resume](https://github.com/xitanggg/open-resume) | 8.8k | TypeScript | 纯前端简历解析器 + 在线简历构建器，主打 ATS 可读性检测 |
| [LingyiChen-AI/JadeAI](https://github.com/LingyiChen-AI/JadeAI) | 1.9k | TypeScript | AI 智能简历生成器：50+ 模板、PDF/图片解析、JD 匹配分析 |
| [OmkarPathak/pyresparser](https://github.com/OmkarPathak/pyresparser) | 958 | Python | 经典传统 NLP 简历解析库（spaCy+NLTK），从 PDF/DOCX 提取姓名/邮箱/技能/经验/学校等 |
| [deepakpadhi986/AI-Resume-Analyzer](https://github.com/deepakpadhi986/AI-Resume-Analyzer) | 893 | Python | NLP 简历信息解析 + 技能匹配 |
| [DataTurks-Engg/Entity-Recognition-In-Resumes-SpaCy](https://github.com/DataTurks-Engg/Entity-Recognition-In-Resumes-SpaCy) | 459 | Python | 用 spaCy NER 做简历实体识别与自动摘要（附标注数据集，数据可复用） |
| [bjherger/ResumeParser](https://github.com/bjherger/ResumeParser) | 376 | Python | 配置驱动（YAML）的简历批量解析，输出汇总 CSV |
| [OmkarPathak/ResumeParser](https://github.com/OmkarPathak/ResumeParser) | 335 | HTML | pyresparser 的前身 Web 版 |
| [gogsbread/ResumeParser](https://github.com/gogsbread/ResumeParser) | 286 | HTML | GATE 框架规则式简历解析 |
| [chen0040/keras-english-resume-parser-and-analyzer](https://github.com/chen0040/keras-english-resume-parser-and-analyzer) | 284 | Python | Keras 深度学习简历解析（序列标注路线） |
| [hxu296/nlp-resume-parser](https://github.com/hxu296/nlp-resume-parser) | 274 | Python | **GPT-3 简历解析服务：PDF → JSON（LLM 结构化抽取最早的代表作之一）** |
| [gopiashokan/AI-Resume-Analyzer-and-LinkedIn-Scraper-using-Generative-AI](https://github.com/gopiashokan/AI-Resume-Analyzer-and-LinkedIn-Scraper-using-Generative-AI) | 207 | Python | LLM 简历分析：摘要、优缺点、LinkedIn 数据增强 |
| [perminder-klair/resume-parser](https://github.com/perminder-klair/resume-parser) | 146 | JavaScript | Node.js 简历转 JSON 库（规则+词表） |
| [praj2408/End-To-End-Resume-ATS-Tracking-LLM-Project-With-Google-Gemini-Pro](https://github.com/praj2408/End-To-End-Resume-ATS-Tracking-LLM-Project-With-Google-Gemini-Pro) | 82 | Python | Gemini ATS 简历解析+评分（视频教程配套项目，实现较完整） |

### B. 简历筛选 / 评分 / ATS 类

| 项目 | Star | 语言 | 功能一句话 |
|---|---|---|---|
| [interviewstreet/hiring-agent](https://github.com/interviewstreet/hiring-agent) | 6.8k | Python | **HackerRank 官方开源的「简历→评分」流水线**：解析+GitHub 信号增强+可解释评分 |
| [JAIJANYANI/Automated-Resume-Screening-System](https://github.com/JAIJANYANI/Automated-Resume-Screening-System) | 482 | Python | ML 简历自动筛选（含数据集） |
| [Hungreeee/Resume-Screening-RAG-Pipeline](https://github.com/Hungreeee/Resume-Screening-RAG-Pipeline) | 190 | Python | **RAG 简历筛选聊天机器人**：向量化简历 + LLM 问答式初筛 |
| [sunnypatell/ats-screener](https://github.com/sunnypatell/ats-screener) | 115 | Svelte | **模拟 Workday/Taleo/iCIMS/Greenhouse/Lever/SuccessFactors 六种 ATS 的评分器**，5 维加权评分 |
| [anukalp-mishra/Resume-Screening](https://github.com/anukalp-mishra/Resume-Screening) | 75 | Python | 传统 ML 简历分类筛选（教程向） |
| [mayankkala/Advanced-ATS-Resume-Checker](https://github.com/mayankkala/Advanced-ATS-Resume-Checker) | 63 | Python | 简历 ATS 深度反馈 + 评分 |
| [Okes2024/AI-based-Resume-Screening-for-Cultural-Fit](https://github.com/Okes2024/AI-based-Resume-Screening-for-Cultural-Fit) | 51 | Python | 文化契合度 AI 筛选（多维度 prompt 评分） |
| [312323205202/ai-resume-screening-system](https://github.com/312323205202/ai-resume-screening-system) | 50 | Python | AWS S3 + 分类 + 自动化的简历筛选系统 |
| [Ancastal/AI-Recruitment-Agent](https://github.com/Ancastal/AI-Recruitment-Agent) | 48 | Python | **AutoGen 多智能体招聘助手**：Screening/Interview/Data 三个 agent 协作（与 Demo 架构最像） |

### C. 岗位匹配 / 求职智能体类

| 项目 | Star | 语言 | 功能一句话 |
|---|---|---|---|
| [santifer/career-ops](https://github.com/santifer/career-ops) | 63k | Go | AI 求职工具：扫描招聘平台、按 A-F 分块 + 5 个加权维度评估岗位 |
| [feder-cr/Jobs_Applier_AI_Agent_AIHawk](https://github.com/feder-cr/Jobs_Applier_AI_Agent_AIHawk) | 30k | Python | AI 自动投简历 agent（解析职位、改写简历、自动申请） |
| [srbhr/Resume-Matcher](https://github.com/srbhr/Resume-Matcher) | 28k | TypeScript/Python | **简历×JD 匹配评分 + 关键词高亮 + 定制简历生成**（全栈：FastAPI+LiteLLM+Next.js） |
| [Gsync/jobsync](https://github.com/Gsync/jobsync) | 800 | TypeScript | 自托管求职追踪器 + AI 求职助手 |
| [weicanie/prisma-ai](https://github.com/weicanie/prisma-ai) | 401 | TypeScript | 中文求职 AI co-pilot：定制简历、匹配工作、面试准备 |
| [adrianhajdin/ai-resume-analyzer](https://github.com/adrianhajdin/ai-resume-analyzer) | 540 | JavaScript | React 简历上传 + AI 分析（教程向但完整） |
| [sliday/resume-job-matcher](https://github.com/sliday/resume-job-matcher) | 266 | Python | 简历-JD 自动匹配评分 + PDF 生成 |
| [he-yufeng/FindJobs-Agent](https://github.com/he-yufeng/FindJobs-Agent) | 252 | Python | LLM 求职工具包：技能分析、AI 面试、简历评分 |
| [tarunlnmiit/autopilot-jobhunt](https://github.com/tarunlnmiit/autopilot-jobhunt) | 191 | Python | 每晚扫描 130+ 招聘页、LLM 给每个岗位打分 |
| [binoydutt/Resume-Job-Description-Matching](https://github.com/binoydutt/Resume-Job-Description-Matching) | 188 | Python | 简历-JD 匹配（TF-IDF 路线） |
| [tonykipkemboi/resume-optimization-crew](https://github.com/tonykipkemboi/resume-optimization-crew) | 153 | Python | CrewAI 多 agent 简历优化：分析 JD、打分、给建议 |
| [amiradridi/Job-Resume-Matching](https://github.com/amiradridi/Job-Resume-Matching) | 134 | Python | 简历-JD 相似度计算 |
| [jlifeng/JobPilot](https://github.com/jlifeng/JobPilot) | 112 | TypeScript | 中文 AI 求职助手：简历构建、JD 匹配、模拟面试 |

### D. 中文相关项目（搜索结果中的真相关项）

| 项目 | Star | 语言 | 功能一句话 |
|---|---|---|---|
| [Snailclimb/interview-guide](https://github.com/Snailclimb/interview-guide) | 3.0k | Java | Spring AI 智能面试平台：Apache Tika 简历解析、AI 简历评估、模拟面试、RAG 知识库 |
| [Anarkh-Lee/resume-alchemist](https://github.com/Anarkh-Lee/resume-alchemist) | 280 | TypeScript | AI 简历优化：毒舌点评、STAR 润色、职位匹配 |
| [liangdabiao/resume-matcher-agent-cn](https://github.com/liangdabiao/resume-matcher-agent-cn) | 146 | Python | **「HR批评简历」中文简历审计工具**：Flask+DeepSeek/智谱，HR 视角 5 步审计报告（Resume-Matcher 中文二开） |
| [yenns7/zhipin-recruit](https://github.com/yenns7/zhipin-recruit) | 2 | Python | **智聘：Flask+LangGraph+DeepSeek 招聘全闭环**（简历解析→匹配→AI面试→看板），与 Demo 同栈 |
| [yyy2045/SmartHR](https://github.com/yyy2045/SmartHR) | 3 | Python | 多智能体协作招聘平台 |
| [RunnerQuan/talentflow](https://github.com/RunnerQuan/talentflow) | 1 | TypeScript | AI 招聘决策智能体：简历解析、技能图谱、智能匹配、面试助手 |

### E. 顺带发现但值得关注

| 项目 | Star | 语言 | 说明 |
|---|---|---|---|
| [jiatastic/GPTInterviewer](https://github.com/jiatastic/GPTInterviewer) | 262 | Python | 基于简历+JD 的 AI 面试官（Demo 的「AI 面试」环节可参考） |
| [caiquegaspar/ats-engineer](https://github.com/caiquegaspar/ats-engineer) | 102 | TeX | ATS 逆向工程手册（PDF）+ ATS 友好 LaTeX 模板，纯资料型 |
| [CodingLucasLi/GPT_Resume_analysing](https://github.com/CodingLucasLi/GPT_Resume_analysing) | 87 | Python | LangChain + OpenAI 简历分析 |

---

## 二、重点项目深入分析

### 1. interviewstreet/hiring-agent（6.8k★，HackerRank 官方开源）—— 最值得学的一个

**一句话**：官方招聘方视角的「简历 → 评分」完整流水线，评分体系设计是全 GitHub 同类项目里最严谨的。

**核心架构（5 步流水线）**：

```
PDF ──①pymupdf_rag.py──▶ Markdown 文本
      ──②pdf.py─────────▶ 按 section 用 Jinja 模板分节调 LLM 提取 JSON（basics/work/education/skills/projects/awards 共 6 个模板）
      ──③github.py──────▶ 从简历提取 GitHub 用户名 → 抓 profile+repos → LLM 选 top7 项目并分类（open_source 多人贡献 / self_project 单人）
      ──④evaluator.py───▶ 按岗位 role 的评分维度调 LLM 严格评分（结构化输出 JSON Schema）
      ──⑤score.py───────▶ 汇总输出 + CSV 落库（开发模式缓存中间结果）
```

**评分体系设计（重点）**：每个岗位是一个目录 `roles/<role_name>/`，包含 `role.json`（维度与权重）、`criteria.jinja`、`system_message.jinja`。软件实习岗的维度（实测源码）：

```json
{
  "categories": [
    {"key": "open_source",      "max": 35},
    {"key": "self_projects",    "max": 30},
    {"key": "production",       "max": 25},
    {"key": "technical_skills", "max": 10}
  ],
  "bonus_max": 20,
  "max_final_score": 120
}
```

- **维度权重体现价值观**：技术技能只占 10 分，开源贡献 35 分——官方明确「工程实践 > 技能堆砌」。
- **评分 prompt 内写死规则**（`system_message.jinja`，实测）：
  - 公平性约束：分数不得依赖姓名/性别/学校/CGPA/地点，只能看技术能力与项目质量；
  - 强制所有类别都给分且**不能超上限**（0-35/0-30/0-25/0-10，bonus≤20，总分≤120）；
  - 细到荒谬的扣分规则：纯 CRUD 教程项目 0 分、无链接的项目每个扣 3-5 分、只有 GitHub 链接没有 demo 扣 2-3 分、单独 Hacktoberfest 参加只给 5-8 分并强制扣 3-5 分；
  - **每个分数必须带 evidence（证据）**，key_strengths 限 1-5 条、areas_for_improvement 限 1-3 条；
  - 与 GitHub 数据联动：`project_type=open_source`（多人贡献）得分高于 `self_project`（单人）。
- **稳定性控制**：`temperature=0.5, top_p=0.9`，用 `format=JSON Schema`（provider 结构化输出），响应经 `extract_json_from_response` 清洗后用 Pydantic 校验。

**社区踩坑（对我们的警示，来自 README 引用的 4 篇分析文章）**：
- **LLM 非确定性方差**：同一简历跑 100 次分数在 74~90 波动，技术技能类稳定、项目质量类噪声大 → 需要 ensemble/多次采样；
- **PDF 隐形文本作弊**：PDF 里嵌入不可见白色小字可以显著拉高分数 → 解析时要注意；
- **评分标准公开后的博弈问题**：候选人会针对公开 rubric 优化简历，导致信号衰减。

**值得借鉴**：role.json 可配置评分维度、证据强制、公平性约束、加分/扣分结构、GitHub 数据增强。

---

### 2. srbhr/Resume-Matcher（28k★）—— 求职者侧最流行的简历×JD 匹配工具

**一句话**：简历上传 → 解析结构化 → 与 JD 做关键词匹配评分（带高亮）→ 生成定制简历，支持 100+ LLM（含 DeepSeek）。

**核心架构**（当前版本，FastAPI + Next.js 全栈）：

```
PDF/DOCX ──①MarkItDown──▶ Markdown
         ──②LLM（complete_json, retries=3）──▶ 结构化 JSON（ResumeData schema）
         ──③日期回填修补（restore_dates_from_markdown）──▶ 校验（Pydantic model_validate）
         ──④keyword-matcher（前端 TS）──▶ JD关键词 vs 简历 命中率 + 逐词高亮
```

**解析管线（实测 `apps/backend/app/services/parser.py`）**：
- 用 `MarkItDown` 把 PDF/DOCX 统一转 Markdown（比直接提纯文本好，保留结构）；
- LLM 按 schema 提取，system prompt 是「You are a JSON extraction engine. Output only valid JSON」；
- **妙招：日期回填**。LLM 常把 "Jun 2020 - Aug 2021" 丢成 "2020 - 2021"，代码用正则从原始 Markdown 里提取完整日期，回填进 JSON（`restore_dates_from_markdown`），这是「LLM 输出 + 规则校验修补」混合架构的典型范例；
- 失败重试 3 次，最终 Pydantic 校验兜底。

**匹配评分（实测 `keyword-matcher.ts`）**：
- JD 关键词提取：小写化 → 按非字母数字切分（保留连字符）→ 过滤停用词（含 role/position/required/experience 等招聘常见词）→ 最短 3 字符、排除纯数字；
- 匹配分 = JD 关键词命中数 / JD 关键词总数（百分比）；
- 简历文本按词切段标记命中与否，UI 上高亮「哪些关键词中了、哪些没中」——**这个可视化对 Demo 很有借鉴意义**。

**值得借鉴**：MarkItDown 统一文档转 Markdown、LLM+规则混合（日期回填）、关键词命中率 + 高亮可视化、`You are a JSON extraction engine` 这类强约束 prompt。

---

### 3. hxu296/nlp-resume-parser（274★）—— LLM 结构化抽取的鼻祖

**一句话**：2022 年的 GPT-3 简历解析服务，验证了「PDF 提文本 + LLM 出 JSON」这条路线的可行性。

**架构**：Flask 服务 → `pdftotext` 提文本 → GPT-3（text-davinci-002）按目标 JSON 结构输出 → 返回结构化简历。一个 PDF 约 15 秒、$0.01-0.06。

**抽取字段**：基本信息（姓名/邮箱/电话/位置/作品集/LinkedIn/GitHub）、教育（学校/学历/毕业年月/专业/GPA）、工作经历（职位/公司/地点/时长/内容）、项目经历（名称/描述）。**注意它包含 GPA 字段**——而 hiring-agent 明确禁止用 GPA 评分，两个项目的取舍恰好形成对照。

**值得借鉴**：字段清单可以作为我们结构化输出的基线；其「prompt 里贴目标 JSON 示例 + 只允许输出 JSON」的做法被后续所有项目沿用。缺点是整篇一次抽取（不分节），长简历容易丢信息——后来者都改成了分节提取。

---

### 4. Ancastal/AI-Recruitment-Agent（48★）—— 与 Demo 架构最接近的多智能体项目

**一句话**：微软 AutoGen 四智能体招聘助手，从简历筛选到面试题生成全流程 agent 协作。

**Agent 分工**：
- **Screening Agent**：简历 vs JD 关键词匹配 + AI 评估（初筛）；
- **Interview Agent**：基于技能差距生成面试题（面试环节）；
- **Data Management Agent**：候选人与结果落 CSV（数据层）；
- **User Proxy Agent**：编排整个流程（调度）。

**技术栈**：AutoGen + GPT-4o-mini + spaCy + pdfplumber（PDF）+ docx2txt（DOCX）。

**值得借鉴**：agent 分工模式（筛 → 面 → 存）与 Demo 的「初筛 → 互相聊天 → 决策」天然对应；但它用的是 AutoGen 组播，我们更轻的做法可以是一个 prompt 里定义多个角色轮流发言（或干脆逐个调用 DeepSeek API 模拟聊天）。它暴露的问题：agent 间通过自然语言传递简历全文，token 消耗大且信息丢失——**建议 agent 间只传递结构化 JSON 摘要**。

---

### 5. 中文项目：liangdabiao/resume-matcher-agent-cn 与 yenns7/zhipin-recruit —— 与我们同栈的现成参考

**resume-matcher-agent-cn（「HR批评简历」，146★）**：基于 Resume-Matcher 二开的中文版，架构极简：Flask 后端仅 7 个文件 5 个依赖 + JSON 文件存储（零数据库）+ pdfminer.six 解析 PDF + 任意 OpenAI 兼容 API（默认智谱，实测支持 DeepSeek）。其 prompt 设计（实测源码）非常值得抄：

- `PROMPT_STRUCTURED_RESUME`：JSON 提取引擎式（不要 Markdown、不要编造、日期 YYYY-MM-DD、只输出 raw JSON），Schema 含 Personal Data / Experiences / Projects / Skills / Education / **Extracted Keywords**（专门抽关键词供匹配用）；
- `PROMPT_STRUCTURED_JOB`：JD 同款 schema，也带 `extractedKeywords` —— 简历和 JD 都抽关键词，之后做集合比对；
- `PROMPT_HR_JUDGE`：中文 HR 深度审计，**5 步输出结构**（第一印象/地毯式审计/修改蓝图/完整改写简历/最终裁决）+ 每条反馈「批判-解析-建议」三段式 + 字数预算（诊断≤800 字、重写≤1000 字）+ 时间线以当前日期为参照 + 缺数据的启发式占位符（`[量化指标：如将 API 响应时间从 800ms 优化至 200ms]`）。

**yenns7/zhipin-recruit（智聘，2★）**：与我们 Demo 几乎完全同栈（Flask + DeepSeek + pdfplumber/python-docx），覆盖简历解析 → 岗位发布 → 技能匹配排名（命中/欠缺标签可视化）→ AI 面试 → BI 看板全闭环，还加了 LangGraph ReAct 智能体做自然语言操作（写操作需用户确认）。虽然 star 极少，但作为**架构蓝图**参考价值高：它证明了 Flask+DeepSeek 单栈就能撑起完整招聘闭环。

**值得借鉴**：中文 prompt 的强结构（5 步 + 字数预算 + 占位符）；简历/JD 双侧抽关键词再比对；JSON 文件存储够用；「写操作确认」防误操作。

---

### 6. sunnypatell/ats-screener（115★）—— 「多考官」评分模拟器

**一句话**：给一份简历算出 **6 个分数**（分别模拟 Workday/Taleo/iCIMS/Greenhouse/Lever/SuccessFactors 的解析与评分策略），并给出按影响度排序的修改建议。

**评分引擎**：每个 ATS 平台是一个 profile，对 **5 个维度**（Formatting 可解析性 / Keyword Match / Sections 完整性 / Experience 量化与行动动词 / Education 匹配度）施加**不同权重**与**不同匹配策略**（Taleo 字面精确匹配、iCIMS 语义 ML 匹配、Greenhouse LLM 语义匹配、Lever stemming 匹配、SuccessFactors 分类法归一化）。

**解析**：客户端 Web Worker 里用 pdfjs-dist（PDF）+ mammoth（DOCX），文件不上传；本地 TF-IDF + 技能分类法（8+ 行业）做关键词；评分交给 LLM（Gemini Flash Lite，Groq Llama 兜底）。

**值得借鉴**：「同一个简历，不同考官（profile）给出不同分数」的模式，与 Demo 的「多个 AI 面试官互相聊天」天然契合——可以设计 2-3 个不同风格的评分 agent（严格技术派/潜力派/沟通派），各自带权重输出，再汇总决策。另外「General（只看简历）与 Targeted（简历+JD）两种评分模式」也值得参考。

---

### 7. OmkarPathak/pyresparser（958★）—— 传统 NLP 路线（对比用）

**一句话**：无 LLM 时代的标杆，spaCy + NLTK + 规则从 PDF/DOCX 提字段，输出 dict（name/email/mobile_number/skills/total_experience/college_name/degree/designation/company_names）。

**实现要点**：姓名/学校/职称用 spaCy NER 实体 + 规则；技能靠**自定义技能词表**逐词匹配；经验年限靠日期正则计算。**局限**：准确率依赖词表质量、不支持中文、无法提取结构化经历。

**对照结论**：这类传统方案已过时，但「**技能词表匹配**」这个思想值得保留——LLM 抽取技能后，用词表/同义词归一化（如 ML ≈ machine learning ≈ 机器学习）能显著提升匹配准确率。

---

## 三、对我们 Demo 的启发（可落地清单）

1. **解析管线直接照搬「MarkItDown/PyMuPDF 提文本 → LLM JSON 结构化 → 规则修补」三层架构**：第一层 PDF/DOCX → Markdown（保留结构）；第二层 LLM 按 JSON Schema 分节提取（参考 hiring-agent 的 6 个 section 模板 + Resume-Matcher 的 `You are a JSON extraction engine` prompt）；第三层用 Pydantic `model_validate` 校验 + **正则日期回填**修补 LLM 丢月份的问题（抄 `restore_dates_from_markdown` 思路）。这三层在 Python 里全部 100 行内可实现。

2. **结构化输出里加 `extractedKeywords` 字段（简历和 JD 双侧都抽）**：参考 resume-matcher-agent-cn——LLM 直接抽关键词比词法提取准得多（中文尤其明显，DeepSeek 能正确抽出「大模型微调」这类复合词），之后匹配就是集合运算，可解释性强。

3. **评分体系用「role.json 式可配置维度 + 权重 + 加分/扣分 + 强制证据」**：把维度（如技能匹配/项目质量/经验相关度/软技能）和权重放配置文件，prompt 动态渲染；每个分数强制给 evidence 引用原文；加 bonus_max 和总分上限。**中文场景可以抄 hiring-agent 的「公平性约束」**（不因学校/GPA/性别加减分——国内招聘尤其敏感，也符合合规要求）。

4. **评分稳定性三件套**：`temperature` 压到 0.5 左右；用 DeepSeek 的 `response_format={"type":"json_object"}` 强制结构化输出；**关键决策（是否进入下一轮）对同一候选人跑 2-3 次取均值或让多个 agent 独立打分后汇总**——hiring-agent 的方差问题（74~90 波动）是前车之鉴，而 Demo 的「AI 互相聊天」天然就是 ensemble，让每个 AI 独立看简历打分再讨论，能显著降噪。

5. **「多考官 profile」直接映射到 Demo 的多 agent 设计**：参考 ats-screener 给不同考官不同权重（严格技术派重技能命中、潜力派重项目复杂度、沟通派重表达），各自输出带证据的分数，最后由决策 agent 加权汇总——比所有 agent 用同一套标准更有说服力，也让「互相聊天」有真实的观点分歧。

6. **agent 之间只传结构化 JSON，不传简历全文**：Ancastal 的教训是 agent 间传全文既费 token 又丢信息。我们 Demo 的聊天环节应让每个 AI 基于同一份结构化 JSON（+各自补充提问的答案）发言，聊天记录也存 JSON。

7. **中文 prompt 抄「HR 批评简历」的强结构输出**：5 步报告（第一印象/审计/修改建议/裁决）+ 每条反馈三段式（批判-解析-建议）+ 字数预算 + 缺数据用占位符而非编造。这套结构让 DeepSeek 的输出稳定且可直接展示给用户。另外简历/JD 文本用 pdfplumber（PDF）+ python-docx（DOCX）即可，无需重依赖。

8. **防作弊与防幻觉**：解析层校验（空字段拒绝、日期格式校验、URL 格式校验）；对「隐形文本」（PDF 白色小字塞关键词）这类攻击至少在报告里提示风险；LLM 抽取失败重试 2-3 次，仍失败则降级返回原始文本并标记「解析失败」——参考 interview-guide 的「分批评估 + 降级兜底」。

---

## 附：研究过程材料

- 原始搜索结果：`research/_search_results.json`、`_search_results2.json`（16 个关键词的 API 原始响应）
- 重点项目 README 缓存：`research/_readmes/`（13 个项目）
- 关键源码摘录：`research/_src/`（hiring-agent 的 role.json/evaluator.py/system_message.jinja、Resume-Matcher 的 parser.py/keyword-matcher.ts、resume-matcher-agent-cn 的 prompts.py）
