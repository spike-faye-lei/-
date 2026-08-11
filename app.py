"""招聘智能体 Demo：全自动演示 + 手动模式（岗位配置 · 证据链评分 · HR 人工审核闸门）
运行：双击 start.bat 或执行 python app.py，浏览器打开 http://localhost:7860
"""
import json
import os
import random
import time

import gradio as gr

from candidates import CANDIDATES
from candidate_bot import reply_stream as candidate_reply_stream
from crawler import fetch_gitee_seekers, fetch_jobs, fetch_seekers, match_profile
from db import get_interview, init_db, list_interviews, save_interview
from evaluator import evaluate, radar_figure
from file_parser import extract_text
from interviewer import STYLES, InterviewSession, is_finished, stream_first_message, stream_next_message
from job_profile import PROFILES, add_hr_feedback, get_profile
from resume_parser import format_resume_summary, parse_resume, pre_screen

init_db()  # 启动时初始化 SQLite

ASSETS = os.path.join(os.path.dirname(__file__), "assets")

COMPLIANCE = (
    "**【合规】** 已获得候选人授权同意，简历与对话数据仅用于本次招聘评估，"
    "存储于企业内网，候选人可随时要求删除（符合《个人信息保护法》要求）"
)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ===== 大赛级简约设计 token（参考 Awwwards 获奖作品：留白/单一强调色/hairline） ===== */
:root {
  --bg-page: #F5F4F0;        /* 暖米色页面底（有质感，非纯白） */
  --bg-panel: #FFFFFF;       /* 面板纯白 */
  --bg-hover: #EEEDE8;       /* hover 表面 */
  --bg-input: #FFFFFF;       /* 输入框 */
  --text-1: #1C1B1A;         /* 主文字近黑（带暖调） */
  --text-2: #5C5A55;         /* 次级文字 */
  --text-3: #A8A49C;         /* 占位/元信息 */
  --border-1: #E8E6E0;       /* hairline 细边（暖灰） */
  --border-2: #DAD7D0;       /* 略深细边 */
  --accent: #4F46E5;         /* 唯一强调色：indigo（点缀） */
  --ink: #1C1B1A;            /* 黑（主按钮） */
  --success: #16A34A; --danger: #DC2626; --warning: #D97706;
  --r-sm: 8px; --r-md: 10px; --r-lg: 14px;
}

body { background: var(--bg-page) !important; }

.gradio-container {
  max-width: 1320px !important; margin: 0 auto !important; padding: 24px 20px 40px !important;
  background: transparent !important;
  font-family: "Inter", -apple-system, "Segoe UI", "Noto Sans SC", "Microsoft YaHei", sans-serif !important;
  color: var(--text-1) !important;
  font-weight: 400;
}

/* 卡片：纯白 + hairline，无阴影无渐变——靠留白分层（大赛简约核心） */
.panel, .gr-box, .form, .wrap, .gr-group {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border-1) !important;
  border-radius: var(--r-md) !important;
  box-shadow: none !important;
  padding: 18px !important;
}
#left-col, #right-col { gap: 14px; }

/* 顶部横幅：白底 + indigo 左边条，大字号层级 */
#banner {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border-1) !important;
  border-left: 3px solid var(--accent) !important;
  border-radius: var(--r-lg) !important;
  padding: 22px 26px; margin-bottom: 16px;
  display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;
}
#banner h1 { margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.03em; color: var(--text-1); }
#banner p { margin: 5px 0 0; font-size: 12.5px; color: var(--text-3); }
#steps { display: flex; gap: 6px; flex-wrap: wrap; }
.step-chip {
  background: var(--bg-panel); border: 1px solid var(--border-1);
  border-radius: 999px; padding: 5px 13px; font-size: 11.5px; color: var(--text-2);
  font-variant-numeric: tabular-nums;
}

/* 按钮：黑色实心主按钮（大赛简约标志）+ 白底细边次按钮；绿/橙仅状态色 */
/* Gradio 6 的 elem_id 直接渲染在 button 元素上，选择器必须直接匹配 */
#auto-btn, #start-btn, #send-btn, #search-btn {
  background: var(--ink) !important;
  border: none !important; color: #fff !important; font-weight: 600; border-radius: var(--r-sm) !important;
  transition: background .15s ease, transform .1s ease !important;
  cursor: pointer;
}
#auto-btn:hover, #start-btn:hover, #send-btn:hover, #search-btn:hover { background: #000 !important; }
#auto-btn { background: var(--ink) !important; font-size: 14px; padding: 10px !important; }
#auto-btn:hover { background: #000 !important; }
#review-btn { background: var(--bg-panel) !important; color: var(--text-1) !important; border: 1px solid var(--border-2) !important; }
#review-btn:hover { background: var(--bg-hover) !important; }

/* 状态条：白底 hairline */
#status-bar {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border-1) !important; border-radius: var(--r-md) !important; padding: 10px 16px !important;
}
#status-bar p { margin: 0; font-size: 12.5px; color: var(--text-2); }

/* 聊天区：AI 白底细边 / 用户黑底白字（高对比极简） */
#chat { border-radius: var(--r-md) !important; background: var(--bg-panel) !important; border: 1px solid var(--border-1) !important; }
#chat .message.bot { background: var(--bg-panel) !important; border: 1px solid var(--border-1) !important; color: var(--text-1) !important; }
#chat .message.user { background: var(--ink) !important; color: #fff !important; }
#radar { border-radius: var(--r-md); background: var(--bg-panel); border: 1px solid var(--border-1); padding: 8px; }

/* 文字与表单控件：极简灰阶 */
.gradio-container label, .gradio-container .label, .gradio-container legend { color: var(--text-2) !important; font-weight: 500; }
.gradio-container h1, .gradio-container h2, .gradio-container h3, .gradio-container h4 { color: var(--text-1) !important; font-weight: 600 !important; }
.gradio-container input, .gradio-container textarea, .gradio-container select {
  background: var(--bg-input) !important; color: var(--text-1) !important;
  border: 1px solid var(--border-2) !important; border-radius: var(--r-sm) !important;
  font-size: 13px;
}
.gradio-container input::placeholder, .gradio-container textarea::placeholder { color: var(--text-3) !important; }
.gradio-container .selected { background: var(--bg-hover) !important; }
.gradio-container .tabs button { color: var(--text-2) !important; }
.footer { text-align: center; color: var(--text-3); font-size: 12px; margin-top: 10px; }
"""


def load_resume_file(file_obj, history, session_state):
    """上传简历文件 -> 解析文本填入简历框"""
    if file_obj is None:
        return None, session_state, "请上传简历文件"
    try:
        text = extract_text(file_obj.name)
        return text, session_state, f"已从 `{os.path.basename(file_obj.name)}` 提取文本，请核对后点击「开始招聘」"
    except Exception as e:
        return None, session_state, f"文件解析失败：{e}"


def search_candidate(label, history, session_state):
    """从简历库手动选择：把候选人简历填入输入框"""
    if not label:
        return None, session_state, "请先选择候选人"
    cand = next(c for c in CANDIDATES if c["label"] == label)
    return cand["resume"], session_state, f"已从 {cand['source']} 检索到候选人，点击「开始招聘」进入流程"


def start_interview(resume_text, profile_id, style_id, history, session_state):
    """手动模式：解析简历 -> 初筛 -> AI 主动联系（分阶段即时反馈 + 流式打字）"""
    if not resume_text or not resume_text.strip():
        yield history, None, _placeholder_radar(), "请先粘贴简历、上传文件或从简历库检索"
        return

    profile = get_profile(profile_id)
    base = [{"role": "assistant", "content": COMPLIANCE}]
    try:
        # 1) 立即反馈（不等待 API）
        yield [dict(m) for m in base], None, _placeholder_radar(), "① 正在解析简历……"
        resume = parse_resume(resume_text)
        base = base + [{"role": "assistant", "content": f"**【简历解析】**\n\n{format_resume_summary(resume)}"}]
        yield [dict(m) for m in base], None, _placeholder_radar(), "② 简历解析完成，正在自动初筛……"

        # 2) 初筛
        screen = pre_screen(resume)
        base = base + [{"role": "assistant", "content": f"**【自动初筛】**\n\n{screen}"}]
        session = InterviewSession(resume, profile, style=style_id)
        yield [dict(m) for m in base], session, _placeholder_radar(), "③ 初筛完成，AI 正在主动联系候选人……"

        # 3) AI 主动联系（流式打字）
        base = base + [{"role": "assistant", "content": "**【AI 主动联系】**\n\n"}]
        for partial, done in stream_first_message(session):
            base[-1]["content"] = f"**【AI 主动联系】**\n\n{partial}"
            yield [dict(m) for m in base], session, _placeholder_radar(), "AI 正在与候选人沟通……"
            if done:
                break
        yield [dict(m) for m in base], session, _placeholder_radar(), f"招聘进行中 —— AI 正在与候选人沟通（第 {session.round} 轮）"
    except Exception as e:
        yield history, None, _placeholder_radar(), f"启动失败：{e}"


def send_reply(user_input, history, session_state, plot_output):
    """手动模式：候选人回答 -> AI 流式推进 -> 结束后出报告+雷达图"""
    if session_state is None:
        yield history, session_state, plot_output, "请先添加简历并点击「开始招聘」"
        return
    if not user_input or not user_input.strip():
        yield history, session_state, plot_output, "请输入候选人回答"
        return

    plot_output = plot_output or _placeholder_radar()
    session = session_state
    hist = history + [{"role": "user", "content": user_input}]
    # 立即反馈：AI 思考占位（不等待 API）
    yield hist + [{"role": "assistant", "content": "（AI 思考中……）"}], session, plot_output, "AI 思考中……"
    try:
        # AI 流式回复（打字机效果，实时可见）
        reply = ""
        for partial, done in stream_next_message(session, user_input):
            reply = partial
            yield hist + [{"role": "assistant", "content": partial}], session, plot_output, "AI 回复中……"
            if done:
                break
        if is_finished(session, reply):
            report, fig = evaluate(session, session.profile)
            history = hist + [
                {"role": "assistant", "content": reply},
                {"role": "assistant", "content": report},
                {"role": "assistant", "content": "**报告已生成，等待 HR 在下方审核后发送最终决定**"},
            ]
            yield history, session, fig, "筛选完成 —— 请在下方进行 HR 审核"
            return
        yield hist + [{"role": "assistant", "content": reply}], session, plot_output, (
            f"招聘进行中（第 {session.round} 轮 · {session.style['name']}风格 · 追问难度：{session.difficulty_name}）"
        )
    except Exception as e:
        yield history, session_state, plot_output, f"调用失败：{e}"


def hr_review(decision, comment, history, session_state, plot_output):
    """HR 人工审核闸门：AI 不决定，人决定"""
    if session_state is None or session_state.report is None:
        return history, session_state, plot_output, "请先完成面试并生成报告，再提交审核"

    session = session_state
    data = session.report
    if decision.startswith("通过"):
        msg = (
            f"**【HR 审核】通过**\n\n"
            f"已向候选人发送线下面试邀约：\n\n{data.get('invite', '—')}\n\n"
            f"**HR 意见：** {comment or '（无）'}"
        )
    else:
        msg = (
            f"**【HR 审核】驳回**\n\n"
            f"已向候选人发送婉拒通知：\n\n{data.get('invite', '—')}\n\n"
            f"**HR 意见：** {comment or '（无）'}"
        )
    history = history + [{"role": "assistant", "content": msg}]
    verdict = "通过" if decision.startswith("通过") else "驳回"
    add_hr_feedback(verdict, comment)  # 反馈进入校准闭环，影响后续评估
    # 面试记录入库（历史可回看）
    candidate_name = session.resume.get("name", "候选人")
    report_text = "\n".join(
        m["content"] for m in history if "筛选决策报告" in m.get("content", "")
    )
    save_interview(candidate_name, "手动模式", session.profile["job"], session.style["name"], verdict, session.report.get("total"), comment, history, report_text)
    session.report = None  # 防重复审核
    return history, session, plot_output, "审核完成 —— HR 意见已进入反馈校准闭环，记录已存档"


def empty_radar_figure(profile: dict):
    """初始占位雷达图：界面一打开就显示（全 0 轮廓，等待评估）"""
    return radar_figure(
        profile,
        {d["name"]: 0 for d in profile["dimensions"]},
        tech_score=0, culture_score=0,
        tech_weight=sum(d["weight"] for d in profile["dimensions"] if d.get("reviewer") == "tech"),
        culture_weight=sum(d["weight"] for d in profile["dimensions"] if d.get("reviewer") == "culture"),
        total=0, decision="待评估",
    )



def _placeholder_radar():
    """缓存的占位雷达图：流式 yield 期间保持 Plot 不空（避免 Gradio 清空组件）"""
    if _PLACEHOLDER_RADAR.get("fig") is None:
        _PLACEHOLDER_RADAR["fig"] = empty_radar_figure(get_profile("ai-dev"))
    return _PLACEHOLDER_RADAR["fig"]


_PLACEHOLDER_RADAR = {}
def refresh_records():
    """刷新面试记录下拉列表"""
    records = list_interviews()
    if not records:
        return [], "暂无面试记录——跑一次流程后自动存档，重启不丢失"
    choices = [
        (f"{r['created_at']} · {r['candidate']} · {r['job']} · {r['decision']} · {r['score'] or '-'}分", r["id"])
        for r in records
    ]
    return choices, f"共 {len(records)} 条记录"


def show_record(record_id):
    """查看一条记录的详情（对话 + 报告）"""
    if not record_id:
        return "请选择一条记录"
    r = get_interview(record_id)
    if not r:
        return "记录不存在"
    try:
        chat = json.loads(r["chat"])
    except json.JSONDecodeError:
        chat = []
    lines = [
        f"### 面试记录 #{r['id']} · {r['candidate']}（{r['created_at']}）",
        "",
        f"- 岗位：{r['job']} ｜ 考官风格：{r['style']} ｜ 结论：**{r['decision']}** ｜ 总分：**{r['score'] or '-'}/10**",
        f"- 来源：{r['source']} ｜ HR 意见：{r['hr_comment'] or '（无）'}",
        "",
    ]
    for m in chat:
        role = "AI 招聘官" if m["role"] == "assistant" else "候选人"
        content = m["content"]
        lines.append(f"**{role}：** {content[:400]}")
        lines.append("")
    if r["report"]:
        lines += ["---", r["report"]]
    return "\n".join(lines)


def auto_demo(history, session_state, plot_output, demo_scope, use_crawler):
    """全自动演示：岗位采集（可选联网爬取）-> 候选人检索 -> 逐份初筛 -> 合适的自动互相聊天 -> 报告（全部入库）"""
    plot = _placeholder_radar()  # 流式期间保持雷达图不空
    want = 5 if demo_scope == "完整 5 人" else 3
    history = [{"role": "assistant", "content": COMPLIANCE}]
    yield history, session_state, plot, "全自动招聘演示启动……"

    # ---- 0. 岗位采集（爬虫：仅采集公开自愿发布信息，失败自动回退） ----
    profile = None
    CRAWL_ON = "联网爬取（V2EX 公开信息）"
    if use_crawler == CRAWL_ON:
        jobs = fetch_jobs(pages=5)  # 5 页 = 50 条公开招聘 JD；失败返回 []
        if jobs:
            top = jobs[0]
            pid = match_profile(f"{top['title']} {top['content']}")
            profile = get_profile(pid)
            samples = "\n".join(f"- {j['title']}" for j in jobs[:5])
            history = history + [{
                "role": "assistant",
                "content": (
                    f"**【岗位采集】（爬虫 · V2EX 公开信息）**\n\n"
                    f"从 V2EX 酷工作板块抓取 **{len(jobs)} 条公开招聘岗位**，示例：\n"
                    f"{samples}\n\n"
                    f"按 JD 关键词自动匹配岗位 rubric：**{profile['job']}**\n"
                    f"数据来源：{top['url']}"
                ),
            }]
            yield history, session_state, plot, "岗位采集完成，开始检索候选人……"
        else:
            profile = get_profile("ai-dev")
            history = history + [{
                "role": "assistant",
                "content": "**【岗位采集】** 网络不可用或 V2EX 无响应，已回退内置岗位配置（AI 应用开发工程师）",
            }]
            yield history, session_state, plot, "岗位采集失败，已回退内置岗位配置"
    else:
        profile = get_profile("ai-dev")

    # ---- 1. 候选人检索：Gitee 真实开发者 → V2EX 求职帖 → 内置简历库补齐 ----
    if use_crawler == CRAWL_ON:
        yield [dict(m) for m in history], session_state, plot, "正在检索候选人（Gitee 开发者档案 / V2EX 求职帖）……"
    candidates = []
    gitee_count = seek_count = 0
    if use_crawler == CRAWL_ON:
        gitee = fetch_gitee_seekers(limit=want)  # 真实开发者档案（每次关键词轮换，候选人不同）
        gitee_count = len(gitee)
        candidates += gitee
        seekers = fetch_seekers(limit=want)  # V2EX 公开求职帖（稀缺）
        seek_count = len(seekers)
        candidates += seekers
    candidates = candidates[:want]
    builtin_count = 0
    if len(candidates) < want:
        # 内置补齐：随机抽取（每次演示候选人不同，不固定顺序）
        pool = random.sample(CANDIDATES, min(len(CANDIDATES), want - len(candidates)))
        candidates += pool
        builtin_count = len(pool)
    if use_crawler == CRAWL_ON:
        history = history + [{
            "role": "assistant",
            "content": (
                f"**【候选人检索】** 共 **{len(candidates)} 位候选人**进入初筛\n\n"
                f"- 联网采集：Gitee 公开开发者 **{gitee_count} 条**（真实技术档案）\n"
                f"- 联网采集：V2EX 公开求职帖 **{seek_count} 条**"
                f"{'（该平台求职帖稀缺，属正常情况）' if seek_count == 0 else ''}\n"
                f"- 内置简历库补齐：**{builtin_count} 条**（演示数据）"
            ),
        }]
        yield history, session_state, plot, "候选人检索完成，开始逐份初筛……"

    for cand in candidates:
        name = cand["label"].split("·")[0].strip()
        # 2. 主动检索（附候选人档案）
        history = history + [{
            "role": "assistant",
            "content": (
                f"**【主动检索】**\n\n从 **{cand['source']}** 检索到候选人：**{name}**\n\n"
                f"**候选人档案：** {cand['profile']}\n\n{cand['resume'][:320]}"
            ),
        }]
        yield history, session_state, plot, f"正在初筛 {name}……"
        time.sleep(0.5)

        # 3. 解析 + 初筛
        try:
            resume = parse_resume(cand["resume"])
            screen = pre_screen(resume)
            history = history + [
                {"role": "assistant", "content": f"**【简历解析】**\n\n{format_resume_summary(resume)}"},
                {"role": "assistant", "content": f"**【自动初筛】**\n\n{screen}"},
            ]
            yield history, session_state, plot, f"初筛完成：{name}"

            if "低" in screen:
                history = history + [{"role": "assistant", "content": f"**【跳过】** **{name} 匹配度低，不进入沟通，自动跳过**"}]
                save_interview(name, cand["source"], profile["job"], "自动初筛跳过", "跳过", None, "", history, "")
                yield history, session_state, plot, f"{name} 已跳过（低匹配）"
                continue

            # 4. AI 互相聊天（流式：招聘官/候选人消息逐字出现）
            session = InterviewSession(resume, profile)
            history = history + [{"role": "assistant", "content": f"**【AI 招聘官】** → {name}\n\n"}]
            q = ""
            for partial, done in stream_first_message(session):
                q = partial
                history[-1]["content"] = f"**【AI 招聘官】** → {name}\n\n{partial}"
                yield [dict(m) for m in history], session_state, plot, f"{name}：AI 招聘官发言中……"
                if done:
                    break
            yield [dict(m) for m in history], session_state, plot, f"{name}：AI 互相聊天中……"

            while not is_finished(session, q):
                # 候选人 AI 流式回答
                history = history + [{"role": "user", "content": f"**{name}（候选人 AI）：**\n\n"}]
                answer = ""
                for partial in candidate_reply_stream(name, cand["resume"], session.history, q):
                    answer = partial
                    history[-1]["content"] = f"**{name}（候选人 AI）：**\n\n{partial}"
                    yield [dict(m) for m in history], session_state, plot, f"{name} 回答中……"
                yield [dict(m) for m in history], session_state, plot, f"{name} 回答完成……"

                # 招聘官流式回复
                history = history + [{"role": "assistant", "content": f"**AI 招聘官** → {name}\n\n"}]
                for partial, done in stream_next_message(session, answer):
                    q = partial
                    history[-1]["content"] = f"**AI 招聘官** → {name}\n\n{partial}"
                    yield [dict(m) for m in history], session_state, plot, f"{name}：AI 招聘官回复中……"
                    if done:
                        break
                if is_finished(session, q):
                    history[-1]["content"] = f"**AI 招聘官 · 收口** → {name}\n\n{q}"
                    yield [dict(m) for m in history], session_state, plot, f"{name}：AI 招聘官给出结论……"
                else:
                    yield [dict(m) for m in history], session_state, plot, f"{name}：AI 招聘官回复完成……"

            # 5. 决策报告 + 雷达图（自动入库）
            report, fig = evaluate(session, profile)
            plot = fig  # 保留本候选人雷达图（后续 yield 不清空）
            decision = session.report.get("decision", "通过")
            save_interview(name, cand["source"], profile["job"], session.style["name"], decision, session.report.get("total"), "", history, report)
            history = history + [
                {"role": "assistant", "content": f"**【筛选决策报告】** **{name}**\n\n{report}"},
                {"role": "assistant", "content": f"**{name} 的报告已提交 HR 审核**（可在下方人工审核）"},
            ]
            yield history, session, fig, f"{name} 处理完成 —— 待 HR 审核"
        except Exception as e:
            history = history + [{"role": "assistant", "content": f"处理 {name} 失败：{e}"}]
            yield history, session_state, plot, f"{name} 处理失败"

    yield history, session_state, plot, "**全自动招聘演示结束** —— 全部结果已存档，可在左侧「面试记录」回看"


with gr.Blocks(title="AI 招聘官") as demo:
    gr.HTML(
        """
        <div id="banner">
          <h1>AI 招聘官</h1>
          <p>全流程 AI 招聘智能体 ｜ 主动检索 · AI 互聊 · 证据链评分 · 人审闸门 ｜ Powered by DeepSeek</p>
          <div id="steps">
            <span class="step-chip">1 检索简历</span>
            <span class="step-chip">2 自动初筛</span>
            <span class="step-chip">3 AI 互相聊天</span>
            <span class="step-chip">4 多考官评分</span>
            <span class="step-chip">5 HR 审核邀约</span>
          </div>
        </div>
        """
    )

    with gr.Row(equal_height=False):
        # 左栏：模式与配置
        with gr.Column(scale=5, elem_id="left-col"):
            with gr.Group(elem_classes="panel"):
                gr.Markdown("### 全自动演示")
                gr.Markdown("AI 自己主动检索简历、判断合不合适、合适的直接开聊，全程无需操作，结果自动存档")
                with gr.Row():
                    scope_dropdown = gr.Dropdown(
                        choices=["快速 3 人（强/中/弱）", "完整 5 人"],
                        value="快速 3 人（强/中/弱）",
                        label="演示范围",
                        scale=4,
                    )
                    auto_btn = gr.Button("一键运行完整招聘流程", elem_id="auto-btn", variant="primary", scale=6)
                crawler_radio = gr.Radio(
                    choices=["联网爬取（V2EX 公开信息）", "离线演示（内置数据）"],
                    value="联网爬取（V2EX 公开信息）",
                    label="岗位与候选人采集",
                    info="联网模式：爬虫抓取 V2EX 酷工作公开招聘帖（PIPL 合规：仅采集自愿公开发布的信息），失败自动回退内置数据",
                )

            with gr.Group(elem_classes="panel"):
                gr.Markdown("### 岗位与考官配置")
                profile_dropdown = gr.Dropdown(
                    choices=[p["id"] for p in PROFILES],
                    value="ai-dev",
                    label="招聘岗位",
                    info="评估维度与权重按岗位定制，多考官分组评审",
                )
                style_dropdown = gr.Dropdown(
                    choices=[(s["name"], sid) for sid, s in STYLES.items()],
                    value="tech",
                    label="考官风格",
                    info="技术深挖：资深技术专家，追问细节验证深浅；压力面试：拷问式考察",
                )
                gr.Markdown("**动态难度：** 连续答好 → 问题升难度；连续答差 → 降难度（基础→进阶→深度）", elem_classes="footer")

            with gr.Group(elem_classes="panel"):
                gr.Markdown("### 手动模式")
                with gr.Tabs():
                    with gr.Tab("上传简历"):
                        resume_file = gr.File(
                            label="拖拽或点击上传（PDF / DOCX / TXT）",
                            file_types=[".pdf", ".docx", ".txt", ".md"],
                        )
                    with gr.Tab("简历库"):
                        candidate_dropdown = gr.Dropdown(
                            choices=[c["label"] for c in CANDIDATES],
                            label="选择候选人",
                        )
                        search_btn = gr.Button("检索该候选人", elem_id="search-btn", variant="primary")
                resume_input = gr.Textbox(
                    label="简历文本",
                    placeholder="上传/检索后自动填入，也可手动粘贴……",
                    lines=5,
                )
                start_btn = gr.Button("开始招聘（手动聊天）", elem_id="start-btn", variant="primary")

            with gr.Accordion("面试记录（历史存档）", open=False):
                with gr.Row():
                    record_dropdown = gr.Dropdown(
                        label="选择记录", choices=[], scale=8,
                        allow_custom_value=True,  # 服务重启后旧页面残留值不报错
                    )
                    refresh_btn = gr.Button("刷新", scale=2)
                record_detail = gr.Markdown("暂无面试记录——跑一次流程后自动存档，重启不丢失")

        # 右栏：演示区
        with gr.Column(scale=7, elem_id="right-col"):
            status = gr.Markdown("选择模式开始 —— 全自动演示或手动模式", elem_id="status-bar")
            chatbot = gr.Chatbot(
                label="招聘现场",
                height=560,
                avatar_images=(os.path.join(ASSETS, "avatar_user.svg"), os.path.join(ASSETS, "avatar_ai.svg")),
            )
            with gr.Row():
                answer_input = gr.Textbox(
                    label="手动模式：模拟候选人回答",
                    placeholder="手动模式下使用，自动演示无需输入……",
                    lines=2,
                    scale=8,
                )
                send_btn = gr.Button("发送", elem_id="send-btn", variant="primary", scale=2)

            radar_plot = gr.Plot(
                label="候选人能力雷达图",
                value=empty_radar_figure(get_profile("ai-dev")),  # 初始就显示占位图
            )

            with gr.Group(elem_classes="panel"):
                gr.Markdown("### HR 人工审核闸门")
                gr.Markdown("AI 只给建议和证据，**最终决定权在 HR**（AI 不决定，人决定）。HR 意见将进入**反馈校准闭环**，自动校准后续候选人评估（对标 Moka Eva）")
                with gr.Row():
                    review_radio = gr.Radio(
                        choices=["通过（进入线下面试）", "驳回"],
                        label="审核决定",
                        value="通过（进入线下面试）",
                        scale=4,
                    )
                    review_comment = gr.Textbox(label="HR 意见（可选）", placeholder="如：技术深度够，但期望薪资偏高……", lines=2, scale=6)
                review_btn = gr.Button("提交审核并发送最终决定", elem_id="review-btn", variant="primary")

    session_state = gr.State(None)

    # show_progress="hidden"：禁用 Gradio 默认 spinner 覆盖层（会遮挡招聘现场，看不见实时对话）
    auto_btn.click(
        auto_demo,
        inputs=[chatbot, session_state, radar_plot, scope_dropdown, crawler_radio],
        outputs=[chatbot, session_state, radar_plot, status],
        show_progress="hidden",
    )
    demo.load(refresh_records, outputs=[record_dropdown, record_detail], show_progress="hidden")
    refresh_btn.click(refresh_records, outputs=[record_dropdown, record_detail], show_progress="hidden")
    record_dropdown.change(show_record, inputs=record_dropdown, outputs=record_detail, show_progress="hidden")
    resume_file.change(
        load_resume_file,
        inputs=[resume_file, chatbot, session_state],
        outputs=[resume_input, session_state, status],
        show_progress="hidden",
    )
    search_btn.click(
        search_candidate,
        inputs=[candidate_dropdown, chatbot, session_state],
        outputs=[resume_input, session_state, status],
        show_progress="hidden",
    )
    start_btn.click(
        start_interview,
        inputs=[resume_input, profile_dropdown, style_dropdown, chatbot, session_state],
        outputs=[chatbot, session_state, radar_plot, status],
        show_progress="hidden",
    )
    send_btn.click(
        send_reply,
        inputs=[answer_input, chatbot, session_state, radar_plot],
        outputs=[chatbot, session_state, radar_plot, status],
        show_progress="hidden",
    )
    answer_input.submit(
        send_reply,
        inputs=[answer_input, chatbot, session_state, radar_plot],
        outputs=[chatbot, session_state, radar_plot, status],
        show_progress="hidden",
    )
    review_btn.click(
        hr_review,
        inputs=[review_radio, review_comment, chatbot, session_state, radar_plot],
        outputs=[chatbot, session_state, radar_plot, status],
        show_progress="hidden",
    )


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft(), css=CSS)
