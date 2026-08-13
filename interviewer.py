"""AI 招聘智能体：主动沟通 -> 初聊 -> 技术深挖（资深技术专家考官，含糊必追问，动态难度）-> 收口邀约"""
import re

from config import chat, chat_stream
from job_profile import classify_dimension, profile_summary
from resume_parser import format_resume_summary

CHAT_ROUNDS = 2   # 前 2 轮：初聊（意向确认）
MAX_ROUNDS = 6    # 总沟通轮数

# 考官风格系统（借鉴 AiInterview 的风格矩阵）
STYLES = {
    "tech": {
        "name": "技术深挖",
        "persona": "你是「智聘科技」的资深技术专家（架构师级），不是普通 HR——你能听懂技术细节，对候选人的技术深浅判断极准",
        "tone": "专业严谨，聚焦技术细节",
        "followup": 2,
        "rules": [
            "候选人回答含糊、空洞、只列要点时，必须立即追问具体实现：怎么做的/用了什么技术/参数配置/量化指标",
            "多问技术选型取舍、难点攻克过程、效果量化",
            "候选人描述超出常理（如'QPS十万''毫秒级'）时，追问怎么测出来的、什么场景下测的",
            "听到技术名词要追问细节验证（如说'用了Redis'就追问：用来干什么？什么数据结构？为什么）",
        ],
    },
    "coach": {
        "name": "温和引导",
        "persona": "你是「智聘科技」的资深技术专家兼导师，既懂技术又善于让候选人放松表达",
        "tone": "友善鼓励，降低候选人紧张感",
        "followup": 2,
        "rules": [
            "回答不足时先肯定再引导补充（'思路是对的，能不能再展开说说当时怎么实现的'）",
            "候选人紧张卡壳时给提示，帮助其完整表达",
        ],
    },
    "stress": {
        "name": "压力面试",
        "persona": "你是「智聘科技」的技术面试官，采用高压快节奏的拷问式面试，考察候选人在压力下的技术真实水平",
        "tone": "节奏快，连续追问，语气略带挑战",
        "followup": 3,
        "rules": [
            "连续快速追问，专挑回答中的漏洞和矛盾处发问",
            "质疑候选人的技术结论（'你说优化了性能，但没提指标，怎么证明有效'）",
            "候选人口误或自相矛盾时立刻抓住",
        ],
    },
    "screen": {
        "name": "快速筛选",
        "persona": "你是「智聘科技」的资深技术专家，做第一轮快速技术筛选，问题精简高效",
        "tone": "简洁高效，直奔核心",
        "followup": 1,
        "rules": [
            "每题直奔核心技术点，不展开闲聊",
            "通过 2-3 个关键问题快速判断技术下限，含糊即淘汰",
        ],
    },
    "behavior": {
        "name": "行为面试",
        "persona": "你是「智聘科技」的资深技术专家，用 STAR 行为面试法考察候选人的真实经历与技术深度",
        "tone": "关注行为与动机，逻辑清晰",
        "followup": 2,
        "rules": [
            "多用 STAR 追问：情境-任务-行动-结果，验证候选人是否真正主导过项目",
            "追问具体角色（你个人做了什么 vs 团队做了什么）与可量化的结果",
        ],
    },
}

# 动态难度状态机（借鉴 AI_InterviewerAgent 连续答对/答错调整）
DIFFICULTY_LEVELS = ["基础", "进阶", "深度"]
DIFFICULTY_HINTS = {
    "基础": "问概念理解、工作职责、基础技术栈",
    "进阶": "问具体实现、技术选型、常见坑",
    "深度": "问方案取舍、性能瓶颈、量化指标、失败复盘",
}
VAGUE_PATTERNS = re.compile(r"不知道|记不清|忘了|不太清楚|没做过|不会|反正|差不多|大概|好像|没什么")
TECH_SIGNALS = re.compile(r"\d|redis|mysql|docker|k8s|api|qps|tps|并发|命中率|缓存|队列|索引|微服务|faiss|向量|rag|langchain|prompt|嵌入|embedding|召回|分块|重排|rerank|分布式|事务|限流|降级")

SYSTEM = """{persona}，正在主动与一名候选人沟通，推进完整招聘流程。
候选人简历：
{resume}

岗位要求与评分规则（你的提问要围绕这些维度考察）：
{profile}

当前阶段：{stage}（全部沟通共 {max} 轮，目前第 {round} 轮）
当前追问难度：{difficulty}（{difficulty_hint}）
面试风格：{tone}
维度覆盖情况：已考察 [{covered}]；尚未考察 [{uncovered}]

流程与规则：
1. 每轮只发 1 条消息，简洁、专业、用中文，不闲聊
2. 你负责主动推进流程，像真人招聘方一样引导对话
3. 「初聊」阶段（第 1-{chat} 轮）：确认候选人的求职意向、期望薪资、到岗时间，核对简历关键信息
4. 「技术面试」阶段（第 {chat}+1 轮起）：围绕简历项目深挖，按当前难度提问，追问技术实现、难点、量化指标
5. 追问铁律：候选人回答含糊、空洞、只列要点不展开时，必须立即追问具体细节；同一话题最多连续追问 {followup} 次，之后推进到下一个话题
6. 绝不重复提问已经问过的问题
7. 只能围绕候选人简历中真实存在的项目和技能提问，严禁编造简历中不存在的项目/技术来提问
8. 重要：如果本轮是最后一轮（第 {max} 轮），必须收口给出结果——消息以「【结论】」开头：通过则表达认可并发出线下面试邀约（含具体时间和地点），不通过则礼貌婉拒；绝对不能再提问
9. 永远不要说"我帮你评估"这类话，你就是招聘方
10. 维度覆盖：优先围绕「尚未考察」的维度提问，保证每个评估维度都被考察到；已考察维度可深挖但不要重复问相同问题

风格规则：
{style_rules}"""


class InterviewSession:
    """一次招聘沟通会话：简历、岗位、风格、难度、历史、轮次、报告"""

    def __init__(self, resume: dict, profile: dict, style: str = "tech"):
        self.resume = resume
        self.profile = profile
        self.style = STYLES.get(style, STYLES["tech"])
        self.history = []  # [{"role": "user"|"assistant", "content": ...}]
        self.round = 0
        self.report = None  # HR 审核用的评估结果数据
        # 动态难度状态
        self.difficulty = 0  # 0=基础 1=进阶 2=深度
        self._good_streak = 0
        self._bad_streak = 0
        # 维度覆盖跟踪：已考察的评估维度名集合
        self.covered_dims = set()

    def _mark_coverage(self, question: str) -> None:
        """把招聘官提问归类到评估维度（关键词启发式），记录已覆盖维度"""
        dim = classify_dimension(question, self.profile)
        if dim:
            self.covered_dims.add(dim)

    @property
    def stage(self) -> str:
        return "初聊" if self.round <= CHAT_ROUNDS else "技术面试"

    @property
    def difficulty_name(self) -> str:
        return DIFFICULTY_LEVELS[self.difficulty]

    def update_difficulty(self, answer: str) -> None:
        """连续答好升难度，连续答差降难度（启发式判断）"""
        is_bad = len(answer.strip()) < 20 or bool(VAGUE_PATTERNS.search(answer))
        is_good = len(answer.strip()) > 30 and bool(TECH_SIGNALS.search(answer))
        if is_bad:
            self._good_streak = 0
            self._bad_streak += 1
            if self._bad_streak >= 2 and self.difficulty > 0:
                self.difficulty -= 1
                self._bad_streak = 0
        elif is_good:
            self._bad_streak = 0
            self._good_streak += 1
            if self._good_streak >= 2 and self.difficulty < 2:
                self.difficulty += 1
                self._good_streak = 0
        else:
            self._good_streak = 0
            self._bad_streak = 0

    def _build_messages(self):
        dim_names = [d["name"] for d in self.profile["dimensions"]]
        covered = "、".join(d for d in dim_names if d in self.covered_dims) or "（暂无）"
        uncovered = "、".join(d for d in dim_names if d not in self.covered_dims) or "（已全覆盖）"
        messages = [
            {
                "role": "system",
                "content": SYSTEM.format(
                    persona=self.style["persona"],
                    resume=format_resume_summary(self.resume),
                    profile=profile_summary(self.profile),
                    stage=self.stage,
                    max=MAX_ROUNDS,
                    round=self.round + 1,  # 下一轮序号
                    difficulty=self.difficulty_name,
                    difficulty_hint=DIFFICULTY_HINTS[self.difficulty_name],
                    tone=self.style["tone"],
                    chat=CHAT_ROUNDS,
                    followup=self.style["followup"],
                    covered=covered,
                    uncovered=uncovered,
                    style_rules="\n".join(f"- {r}" for r in self.style["rules"]),
                ),
            }
        ]
        messages.extend(self.history[-8:])  # 只带最近 8 条消息（约 4 轮），控制 token 成本
        return messages


def first_message(session: InterviewSession) -> str:
    """AI 主动发出第一条消息：自我介绍 + 确认求职意向"""
    reply = chat(session._build_messages(), temperature=0.7)
    session.history.append({"role": "assistant", "content": reply})
    session.round += 1
    session._mark_coverage(reply)
    return reply


def stream_first_message(session: InterviewSession):
    """流式版 first_message：yield (partial, done)，done=True 时附带最终文本。

    yield (partial_text, False) 多次 → 最后 yield (final_text, True)
    """
    parts = []
    for chunk in chat_stream(session._build_messages(), temperature=0.7):
        parts.append(chunk)
        yield "".join(parts), False
    reply = "".join(parts)
    session.history.append({"role": "assistant", "content": reply})
    session.round += 1
    session._mark_coverage(reply)
    yield reply, True


CLOSING_PROMPT = """你是「智聘科技」的 AI 招聘智能体。与候选人的沟通已全部结束，这是最后一步，必须给出最终筛选结果。
【硬性要求】
1. 输出必须以「【结论】」开头，且只能写"通过"或"不通过"
2. 通过：发出线下面试邀约，写明具体时间和地点，欢迎语气
3. 不通过：礼貌婉拒，感谢候选人参与
4. 严禁提问、严禁寒暄、严禁输出其他任何内容"""


def next_message(session: InterviewSession, answer: str) -> str:
    """候选人回答后，AI 继续推进（先更新难度，再追问/换阶段/给结论）"""
    session.history.append({"role": "user", "content": answer})
    session.update_difficulty(answer)
    if session.round + 1 >= MAX_ROUNDS:
        # 最后一轮：切换收口 prompt（只保留最近几轮对话 + 强制结束指令），强制给出结论与面试邀约
        messages = [{"role": "system", "content": CLOSING_PROMPT}] + session.history[-6:]
        messages.append({"role": "user", "content": "【对话已结束】请现在输出最终筛选结果。"})
    else:
        messages = session._build_messages()
    reply = chat(messages, temperature=0.3 if session.round + 1 >= MAX_ROUNDS else 0.7)
    session.history.append({"role": "assistant", "content": reply})
    session.round += 1
    session._mark_coverage(reply)
    return reply


def is_finished(session: InterviewSession, reply: str) -> bool:
    """沟通是否结束：AI 给出结论或达到最大轮数"""
    return "【结论】" in reply or session.round >= MAX_ROUNDS


def stream_next_message(session: InterviewSession, answer: str):
    """流式版 next_message：先更新难度，再流式获取 AI 回复。

    yield (partial, done)，done=True 时附带最终回复文本（此时 history/round 已更新）。
    """
    session.history.append({"role": "user", "content": answer})
    session.update_difficulty(answer)
    if session.round + 1 >= MAX_ROUNDS:
        # 最后一轮：切换收口 prompt，强制给出结论与面试邀约
        messages = [{"role": "system", "content": CLOSING_PROMPT}] + session.history[-6:]
        messages.append({"role": "user", "content": "【对话已结束】请现在输出最终筛选结果。"})
        temp = 0.3
    else:
        messages = session._build_messages()
        temp = 0.7
    parts = []
    for chunk in chat_stream(messages, temperature=temp):
        parts.append(chunk)
        yield "".join(parts), False
    reply = "".join(parts)
    session.history.append({"role": "assistant", "content": reply})
    session.round += 1
    session._mark_coverage(reply)
    yield reply, True
