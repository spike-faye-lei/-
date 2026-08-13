"""岗位配置（rubric）：评估维度、权重、考官分组、评分规则
演示时可切换岗位看报告变化；HR 审核意见会进入反馈校准闭环
"""
from db import add_hr_feedback_row, load_hr_feedback

# keywords：面试维度覆盖检查用（代码侧关键词归类招聘官提问，省一次 LLM 调用）
# 归类规则：按维度顺序第一个命中关键词的维度胜出（技术维度排前，软性维度兜底）
PROFILES = [
    {
        "id": "ai-dev",
        "job": "AI 应用开发工程师",
        "dimensions": [
            {"name": "技术能力", "weight": 40, "reviewer": "tech", "keywords": [
                "redis", "mysql", "docker", "k8s", "api", "qps", "tps", "并发", "缓存", "队列",
                "索引", "微服务", "faiss", "向量", "rag", "langchain", "prompt", "embedding",
                "召回", "分块", "重排", "分布式", "限流", "降级", "架构", "框架", "技术栈", "实现",
            ]},
            {"name": "项目经验", "weight": 30, "reviewer": "tech", "keywords": [
                "项目", "负责", "上线", "重构", "迭代", "业务", "需求", "效果", "收益", "经历", "做过",
            ]},
            {"name": "沟通表达", "weight": 20, "reviewer": "culture", "keywords": [
                "沟通", "协作", "表达", "团队", "冲突", "协调",
            ]},
            {"name": "求职意向", "weight": 10, "reviewer": "culture", "keywords": [
                "期望", "薪资", "到岗", "意向", "离职", "城市", "规划", "入职", "加班",
            ]},
        ],
        "rules": [
            "没有任何 AI/大模型相关经验时，技术能力不超过 5 分",
            "纯 CRUD 或纯增删改查项目，项目经验不超过 4 分",
            "回答含糊、空洞、只列要点不展开时，沟通表达必须扣分",
        ],
    },
    {
        "id": "backend",
        "job": "后端开发工程师",
        "dimensions": [
            {"name": "技术能力", "weight": 35, "reviewer": "tech", "keywords": [
                "java", "golang", "spring", "mysql", "redis", "kafka", "事务", "锁", "限流",
                "降级", "队列", "缓存", "jvm", "gc", "索引", "隔离级别", "实现", "技术栈",
            ]},
            {"name": "系统设计", "weight": 30, "reviewer": "tech", "keywords": [
                "设计", "方案", "架构", "扩展", "容量", "拆分", "一致性", "可用性", "分库分表", "高并发", "分布式",
            ]},
            {"name": "项目经验", "weight": 25, "reviewer": "tech", "keywords": [
                "项目", "负责", "上线", "业务", "效果", "经历", "做过",
            ]},
            {"name": "沟通表达", "weight": 10, "reviewer": "culture", "keywords": [
                "沟通", "协作", "表达", "团队", "冲突",
            ]},
        ],
        "rules": [
            "没有高并发/分布式相关经验时，系统设计不超过 5 分",
            "未涉及数据库设计或性能优化，项目经验不超过 5 分",
        ],
    },
    {
        "id": "frontend",
        "job": "前端开发工程师",
        "dimensions": [
            {"name": "技术能力", "weight": 35, "reviewer": "tech", "keywords": [
                "vue", "react", "typescript", "小程序", "css", "webpack", "vite", "组件",
                "性能优化", "渲染", "状态管理", "hooks", "实现",
            ]},
            {"name": "用户体验", "weight": 25, "reviewer": "culture", "keywords": [
                "交互", "体验", "设计", "可用性", "易用", "动效", "视觉", "无障碍", "适配",
            ]},
            {"name": "项目经验", "weight": 25, "reviewer": "tech", "keywords": [
                "项目", "负责", "上线", "业务", "效果", "经历",
            ]},
            {"name": "沟通表达", "weight": 15, "reviewer": "culture", "keywords": [
                "沟通", "协作", "表达", "团队", "冲突",
            ]},
        ],
        "rules": [
            "没有组件化/性能优化经验时，技术能力不超过 5 分",
            "仅套模板无自主设计能力时，用户体验不超过 4 分",
        ],
    },
]

REVIEWER_NAMES = {"tech": "技术考官", "culture": "文化考官"}

# HR 反馈校准闭环（Moka Eva 模式）：HR 审核意见会作为后续评估的校准依据
# 持久化到 SQLite（db.hr_feedback 表），重启不丢
HR_FEEDBACK = load_hr_feedback()


def get_profile(profile_id: str) -> dict:
    """按 id 取岗位配置，默认第一个"""
    for p in PROFILES:
        if p["id"] == profile_id:
            return p
    return PROFILES[0]


def add_hr_feedback(decision: str, comment: str, job: str = "") -> None:
    """HR 审核后记录反馈，进入校准闭环（内存 + SQLite 双写，带岗位便于隔离）"""
    if comment and comment.strip():
        item = {"decision": decision, "comment": comment.strip(), "job": job}
        HR_FEEDBACK.append(item)
        add_hr_feedback_row(decision, comment.strip(), job)
    if len(HR_FEEDBACK) > 60:
        HR_FEEDBACK.pop(0)


def classify_dimension(text: str, profile: dict):
    """把招聘官提问归类到岗位维度（关键词启发式，第一个命中维度胜出），未命中返回 None"""
    text = (text or "").lower()
    for dim in profile["dimensions"]:
        for kw in dim.get("keywords", []):
            if kw in text:
                return dim["name"]
    return None


def profile_summary(profile: dict) -> str:
    """岗位配置的中文摘要（展示给界面和评估 prompt）"""
    dims = "、".join(
        f"{d['name']}(权重{d['weight']}%, {REVIEWER_NAMES.get(d.get('reviewer'), '技术考官')})"
        for d in profile["dimensions"]
    )
    rules = "\n".join(f"- {r}" for r in profile["rules"])
    summary = f"招聘岗位：{profile['job']}\n评估维度：{dims}\n评分规则：\n{rules}"
    # 只注入本岗位的反馈（按 job 隔离，避免串岗校准污染）
    job_feedback = [f for f in HR_FEEDBACK if f.get("job") == profile["job"]]
    if job_feedback:
        recent = "\n".join(
            f"- HR审核[{f['decision']}]：{f['comment']}" for f in job_feedback[-3:]
        )
        summary += f"\n本岗位 HR 历史反馈（评估时参考这些校准意见，避免重复偏差）：\n{recent}"
    return summary
