"""岗位配置（rubric）：评估维度、权重、考官分组、评分规则
演示时可切换岗位看报告变化；HR 审核意见会进入反馈校准闭环
"""
PROFILES = [
    {
        "id": "ai-dev",
        "job": "AI 应用开发工程师",
        "dimensions": [
            {"name": "技术能力", "weight": 40, "reviewer": "tech"},
            {"name": "项目经验", "weight": 30, "reviewer": "tech"},
            {"name": "沟通表达", "weight": 20, "reviewer": "culture"},
            {"name": "求职意向", "weight": 10, "reviewer": "culture"},
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
            {"name": "技术能力", "weight": 35, "reviewer": "tech"},
            {"name": "系统设计", "weight": 30, "reviewer": "tech"},
            {"name": "项目经验", "weight": 25, "reviewer": "tech"},
            {"name": "沟通表达", "weight": 10, "reviewer": "culture"},
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
            {"name": "技术能力", "weight": 35, "reviewer": "tech"},
            {"name": "用户体验", "weight": 25, "reviewer": "culture"},
            {"name": "项目经验", "weight": 25, "reviewer": "tech"},
            {"name": "沟通表达", "weight": 15, "reviewer": "culture"},
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
from db import add_hr_feedback_row, load_hr_feedback

HR_FEEDBACK = load_hr_feedback()


def get_profile(profile_id: str) -> dict:
    """按 id 取岗位配置，默认第一个"""
    for p in PROFILES:
        if p["id"] == profile_id:
            return p
    return PROFILES[0]


def add_hr_feedback(decision: str, comment: str) -> None:
    """HR 审核后记录反馈，进入校准闭环（内存 + SQLite 双写）"""
    if comment and comment.strip():
        item = {"decision": decision, "comment": comment.strip()}
        HR_FEEDBACK.append(item)
        add_hr_feedback_row(decision, comment.strip())
    if len(HR_FEEDBACK) > 6:
        HR_FEEDBACK.pop(0)


def profile_summary(profile: dict) -> str:
    """岗位配置的中文摘要（展示给界面和评估 prompt）"""
    dims = "、".join(
        f"{d['name']}(权重{d['weight']}%, {REVIEWER_NAMES.get(d.get('reviewer'), '技术考官')})"
        for d in profile["dimensions"]
    )
    rules = "\n".join(f"- {r}" for r in profile["rules"])
    summary = f"招聘岗位：{profile['job']}\n评估维度：{dims}\n评分规则：\n{rules}"
    if HR_FEEDBACK:
        recent = "\n".join(
            f"- HR审核[{f['decision']}]：{f['comment']}" for f in HR_FEEDBACK[-3:]
        )
        summary += f"\nHR 历史反馈（评估时参考这些校准意见，避免重复偏差）：\n{recent}"
    return summary
