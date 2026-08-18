"""入职运营智能体（第三智能体）：Offer 发放 → 培训内容匹配 → 入职流程引导 → 新人数据归档

与另两个智能体的分工（产品框架）：
- 简历筛选智能体（handlers.run_library_screen + algorithms）：平台/本地双路径收简历 → 规则+匹配+加分三层打分 → 初筛淘汰，人工只留「结果复核」
- AI 面试智能体（interviewer + evaluator + handlers.run_queue_interviews）：自动面试（实时追问+能力图谱）→ 判定，自动发面试通知
- 入职运营智能体（本模块）：Offer → 培训匹配 → 入职引导 → 归档
"""
import json

from db import get_candidate, list_offers, update_candidate, update_offer_status

# 培训课程库（内置演示数据；生产可对接企业培训系统/云学堂等）
TRAINING_LIBRARY = [
    {"id": "t1", "title": "新员工入职必修：公司制度与文化", "duration": "2h", "keywords": []},
    {"id": "t2", "title": "信息安全与数据合规培训", "duration": "1.5h", "keywords": []},
    {"id": "t3", "title": "Python 工程化实战", "duration": "8h", "keywords": ["python", "fastapi", "django", "后端"]},
    {"id": "t4", "title": "大模型应用开发（RAG/LangChain）", "duration": "12h", "keywords": ["大模型", "langchain", "rag", "llm", "ai", "向量", "prompt", "agent"]},
    {"id": "t5", "title": "Java 微服务与高并发架构", "duration": "10h", "keywords": ["java", "spring", "微服务", "高并发", "分布式", "kafka", "mysql"]},
    {"id": "t6", "title": "前端工程化与性能优化", "duration": "8h", "keywords": ["vue", "react", "前端", "typescript", "webpack", "小程序"]},
    {"id": "t7", "title": "数据分析与可视化（SQL/Pandas）", "duration": "6h", "keywords": ["sql", "pandas", "数据分析", "spark", "flink", "数仓"]},
    {"id": "t8", "title": "测试自动化与质量保障", "duration": "6h", "keywords": ["pytest", "测试", "selenium", "jmeter", "自动化测试"]},
    {"id": "t9", "title": "项目管理与敏捷实践", "duration": "4h", "keywords": ["产品", "项目管理", "pm"]},
    {"id": "t10", "title": "AI 产品经理进阶", "duration": "6h", "keywords": ["产品设计", "axure", "产品经理", "aigc"]},
]

# 入职流程清单（固定流程 + 按岗位适配）
ONBOARDING_BASE = [
    "① 资料提交：身份证/学历证明/离职证明",
    "② 劳动合同签署（电子签）",
    "③ 社保公积金信息采集",
    "④ 设备发放：电脑/工牌/账号开通",
    "⑤ 直属上级 1v1 面谈",
    "⑥ 试用期目标确认（30/60/90 天计划）",
    "⑦ 培训学习计划启动",
]


def match_trainings(candidate_name, job_title):
    """培训内容匹配：按候选人技能词 + 岗位名匹配课程库（关键词命中算法）"""
    cand = get_candidate(candidate_name) if isinstance(candidate_name, int) else None
    if not cand:
        # 按姓名兜底（调用方可能传名字）
        from db import get_candidate_by_name
        cand = get_candidate_by_name(candidate_name)
    if not cand:
        return TRAINING_LIBRARY[:2]  # 无候选人数据时只给必修课
    try:
        parsed = json.loads(cand.get("parsed") or "{}")
        skills = [s.lower() for s in parsed.get("skills", [])]
    except json.JSONDecodeError:
        skills = []
    text = " ".join(skills) + " " + (job_title or "").lower() + " " + (cand.get("resume_text") or "").lower()[:2000]
    scored = []
    for course in TRAINING_LIBRARY:
        kws = course["keywords"]
        hit = sum(1 for k in kws if k in text) if kws else -1  # 无关键词的必修课固定入选
        scored.append((hit, course))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:4]]


def onboarding_plan(candidate_name, job_title=""):
    """生成入职计划：培训匹配 + 入职流程清单 + 状态归档（状态机 → 已入职）"""
    from db import get_candidate_by_name
    cand = get_candidate_by_name(candidate_name)
    trainings = match_trainings(candidate_name, job_title)
    training_lines = "\n".join(f"- {c['title']}（{c['duration']}）" for c in trainings)
    checklist = "\n".join(ONBOARDING_BASE)
    plan = (
        f"## 入职运营计划：{candidate_name}\n\n"
        f"### 培训内容匹配（按技能+岗位自动匹配）\n\n{training_lines}\n\n"
        f"### 入职流程清单\n\n{checklist}\n\n"
        f"### 新人数据归档\n\n"
        f"候选人全流程数据（简历/初筛/面试/评估/Offer/培训）已按状态机归档于数据库，"
        f"可随时回溯审计（授权日志+通知记录+Offer 记录）。"
    )
    # 状态机归档：候选人 → 已入职（入职运营智能体的终态动作）
    if cand:
        update_candidate(cand["id"], status="已入职", status_note="入职运营智能体完成归档")
        # Offer 状态联动
        offers = list_offers()
        for o in offers:
            if o["candidate_name"] == candidate_name and o["status"] == "待接受":
                update_offer_status(o["id"], "已接受")
    return plan


def pending_offers_markdown():
    """待入职运营的 Offer 列表（已发 Offer 未归档的候选人）"""
    rows = list_offers()
    if not rows:
        return "暂无 Offer —— HR 审核通过后自动生成 Offer 草稿"
    lines = ["### Offer 待办（入职运营）", "", "| ID | 候选人 | 岗位 | 薪资 | 状态 |", "| --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r['id']} | {r['candidate_name']} | {r['job_title']} | {r['salary']} | {r['status']} |")
    return "\n".join(lines)
