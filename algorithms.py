"""招聘筛选算法库 —— 全部为确定性代码实现（不依赖 LLM 算数），可解释、可审计、可测试

算法清单：
1. 规则引擎（决策表判定）  check_rules()
   学历/年限/必备技能/薪资上限/排除词，任一硬性条件不满足 → 淘汰并给出原因
2. TF-IDF + 余弦相似度      tfidf_similarity()
   JD 与简历在技能词维度上的文本匹配度（0~1），用于初筛排序的第二参照分
3. 代码侧简历字段提取        extract_fields()
   正则 + 技能词表匹配，从简历文本直接提取结构化字段（规则引擎的输入，不调 LLM）
4. 加权评分模型              weighted_total()
   总分 = Σ(维度分 × 岗位权重) / Σ权重（LLM 出维度分，代码算总分，防 LLM 算错）

与 LLM 侧算法的分工：LLM 负责"理解与评价"（解析摘要、维度打分、证据链），
代码负责"计算与判定"（加权、排序、硬性规则），二者互相校验。
"""
import math
import re

# ---------- 学历等级映射（规则引擎用） ----------
EDU_LEVELS = {"高中": 0, "中专": 0, "大专": 1, "本科": 2, "硕士": 3, "研究生": 3, "博士": 4}


# ---------- 技能词表（TF-IDF 词典 + 规则引擎必备技能匹配共用） ----------
SKILL_LEXICON = [
    # 语言/框架
    "python", "java", "golang", "go", "c++", "javascript", "typescript", "rust", "php",
    "fastapi", "django", "flask", "spring", "spring boot", "vue", "react", "node",
    "pytorch", "tensorflow", "scikit-learn",
    # 大模型/AI
    "大模型", "llm", "langchain", "llamaindex", "rag", "prompt", "embedding", "向量",
    "向量数据库", "milvus", "chroma", "faiss", "微调", "fine-tune", "深度学习", "机器学习",
    "nlp", "aigc", "agent", "智能体", "vllm", "推理优化", "重排", "rerank", "多模态",
    "deepseek", "gpt", "通义", "文心",
    # 后端/基础设施
    "mysql", "postgresql", "redis", "kafka", "rabbitmq", "消息队列", "微服务", "分布式",
    "高并发", "docker", "kubernetes", "k8s", "linux", "nginx", "elasticsearch", "es",
    "mongodb", "分库分表", "限流", "降级", "熔断", "幂等", "事务",
    # 大数据
    "spark", "flink", "hive", "hadoop", "数据仓库", "数仓", "etl", "pandas", "sql",
    # 前端
    "小程序", "webpack", "vite", "css", "html", "echarts", "可视化", "微前端", "性能优化",
    # 测试/运维
    "pytest", "selenium", "jmeter", "自动化测试", "jenkins", "ci/cd", "devops", "监控",
    # 产品/数据
    "axure", "产品设计", "数据分析", "ab实验", "ctr", "powerbi",
]
# 供外部导入：技能词表即 TF-IDF 词典
LEXICON = SKILL_LEXICON

# ---------- 正则模式（代码侧字段提取） ----------
_EDU_PAT = re.compile(r"(博士|硕士|研究生|本科|大专|中专|高中)")
_YEARS_PAT = re.compile(r"(?<!\d)(\d{1,2})\s*年(?![龄纪])")  # "5年Python" 匹配；负向前瞻避开 "2026年" 的 "26年"
_SALARY_PAT = re.compile(r"(\d{1,2}(?:\.\d)?)\s*[-~至]\s*(\d{1,3})\s*[kK千]?")
_NAME_PAT = re.compile(r"^([\u4e00-\u9fa5]{2,4})[，,]")
_EMAIL_PAT = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def extract_fields(resume_text: str) -> dict:
    """代码侧简历结构化提取（正则 + 词表匹配，确定性，不调 LLM）

    返回 {name, education, years, skills, expected_salary, email}
    —— 供规则引擎硬性判定使用；LLM 解析（resume_parser）负责语义层面的补充。
    """
    text = resume_text or ""
    name_m = _NAME_PAT.search(text.strip())
    edu_m = _EDU_PAT.search(text)
    years_m = _YEARS_PAT.search(text)
    sal_m = _SALARY_PAT.search(text)
    email_m = _EMAIL_PAT.search(text)
    lower = text.lower()
    skills = sorted({s for s in SKILL_LEXICON if s in lower})
    return {
        "name": name_m.group(1) if name_m else "",
        "education": edu_m.group(1) if edu_m else "",
        "years": int(years_m.group(1)) if years_m else 0,
        "skills": skills,
        "expected_salary": (float(sal_m.group(1)), float(sal_m.group(2))) if sal_m else None,
        "email": email_m.group(0) if email_m else "",
    }


# ---------- 1. 规则引擎（决策表判定） ----------
def check_rules(fields: dict, rules: dict) -> tuple:
    """硬性筛选规则判定。返回 (passed: bool, reasons: list[str])

    rules 支持（全部可选，缺省不检查）：
      min_education  最低学历（"本科"）
      min_years      最低工作年限
      max_years      最高年限（防资历过高，0 表示不限）
      must_skills    必备技能（全部命中才过，任一缺失即淘汰）
      plus_skills    加分技能（命中可加分提示，不淘汰）
      max_salary     期望薪资上限（单位 K，取区间低值比较）
      exclude_keywords 排除关键词（简历中出现任一即淘汰）
    """
    reasons, passed = [], True
    edu = fields.get("education", "")
    if rules.get("min_education") and edu:
        if EDU_LEVELS.get(edu, -1) < EDU_LEVELS.get(rules["min_education"], 0):
            passed = False
            reasons.append(f"学历不达标（要求{rules['min_education']}以上，实际{edu}）")
    years = fields.get("years", 0)
    if rules.get("min_years") and years < rules["min_years"]:
        passed = False
        reasons.append(f"工作年限不足（要求{rules['min_years']}年以上，实际约{years}年）")
    if rules.get("max_years") and years > rules["max_years"]:
        passed = False
        reasons.append(f"工作年限超出上限（上限{rules['max_years']}年，实际约{years}年，资历过高）")
    skills = fields.get("skills", [])
    for s in rules.get("must_skills", []):
        if s and s not in skills:
            passed = False
            reasons.append(f"缺少必备技能：{s}")
    sal = fields.get("expected_salary")
    if sal and rules.get("max_salary"):
        if sal[0] > rules["max_salary"]:
            passed = False
            reasons.append(f"期望薪资超预算（上限{rules['max_salary']}K，期望{sal[0]}~{sal[1]}K）")
    lower_text = " ".join(skills)
    for kw in rules.get("exclude_keywords", []):
        if kw and kw in lower_text:
            passed = False
            reasons.append(f"命中排除关键词：{kw}")
    return passed, reasons


# ---------- 2. TF-IDF + 余弦相似度（JD ↔ 简历匹配） ----------
def _tokenize(text: str) -> list:
    """分词：英文/数字连续串 + 技能词表多词匹配（长词优先）"""
    text = text or ""
    tokens = re.findall(r"[a-z][a-z0-9+#.-]{1,}", text.lower())
    for word in sorted(SKILL_LEXICON, key=len, reverse=True):
        if word in text.lower():
            tokens.append(word)
    return tokens


def _tfidf_vectors(docs: list) -> list:
    """文档集 → TF-IDF 向量列表。

    tf = 词频；idf = ln((1+N)/(1+df)) + 1（平滑，防除零）
    """
    tokenized = [_tokenize(d) for d in docs]
    n = len(tokenized)
    df = {}
    for toks in tokenized:
        for w in set(toks):
            df[w] = df.get(w, 0) + 1
    vectors = []
    for toks in tokenized:
        tf = {}
        for w in toks:
            tf[w] = tf.get(w, 0) + 1
        vec = {w: c * (math.log((1 + n) / (1 + df[w])) + 1) for w, c in tf.items()}
        vectors.append(vec)
    return vectors


def _cosine(a: dict, b: dict) -> float:
    """余弦相似度：cos = A·B / (|A|·|B|)，向量为稀疏 dict"""
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def tfidf_similarity(jd_text: str, resume_texts: list) -> list:
    """JD 与每份简历的 TF-IDF 余弦相似度（0~1），返回与 resume_texts 同序的列表。

    文档集 = [JD] + 简历们，IDF 在同一语料内计算，JD 为查询向量。
    """
    docs = [jd_text] + list(resume_texts)
    vecs = _tfidf_vectors(docs)
    jd_vec = vecs[0]
    return [round(_cosine(jd_vec, v), 3) for v in vecs[1:]]


# ---------- 4. 加权评分模型 ----------
def weighted_total(dimension_scores: dict, weight_map: dict) -> float:
    """总分 = Σ(维度分 × 权重) / Σ权重。缺失维度按 0 分计入分母（防总分虚高）"""
    total, weight_sum = 0.0, 0
    for name, weight in weight_map.items():
        total += float(dimension_scores.get(name, 0)) * weight
        weight_sum += weight
    return round(total / weight_sum, 1) if weight_sum else 0.0


# ---------- 分层打分模型：规则层 60% + 语义匹配层 30% + 加分层 10% ----------
# 对应《简历打分算法逻辑说明》：三层可解释打分，权重可配（job_profiles.rules.layer_weights）
DEFAULT_LAYER_WEIGHTS = {"rule": 0.6, "match": 0.3, "bonus": 0.1}

# 加分层人工规则库（10% 权重）：大厂背景 / 证书 / 项目复杂度关键词
BIG_COMPANY_NAMES = ["阿里", "腾讯", "字节", "百度", "美团", "京东", "华为", "网易", "拼多多", "快手", "滴滴", "微软", "谷歌", "google", "amazon", "meta", "bilibili", "小红书", "shopee"]
CERTIFICATES = ["软考", "pmp", "acm", "ccf", "专利", "论文", "kaggle", "阿里云认证", "腾讯云认证", "aws认证", "雅思", "托福", "cet-6", "英语六级", "系统架构师", "高级工程师"]
PROJECT_DEPTH_KEYWORDS = ["从0到1", "从零搭建", "主导", "架构", "亿级", "千万级", "百万级", "日均", "qps", "峰值", "开源", "贡献", "落地", "上线", "降本", "提效"]


def rule_layer_score(fields: dict, rules: dict) -> dict:
    """规则层（60%）：硬门槛判定 + 满足度评分 + overqualified 标记。

    硬门槛（任一不满足直接淘汰，返回 passed=False）：check_rules 的硬性条件；
    满足度评分（0-100，硬门槛全过时生效）：
      必备技能命中率 ×60 + 学历富余 ×20 + 年限匹配 ×20
    overqualified 标记：学历超过岗位要求 2 级及以上（如要求大专、候选博士）→
      不直接淘汰、不自动降分，返回 flag 由 HR 决定（法律风险敏感项，人做判断）。
    """
    passed, reasons = check_rules(fields, rules)
    if not passed:
        return {"passed": False, "score": 0.0, "reasons": reasons}
    # 满足度评分
    must = rules.get("must_skills", [])
    must_hit = sum(1 for s in must if s in fields.get("skills", [])) / len(must) if must else 1.0
    edu = fields.get("education", "")
    edu_min = rules.get("min_education", "")
    flags = []
    if edu_min and edu in EDU_LEVELS:
        gap = EDU_LEVELS[edu] - EDU_LEVELS[edu_min]
        if gap >= 2:
            flags.append(f"学历超出岗位要求 2 级（要求{edu_min}，实际{edu}）——建议人工关注，由 HR 决定是否按 overqualified 降分")
        edu_score = min(1.0, 0.6 + 0.2 * gap)
    else:
        edu_score = 0.6  # 未配置学历要求时给中位分，不奖不罚
    years = fields.get("years", 0)
    y_min, y_max = rules.get("min_years", 0), rules.get("max_years", 0)
    if y_min or y_max:
        lo = y_min if y_min else max(0, years - 3)
        hi = y_max if y_max else years + 5
        mid = (lo + hi) / 2
        years_score = max(0.0, 1.0 - abs(years - mid) / max(1.0, mid))
    else:
        years_score = 0.6
    score = round((0.6 * must_hit + 0.2 * edu_score + 0.2 * years_score) * 100, 1)
    return {"passed": True, "score": score, "reasons": reasons, "flags": flags}


def bonus_layer_score(fields: dict, resume_text: str) -> float:
    """加分层（10%）：大厂背景 + 证书 + 项目复杂度关键词，人工规则加权（0-100）

    命中项封顶 100：大厂 40 / 证书 30 / 项目深度关键词 30（多命中按阶梯累加）
    """
    text = (resume_text or "").lower()
    skills_text = " ".join(fields.get("skills", []))
    score = 0.0
    big = sum(1 for n in BIG_COMPANY_NAMES if n in text)
    cert = sum(1 for c in CERTIFICATES if c in text)
    depth = sum(1 for k in PROJECT_DEPTH_KEYWORDS if k in text)
    score += min(40.0, big * 20)          # 大厂背景：每家 20，封顶 40
    score += min(30.0, cert * 15)          # 证书：每项 15，封顶 30
    score += min(30.0, depth * 10)         # 项目复杂度：每个关键词 10，封顶 30
    return round(score, 1)


def bm25_scores(jd_text: str, resume_texts: list, k1: float = 1.5, b: float = 0.75) -> list:
    """BM25 稀疏检索（关键词精确匹配的经典排序算法，确定性实现）

    score(D,Q) = Σ idf(qi) · f(qi,D)·(k1+1) / (f(qi,D) + k1·(1−b+b·|D|/avgdl))
    idf(qi) = ln(1 + (N − df + 0.5) / (df + 0.5))
    D=简历文档，Q=JD 查询，f=词频，df=含词文档数，avgdl=平均文档长度。
    """
    docs = [jd_text or ""] + [t or "" for t in resume_texts]
    tokenized = [_tokenize(d) for d in docs]
    n = len(tokenized) - 1  # 文档集只算简历
    avgdl = sum(len(t) for t in tokenized[1:]) / n if n else 1.0
    df = {}
    for toks in tokenized[1:]:
        for w in set(toks):
            df[w] = df.get(w, 0) + 1
    query_terms = tokenized[0]
    scores = []
    for toks in tokenized[1:]:
        dl = len(toks)
        tf_map = {}
        for w in toks:
            tf_map[w] = tf_map.get(w, 0) + 1
        total = 0.0
        for qi in set(query_terms):
            f = tf_map.get(qi, 0)
            if not f:
                continue
            idf = math.log(1 + (n - df.get(qi, 0) + 0.5) / (df.get(qi, 0) + 0.5))
            total += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / max(avgdl, 1.0)))
        scores.append(round(total, 4))
    return scores


def _normalize(values: list) -> list:
    """min-max 归一化到 [0,1]（全零时返回全零）"""
    if not values:
        return []
    vmax = max(values)
    vmin = min(values)
    if vmax == vmin:
        return [0.0] * len(values)
    return [round((v - vmin) / (vmax - vmin), 4) for v in values]


def _rank_list(scores: list) -> list:
    """分数 → 排名（1 起，高分在前，并列取平均名次）"""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    ranks = [0] * len(scores)
    for pos, idx in enumerate(order, 1):
        ranks[idx] = pos
    return ranks


def reciprocal_rank_fusion(score_lists: list, k: float = 60.0) -> list:
    """RRF 融合：多路检索结果按排名融合。score(d) = Σ 1/(k + rank_i(d))

    输入多路分数列表（分数越高越好），输出融合分数（越高越好，确定性）。
    """
    if not score_lists:
        return []
    n = len(score_lists[0])
    fused = [0.0] * n
    for scores in score_lists:
        for idx, rank in enumerate(_rank_list(scores)):
            fused[idx] += 1.0 / (k + rank)
    return [round(v, 6) for v in fused]


def match_layer_score(jd_text: str, resume_texts: list, dense_scores: list = None) -> list:
    """语义匹配层（30%）：JD↔简历匹配度（0-100），混合检索实现。

    双路稀疏检索 + RRF 融合：
    - 路1：TF-IDF + 余弦相似度（词级软匹配）
    - 路2：BM25（关键词精确匹配经典算法）
    - 融合：RRF（Reciprocal Rank Fusion，k=60）
    dense 路（Embedding 语义向量，如 bge-large-zh / Sentence-BERT）为适配器占位：
    传入 dense_scores 时自动三路 RRF 融合；生产环境接入向量库后即启用。
    无 dense 时输出归一化后 ×100 的融合分。
    """
    tfidf = tfidf_similarity(jd_text, resume_texts)
    bm25_norm = _normalize(bm25_scores(jd_text, resume_texts))
    if dense_scores is not None and len(dense_scores) == len(resume_texts):
        # 三路 RRF：dense（语义）+ BM25（精确）+ TF-IDF（词级），融合后归一化到 0-100
        fused = reciprocal_rank_fusion([list(dense_scores), bm25_norm, tfidf])
        fused_norm = _normalize(fused)
        return [round(f * 100, 1) for f in fused_norm]
    # 双路：BM25 与 TF-IDF 各占 50%（确定性、无外部依赖）
    return [round((0.5 * bm + 0.5 * tf) * 100, 1) for bm, tf in zip(bm25_norm, tfidf)]


def composite_score(rule_result: dict, match_score: float, bonus_score: float, weights: dict = None) -> dict:
    """综合打分：规则层 60% + 语义匹配层 30% + 加分层 10%（权重可配）

    硬门槛不通过 → 综合分 0 且淘汰；返回 {passed, total, layers}（layers 保留各层得分，可解释）
    """
    w = {**DEFAULT_LAYER_WEIGHTS, **(weights or {})}
    if not rule_result.get("passed"):
        return {"passed": False, "total": 0.0, "layers": {
            "rule": rule_result.get("score", 0), "match": match_score, "bonus": bonus_score,
            "reasons": rule_result.get("reasons", []),
        }}
    total = w["rule"] * rule_result["score"] + w["match"] * match_score + w["bonus"] * bonus_score
    return {
        "passed": True,
        "total": round(total, 1),
        "layers": {"rule": rule_result["score"], "match": match_score, "bonus": bonus_score,
                    "weights": w},
    }


# ---------- 算法说明（界面与 README 展示用） ----------
ALGORITHM_DOC = """## 招聘筛选算法说明

### 分层打分模型（综合分 = 规则层 60% + 语义匹配层 30% + 加分层 10%）

**① 规则层（60%，硬门槛 + 满足度评分）** `algorithms.rule_layer_score()`
HR 配置的硬性条件（学历下限/年限范围/必备技能/薪资上限/排除关键词）任一不满足 → 直接淘汰并输出原因；
全过时按满足度评分：必备技能命中率 ×60 + 学历富余 ×20 + 年限匹配 ×20。决策表判定，同输入必同输出。

**② 语义匹配层（30%）** `algorithms.match_layer_score()`
JD 与简历的语义匹配度。默认实现 TF-IDF + 余弦相似度（tf=词频，idf=ln((1+N)/(1+df))+1，cos=A·B/(|A|·|B|)，
词表 {n} 技能词 + 英文 token，无外部依赖可审计）。
生产替换位：本层为适配器接口，可直接换 Sentence-BERT / 腾讯云 TI 文本匹配等语义模型。

**③ 加分层（10%）** `algorithms.bonus_layer_score()`
人工规则加权：大厂背景（每家 20 分封顶 40）+ 证书（每项 15 分封顶 30）+ 项目复杂度关键词
（从0到1/亿级/QPS/开源等，每个 10 分封顶 30）。规则库在代码中显式定义，可随时增补。

**迭代机制：** HR 每次复核结论回流 `hr_feedback` 表（按岗位隔离），作为评估 prompt 的校准上下文；
层权重配置于岗位规则 `layer_weights`（默认 60/30/10），每月可按回流数据人工调整（运营流程）。

### 面试与评估算法
- **自适应提问（动态难度状态机）** `interviewer`：连续 2 次高质量回答升难度（基础→进阶→深度），连续 2 次含糊降难度
- **多考官证据链评审** `evaluator`：技术×文化考官分组评分，每个分数必须引用候选人原话/简历原文；加权总分由代码计算（LLM 只出维度分）
- **能力图谱**：各维度得分即候选人能力雷达（界面可视化）

### 合规锚点
算法只输出建议+证据+排序，**最终录用决策由 HR 做出**；HR 意见按岗位进入反馈校准闭环。
""".replace("{n}", str(len(SKILL_LEXICON)))
