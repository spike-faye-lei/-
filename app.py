"""招聘智能体 Demo：全自动演示 + 手动模式（岗位配置 · 证据链评分 · HR 人工审核闸门）
运行：双击 start.bat 或执行 python app.py，浏览器打开 http://localhost:7860
"""
import json
import os
import random
import re
import time

import gradio as gr

from bulk_screen import BATCH_LIMIT, screen_batch
from candidates import CANDIDATES
from candidate_bot import reply_stream as candidate_reply_stream
from compare import compare_report
from crawler import fetch_gitee_seekers, fetch_jobs, fetch_seekers, match_profile
from db import (
    add_batch_report,
    get_batch,
    get_hr_decision,
    get_interview,
    get_stats,
    init_db,
    list_batches,
    list_interviews,
    list_pending,
    list_screening_queue,
    save_interview,
    save_screening,
    screening_in_queue,
    set_invite,
    update_interview_hr,
    update_screening_hr,
)
from evaluator import evaluate, radar_figure
from file_parser import extract_text
from interviewer import STYLES, InterviewSession, is_finished, stream_first_message, stream_next_message
from jd_generator import generate_jd, generate_questions, jd_to_markdown, match_rubric_markdown
from job_profile import PROFILES, add_hr_feedback, get_profile
from resume_parser import format_resume_summary, parse_resume, pre_screen

init_db()  # 启动时初始化 SQLite

ASSETS = os.path.join(os.path.dirname(__file__), "assets")

COMPLIANCE = (
    "**【合规】** 演示环境仅使用公开信息与内置模拟数据；生产环境须获得候选人授权同意，"
    "简历与对话数据仅用于招聘评估、加密存储于企业内网，候选人可随时要求删除（《个人信息保护法》）"
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

/* ===== 强制浅色模式（Gradio 6 跟随系统深色模式会给 :root 加 .dark 类） =====
   系统深色模式下，主题 CSS 会把语义变量切到 neutral-900/950 深色值，
   导致 Tab 栏/下拉框/勾选组/表格/滚动条等原生组件变深，与自定义浅色 token 混搭。
   这里用同选择器把深色变量覆盖回浅色设计 token（用户 CSS 在主题 CSS 之后加载，必然生效）。 */
:root { color-scheme: light; }
:root.dark, :root .dark {
  color-scheme: light;
  --body-background-fill: var(--bg-page);
  --body-text-color: var(--text-1);
  --body-text-color-subdued: var(--text-2);
  --background-fill-primary: var(--bg-panel);
  --background-fill-secondary: var(--bg-page);
  --block-background-fill: var(--bg-panel);
  --panel-background-fill: var(--bg-panel);
  --border-color-primary: var(--border-2);
  --border-color-accent: var(--border-2);
  --border-color-accent-subdued: var(--border-1);
  --input-background-fill: var(--bg-input);
  --input-background-fill-focus: var(--bg-input);
  --input-background-fill-hover: var(--bg-input);
  --input-border-color: var(--border-2);
  --input-border-color-focus: var(--accent);
  --input-border-color-hover: var(--border-2);
  --input-placeholder-color: var(--text-3);
  --input-shadow: none;
  --input-shadow-focus: none;
  --checkbox-background-color: var(--bg-input);
  --checkbox-background-color-focus: var(--bg-input);
  --checkbox-background-color-hover: var(--bg-input);
  --checkbox-border-color: var(--border-2);
  --checkbox-border-color-focus: var(--accent);
  --checkbox-border-color-hover: var(--border-2);
  --checkbox-label-background-fill: var(--bg-input);
  --checkbox-label-background-fill-hover: var(--bg-hover);
  --checkbox-label-text-color: var(--text-1);
  --checkbox-label-text-color-selected: var(--text-1);
  --table-text-color: var(--text-1);
  --table-border-color: var(--border-1);
  --table-odd-background-fill: var(--bg-panel);
  --table-even-background-fill: var(--bg-hover);
  --table-row-focus: var(--bg-hover);
  --code-background-fill: var(--bg-hover);
  --stat-background-fill: var(--bg-hover);
  --accordion-text-color: var(--text-1);
  --block-title-text-color: var(--text-1);
  --block-label-text-color: #fff;
  --button-secondary-background-fill: var(--bg-input);
  --button-secondary-background-fill-hover: var(--bg-hover);
  --button-secondary-border-color: var(--border-2);
  --button-secondary-border-color-hover: var(--border-2);
  --button-secondary-text-color: var(--text-1);
  --button-secondary-text-color-hover: var(--text-1);
  --button-cancel-background-fill: var(--bg-input);
  --button-cancel-background-fill-hover: var(--bg-hover);
  --button-cancel-border-color: var(--border-2);
  --button-cancel-text-color: var(--text-1);
  --button-cancel-text-color-hover: var(--text-1);
  --link-text-color: var(--accent);
  --link-text-color-hover: var(--accent);
  --link-text-color-active: var(--accent);
  --link-text-color-visited: var(--accent);
  --error-background-fill: #fef2f2;
  --error-text-color: #dc2626;
  --shadow-spread: 0px;
  --loader-color: var(--accent);
}
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
    """HR 人工审核闸门：AI 不决定，人决定。审核后通知文本可编辑，确认发送才算数"""
    if session_state is None or session_state.report is None:
        return history, session_state, plot_output, "", None, "请先完成面试并生成报告，再提交审核"

    session = session_state
    data = session.report
    verdict = "通过" if decision.startswith("通过") else "驳回"
    invite = data.get("invite", "—")
    kind = "线下面试邀约" if verdict == "通过" else "婉拒通知"
    msg = (
        f"**【HR 审核】{verdict}**\n\n"
        f"AI 起草的{kind}已填入下方文本框（可编辑），确认后点击「确认发送」\n\n"
        f"**HR 意见：** {comment or '（无）'}"
    )
    history = history + [{"role": "assistant", "content": msg}]
    add_hr_feedback(verdict, comment, session.profile["job"])  # 反馈进入校准闭环（按岗位隔离）
    candidate_name = session.resume.get("name", "候选人")
    iid = getattr(session, "interview_id", None)
    if iid:
        # 自动面试记录已按「待HR审核」入库，这里回写 HR 结论（不新建，避免重复记录）
        update_interview_hr(iid, verdict, comment)
    else:
        # 手动模式：审核时才首次入库
        report_text = "\n".join(
            m["content"] for m in history if "筛选决策报告" in m.get("content", "")
        )
        iid = save_interview(candidate_name, "手动模式", session.profile["job"], session.style["name"], verdict, session.report.get("total"), comment, history, report_text)
    session.report = None  # 防重复审核
    pending = {"iid": iid, "verdict": verdict, "candidate": candidate_name}
    return history, session, plot_output, invite, pending, f"审核完成（{verdict}）—— 请确认通知文本后点击「确认发送」"


def confirm_invite(invite_text, history, session_state, plot_output, invite_state):
    """确认发送：邀约/婉拒文本回写存档"""
    if not invite_state:
        return history, session_state, plot_output, invite_text, invite_state, "没有待发送的通知 —— 请先提交 HR 审核"
    if not invite_text or not invite_text.strip():
        return history, session_state, plot_output, invite_text, invite_state, "通知文本为空 —— 请填写后发送"
    set_invite(invite_state["iid"], invite_text.strip())
    kind = "线下面试邀约" if invite_state["verdict"] == "通过" else "婉拒通知"
    history = history + [{
        "role": "assistant",
        "content": f"**【已发送】** {invite_state['candidate']} 的{kind}：\n\n{invite_text.strip()}",
    }]
    return history, session_state, plot_output, invite_text, None, f"{kind}已确认发送，记录已存档（可在「面试记录」回看）"


# ==================== 待审核队列：从库加载、逐条人工审核 ====================

def refresh_pending():
    """刷新待 HR 审核记录下拉列表（自动面试完成的候选人都在这里排队）"""
    rows = list_pending()
    choices = [
        (f"#{r['id']} {r['candidate']} · {r['job']} · {r['score'] or '-'}分", r["id"])
        for r in rows
    ]
    return choices


def _extract_invite(report_md: str) -> str:
    """从报告 markdown 提取 AI 起草的通知文本（邀约/婉拒）"""
    m = re.search(r"下一步（待 HR 审核确认后发送）：\*\*\s*(.+)", report_md or "")
    if m:
        return m.group(1).strip().split("\n**")[0].strip()
    return ""


def load_pending(record_id):
    """载入一条待审核记录：完整详情 + AI 通知草稿 + 审核状态（供提交/确认发送使用）"""
    if isinstance(record_id, (list, tuple)):
        record_id = record_id[0] if record_id else None
    if not record_id:
        return "请先选择待审核记录", "", None, "请先选择待审核记录"
    r = get_interview(record_id)
    if not r:
        return "记录不存在", "", None, "记录不存在"
    detail = show_record(record_id)
    invite = _extract_invite(r["report"] or "")
    state = {"iid": r["id"], "candidate": r["candidate"], "job": r["job"]}
    return detail, invite, state, f"已载入 **{r['candidate']}** —— 上方选择审核决定、填写意见后点「提交审核（待审核记录）」"


def submit_pending(decision, comment, invite_text, pending_state):
    """待审核记录的人工审核：回写结论 + 岗位反馈校准 + 通知草稿转交「确认发送」"""
    if not pending_state:
        return invite_text, None, None, "请先载入待审核记录"
    verdict = "通过" if decision.startswith("通过") else "驳回"
    update_interview_hr(pending_state["iid"], verdict, comment)
    add_hr_feedback(verdict, comment, pending_state["job"])
    new_invite_state = {"iid": pending_state["iid"], "verdict": verdict, "candidate": pending_state["candidate"]}
    kind = "线下面试邀约" if verdict == "通过" else "婉拒通知"
    return invite_text, new_invite_state, None, f"审核完成（{verdict}）—— AI 起草的{kind}已填入下方（可编辑），点击「确认发送」"


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
    # 新版 Gradio 的 Dropdown 值可能以 list/tuple 传入，取第一个元素
    if isinstance(record_id, (list, tuple)):
        record_id = record_id[0] if record_id else None
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


def _interview_candidate(name, source, resume_text, resume, profile, history, session_state, plot, batch_id=None):
    """对单个候选人跑完 AI 互相聊天 + 决策报告（generator）——全自动演示与一键面试共用

    调用方逐个消费 yield：(history, session, plot, status)；循环结束后 session 即最终会话（含 report）。
    结果自动入库（interviews + batch_reports）。
    """
    session = InterviewSession(resume, profile)
    start = len(history)  # 记录本候选人在累计 history 中的起点，入库时只存自己的切片
    history = history + [{"role": "assistant", "content": f"**【AI 招聘官】** → {name}\n\n"}]
    q = ""
    try:
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
            for partial in candidate_reply_stream(name, resume_text, session.history, q):
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

        # 决策报告 + 雷达图（入库：只存本候选人自己的对话切片）
        report, fig = evaluate(session, profile)
        iid = save_interview(name, source, profile["job"], session.style["name"], "待HR审核", session.report.get("total"), "", history[start:], report)
        session.interview_id = iid  # HR 审核时回写这条记录，而不是新建
        if batch_id:
            add_batch_report(batch_id, name, profile["job"], session.report.get("total", 0), session.report.get("decision", "待复核"), session.report.get("dimension_scores", {}))
        history = history + [
            {"role": "assistant", "content": f"**【筛选决策报告】** **{name}**\n\n{report}"},
            {"role": "assistant", "content": f"**{name} 的报告已提交 HR 审核**（AI 结论仅供建议，可在下方人工审核）"},
        ]
        yield history, session, fig, f"{name} 处理完成 —— 待 HR 审核"
    except Exception as e:
        history = history + [{"role": "assistant", "content": f"处理 {name} 失败：{e}"}]
        yield history, session, plot, f"{name} 处理失败"


def _entry_from_session(name, session):
    """从会话报告提取横向对比条目（无报告时返回 None）"""
    if session is None or not session.report:
        return None
    return {
        "name": name,
        "total": session.report.get("total", 0),
        "decision": session.report.get("decision", ""),
        "dimension_scores": session.report.get("dimension_scores", {}),
    }


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

    # ---- 2. 逐份初筛 → 自动互相聊天 → 报告（共用面试循环，批量入库，结束时横向对比） ----
    batch_id = time.strftime("%Y%m%d-%H%M%S")
    batch_entries = []
    for cand in candidates:
        name = cand["label"].split("·")[0].strip()
        cand_start = len(history)  # 本候选人在累计 history 中的起点（跳过记录也只存自己的切片）
        # 主动检索（附候选人档案）
        history = history + [{
            "role": "assistant",
            "content": (
                f"**【主动检索】**\n\n从 **{cand['source']}** 检索到候选人：**{name}**\n\n"
                f"**候选人档案：** {cand['profile']}\n\n{cand['resume'][:320]}"
            ),
        }]
        yield history, session_state, plot, f"正在初筛 {name}……"
        time.sleep(0.5)

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
                save_interview(name, cand["source"], profile["job"], "自动初筛跳过", "跳过", None, "", history[cand_start:], "")
                yield history, session_state, plot, f"{name} 已跳过（低匹配）"
                continue

            # AI 互相聊天 + 决策报告（与一键面试共用的面试循环）
            for h, sess, p, st in _interview_candidate(
                name, cand["source"], cand["resume"], resume, profile,
                history, session_state, plot, batch_id,
            ):
                history, session_state, plot = h, sess, p
                yield history, session_state, plot, st
            entry = _entry_from_session(name, session_state)
            if entry:
                batch_entries.append(entry)
        except Exception as e:
            history = history + [{"role": "assistant", "content": f"处理 {name} 失败：{e}"}]
            yield history, session_state, plot, f"{name} 处理失败"

    # ---- 3. 多人横向对比（≥2 人完成面试时生成） ----
    if len(batch_entries) >= 2:
        matrix, summary = compare_report(batch_entries, profile)
        history = history + [{
            "role": "assistant",
            "content": f"**【候选人横向对比】**（批次 {batch_id}）\n\n{matrix}\n\n{summary}",
        }]
        yield history, session_state, plot, "横向对比报告已生成（也可在「候选人对比」页查看历史批次）"

    yield history, session_state, plot, "**全自动招聘演示结束** —— 全部结果已存档，可在左侧「面试记录」回看"


# ==================== 批量简历初筛（AI 建议 + 人工复核闸门） ====================

def _collect_resumes(files, pasted_text):
    """收集待筛简历：多文件上传 + 粘贴文本（=== 分隔，每份第一行为姓名）→ [(name, source, text)]"""
    resumes = []
    for f in files or []:
        try:
            text = extract_text(f.name)
        except Exception:
            continue  # 单份解析失败跳过，不中断整批
        if text.strip():
            resumes.append((os.path.basename(f.name), "上传文件", text))
    for i, chunk in enumerate((pasted_text or "").split("==="), 1):
        chunk = chunk.strip()
        if not chunk:
            continue
        first_line = chunk.split("\n", 1)[0].strip()
        name = first_line[:20] if first_line else f"粘贴简历 {i}"
        resumes.append((name, "粘贴文本", chunk))
    return resumes


def run_bulk_screen(files, pasted_text, profile_id, progress=gr.Progress()):
    """批量初筛主流程（generator）：收集 → 逐份评分（带进度）→ 结果表 + 复核勾选项"""
    resumes = _collect_resumes(files, pasted_text)
    if not resumes:
        yield None, None, gr.update(choices=[], value=[]), "请上传简历文件，或在文本框中粘贴简历（多份用 === 分隔，每份第一行为姓名）"
        return
    truncated = len(resumes) > BATCH_LIMIT
    if truncated:
        resumes = resumes[:BATCH_LIMIT]
    profile = get_profile(profile_id)

    results = []
    for done, total, partial in screen_batch(resumes, profile):
        progress(done / total, desc=f"AI 评分中 {done}/{total}")
        yield None, None, gr.update(choices=[], value=[]), f"评分中 {done}/{total} 份……"
    results = partial

    rows, choices, by_label = [], [], {}
    for rank, r in enumerate(results, 1):
        if r.get("error"):
            rows.append([rank, r["name"], "评分失败", "—", r["error"], "—"])
            continue
        dims = "  ".join(f"{n} {s:.1f}" for n, s in r.get("dimension_scores", {}).items())
        rows.append([rank, r["name"], r.get("total", 0), r.get("decision", ""), r.get("comment", ""), dims])
        label = f"#{rank} {r['name']}（{r['total']}分 · {r.get('decision', '')}）"
        choices.append(label)
        by_label[label] = r
    note = f"共 {len(resumes)} 份完成初筛" + (f"（超出每批上限 {BATCH_LIMIT}，已截断）" if truncated else "")
    note += "。结果按总分降序，请在下表中勾选进入面试队列的候选人（人工复核：AI 只给建议，人决定）"
    state = {"results": results, "profile_id": profile_id, "by_label": by_label}
    yield rows, state, gr.update(choices=choices, value=[]), note


def send_to_queue(selected, screen_state):
    """人工复核：勾选通过初筛者 → screenings 落库（含简历原文 + hr_decision 回写）→ 队列从库中重建

    HR 复核状态持久化在 screenings.hr_decision，刷新/重启后队列不丢。
    """
    if not screen_state or not screen_state.get("by_label"):
        return [], "请先运行批量初筛", queue_markdown([])
    if not selected:
        return [], "请先勾选进入面试队列的候选人（人工复核是必须环节）", queue_markdown([])
    profile = get_profile(screen_state["profile_id"])
    count = skipped = 0
    for label in selected:
        r = screen_state["by_label"].get(label)
        if not r:
            continue
        if screening_in_queue(r["name"], profile["job"]):
            skipped += 1  # 已在队列中：防重复勾选产生重复面试
            continue
        sid = save_screening(
            r["name"], r.get("source", ""), profile["job"],
            r.get("dimension_scores", {}), r.get("total", 0), r.get("decision", ""),
            resume_text=r.get("resume_text", ""),
        )
        update_screening_hr(sid, "进入面试队列", "HR 人工复核通过")  # 复核结论真正落库
        count += 1
    queue = load_queue_from_db()
    note = f"已勾选 {count} 人通过初筛，HR 复核结论已存档" + (f"；{skipped} 人已在队列中自动跳过" if skipped else "")
    note += f"；面试队列共 {len(queue)} 人（刷新不丢），点击下方「一键面试队列」开始自动面试"
    return queue, note, queue_markdown(queue)


def load_queue_from_db():
    """从 screenings 表重建面试队列（持久化，重启/刷新后由页面加载恢复）"""
    rows = list_screening_queue()
    return [
        {
            "screening_id": r["id"],
            "name": r["candidate"],
            "source": r["source"] or "",
            "resume_text": r["resume"] or "",
            "total": r["total"] or 0,
        }
        for r in rows
    ]


def queue_markdown(queue):
    """队列展示文本（批量初筛页实时可见）"""
    if not queue:
        return "**当前面试队列：** 空 —— 勾选初筛结果后点「送入面试队列」"
    lines = [f"**当前面试队列（{len(queue)} 人）：**"]
    for i, q in enumerate(queue, 1):
        name = q["name"].rsplit(".txt", 1)[0] if ".txt" in q["name"] else q["name"]
        lines.append(f"{i}. **{name}** — 初筛 {q.get('total', 0)} 分")
    return "\n".join(lines)


def restore_queue():
    """页面加载时从库恢复面试队列 + 展示文本（刷新/重启不丢）"""
    queue = load_queue_from_db()
    return queue, queue_markdown(queue)


def run_queue_interviews(queue, profile_id, history, session_state, plot, progress=gr.Progress()):
    """一键面试（generator）：初筛通过队列 → 逐人自动面试 → 横向对比报告

    对话直播在本页（批量初筛）的「一键面试直播」框；结果全部入库，
    对比报告在「候选人对比」页可回看，HR 在「AI 面试官」页待审核队列逐条审核。
    """
    def emit(h, s, p, status):
        return h, s, p, status, queue_markdown(queue)

    if not queue:
        yield history, session_state, plot, "面试队列为空 —— 请先运行批量初筛并勾选候选人", queue_markdown(queue)
        return
    profile = get_profile(profile_id)
    batch_id = time.strftime("%Y%m%d-%H%M%S")
    entries = []
    history = history + [{
        "role": "assistant",
        "content": f"**【面试队列】** 初筛通过的 **{len(queue)} 位候选人**进入自动面试（岗位：{profile['job']} · 批次 {batch_id}）",
    }]
    yield emit(history, session_state, plot, "一键面试启动 —— 直播见上方对话框")

    total = len(queue)
    for i, item in enumerate(queue, 1):
        name = item["name"]
        progress((i - 1) / total, desc=f"面试中 {i}/{total}：{name}")
        history = history + [{
            "role": "assistant",
            "content": f"**【面试队列】** {i}/{total}：**{name}**（{item['source']} · 初筛 {item.get('total', 0)} 分，已通过 HR 复核）",
        }]
        yield emit(history, session_state, plot, f"{name}：进入面试……")
        try:
            resume = parse_resume(item["resume_text"])
            history = history + [{"role": "assistant", "content": f"**【简历解析】**\n\n{format_resume_summary(resume)}"}]
            yield emit(history, session_state, plot, f"{name}：简历解析完成")
            for h, sess, p, st in _interview_candidate(
                name, item["source"], item["resume_text"], resume, profile,
                history, session_state, plot, batch_id,
            ):
                history, session_state, plot = h, sess, p
                yield emit(history, session_state, plot, st)
            # 只有面试真正完成（记录已入库）才标记「已面试」；失败则留在队列可重试
            if getattr(session_state, "interview_id", None):
                update_screening_hr(item["screening_id"], "已面试", "自动面试完成")
                entry = _entry_from_session(name, session_state)
                if entry:
                    entries.append(entry)
            else:
                yield emit(history, session_state, plot, f"{name} 面试失败 —— 仍在队列中，可重试")
            queue = load_queue_from_db()  # 已面试者出队，队列展示实时更新
        except Exception as e:
            history = history + [{"role": "assistant", "content": f"处理 {name} 失败：{e}"}]
            yield emit(history, session_state, plot, f"{name} 处理失败 —— 仍在队列中，可重试")
            queue = load_queue_from_db()

    if len(entries) >= 2:
        matrix, summary = compare_report(entries, profile)
        history = history + [{
            "role": "assistant",
            "content": f"**【候选人横向对比】**（批次 {batch_id}）\n\n{matrix}\n\n{summary}",
        }]
    yield emit(history, session_state, plot, f"**面试队列全部完成** —— {len(entries)} 人已面试，对比报告已生成（「候选人对比」页可回看历史批次）")


def refresh_batches():
    """刷新面试批次下拉列表"""
    batches = list_batches()
    if not batches:
        return [], "暂无面试批次 —— 跑完一批面试（≥1 人完成报告）后自动存档"
    choices = [(f"{b['batch_id']} · {b['cnt']}人 · {b['created_at']}", b["batch_id"]) for b in batches]
    return choices, f"共 {len(batches)} 个批次"


def show_compare(batch_id):
    """从库中取一批面试的结构化结果，生成横向对比报告"""
    if isinstance(batch_id, (list, tuple)):  # 新版 Gradio Dropdown 值可能是 list
        batch_id = batch_id[0] if batch_id else None
    if not batch_id:
        return "请选择面试批次"
    rows = get_batch(batch_id)
    if not rows:
        return "批次不存在或为空"
    job = rows[0]["job"]
    profile = next((p for p in PROFILES if p["job"] == job), PROFILES[0])
    entries = []
    for r in rows:
        try:
            scores = json.loads(r["scores"] or "{}")
        except json.JSONDecodeError:
            scores = {}
        # 决策口径：HR 最终结论优先；未审核的显示 AI 建议（与面试记录保持一致）
        hr_decision = get_hr_decision(r["name"], job)
        decision = hr_decision if hr_decision else f"AI:{r['decision'] or ''}"
        entries.append({
            "name": r["name"],
            "total": r["total"] or 0,
            "decision": decision,
            "dimension_scores": scores,
        })
    matrix, summary = compare_report(entries, profile)
    return f"### 批次 {batch_id} · {job} · {len(entries)} 人（决策列：HR 结论优先，未审核为 AI 建议）\n\n{matrix}\n\n{summary}"


def run_jd_gen(role_name, notes):
    """JD 生成器：岗位名 + 要点 → 完整 JD + 岗位配置匹配"""
    if not role_name or not role_name.strip():
        return "请先填写岗位名称"
    try:
        jd = generate_jd(role_name.strip(), notes)
        return jd_to_markdown(jd) + "\n\n---\n\n" + match_rubric_markdown(jd)
    except Exception as e:
        return f"JD 生成失败：{e}"


def run_question_gen(profile_id, per_dim):
    """面试题生成器：按岗位维度生成分级题库"""
    profile = get_profile(profile_id)
    try:
        return generate_questions(profile, int(per_dim))
    except Exception as e:
        return f"题库生成失败：{e}"


def stats_markdown():
    """招聘数据看板（读库统计，不调 LLM）"""
    s = get_stats()
    jobs = "\n".join(f"- {j}：{c} 场" for j, c in s["jobs"]) or "- （暂无）"
    return (
        "### 招聘数据看板\n\n"
        f"| 指标 | 数值 |\n| --- | --- |\n"
        f"| 已出结论的面试 | **{s['total']}** 场 |\n"
        f"| 通过 | **{s['passed']}** 人 |\n"
        f"| 通过率 | **{s['pass_rate']}%** |\n"
        f"| 面试平均分 | **{s['avg_score'] if s['avg_score'] is not None else '—'}** |\n"
        f"| 批量初筛人次 | **{s['screened']}** |\n"
        f"| 已发送邀约/婉拒 | **{s['invited']}** 封 |\n\n"
        f"### 岗位分布\n\n{jobs}"
    )


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

    with gr.Tabs():
        with gr.Tab("AI 面试官"):
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
                            info="联网模式：仅采集平台公开自愿发布的信息，限速礼貌抓取，失败自动回退内置数据（仅用于功能演示，生产环境须接入官方授权接口）",
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
                        review_btn = gr.Button("提交审核（生成通知草稿）", elem_id="review-btn", variant="primary")
                        invite_input = gr.Textbox(
                            label="AI 起草的通知文本（可编辑，确认后发送）",
                            placeholder="提交审核后自动填入，可修改后再确认发送……",
                            lines=3,
                        )
                        send_invite_btn = gr.Button("确认发送", elem_id="review-btn", variant="primary")
                        gr.Markdown("---\n**待审核队列**：自动面试/批量面试的候选人按「待HR审核」入库，这里从库里载入逐条审核（不依赖当前会话）")
                        with gr.Row():
                            pending_dropdown = gr.Dropdown(
                                label="待审核记录", choices=[], scale=8,
                                allow_custom_value=True,  # 服务重启后旧页面残留值不报错
                            )
                            pending_refresh_btn = gr.Button("刷新", scale=2)
                        pending_load_btn = gr.Button("载入待审核记录", elem_id="search-btn", variant="primary")
                        pending_detail = gr.Markdown("")
                        pending_submit_btn = gr.Button("提交审核（待审核记录）", elem_id="review-btn", variant="primary")

        with gr.Tab("批量初筛"):
            with gr.Row(equal_height=False):
                with gr.Column(scale=5, elem_id="left-col"):
                    with gr.Group(elem_classes="panel"):
                        gr.Markdown("### 批量简历初筛")
                        gr.Markdown("上传/粘贴多份简历 → AI 逐份评分排序 → **人工勾选复核** → 送入面试队列（AI 只给建议，人决定）")
                        screen_profile = gr.Dropdown(
                            choices=[p["id"] for p in PROFILES],
                            value="ai-dev",
                            label="招聘岗位",
                            info="评分维度与权重按岗位配置（1000 份 = 分 50 批处理）",
                        )
                        screen_files = gr.File(
                            label="上传简历（PDF / DOCX / TXT，可多选）",
                            file_count="multiple",
                            file_types=[".pdf", ".docx", ".txt", ".md"],
                        )
                        screen_paste = gr.Textbox(
                            label="或粘贴多份简历（=== 分隔，每份第一行为姓名）",
                            lines=8,
                            placeholder="张三的简历\n张三，男，28岁，硕士……\n===\n李四的简历\n李四，女，25岁，本科……",
                        )
                        screen_btn = gr.Button(f"开始批量初筛（每批上限 {BATCH_LIMIT} 份）", elem_id="start-btn", variant="primary")
                    with gr.Group(elem_classes="panel"):
                        gr.Markdown("### 人工复核闸门")
                        gr.Markdown("勾选通过初筛的候选人 → 送入面试队列。**AI 只给评分建议，最终谁进面试由 HR 勾选决定**")
                        screen_check = gr.CheckboxGroup(label="初筛结果（勾选 = 进入面试队列）", choices=[])
                        queue_btn = gr.Button("送入面试队列", elem_id="search-btn", variant="primary")
                        queue_display = gr.Markdown("**当前面试队列：** 空")
                        queue_interview_btn = gr.Button("一键面试队列（AI 招聘官自动面试）", elem_id="auto-btn", variant="primary")
                        screen_status = gr.Markdown("等待运行初筛……", elem_id="status-bar")
                with gr.Column(scale=7, elem_id="right-col"):
                    queue_chatbot = gr.Chatbot(
                        label="一键面试直播（AI 招聘官 × 候选人 AI 实时对话）",
                        height=400,
                        avatar_images=(os.path.join(ASSETS, "avatar_user.svg"), os.path.join(ASSETS, "avatar_ai.svg")),
                    )
                    screen_table = gr.Dataframe(
                        headers=["排名", "姓名", "总分", "AI 建议", "一句话点评", "各维度得分"],
                        datatype=["number", "str", "number", "str", "str", "str"],
                        label="初筛结果（按总分降序）",
                        interactive=False,
                        wrap=True,
                    )

        with gr.Tab("候选人对比"):
            with gr.Group(elem_classes="panel"):
                gr.Markdown("### 候选人横向对比")
                gr.Markdown("选择一批面试 → 生成对比报告：各维度得分矩阵（代码计算，确定性）+ AI 推荐排序与综合评语")
                with gr.Row():
                    batch_dropdown = gr.Dropdown(
                        label="面试批次", choices=[], scale=8,
                        allow_custom_value=True,  # 服务重启后旧页面残留值不报错
                    )
                    batch_refresh_btn = gr.Button("刷新批次", scale=2)
                compare_btn = gr.Button("生成对比报告", elem_id="start-btn", variant="primary")
                compare_output = gr.Markdown("暂无对比报告 —— 选择批次后点击「生成对比报告」")

        with gr.Tab("招聘工具"):
            with gr.Row(equal_height=False):
                with gr.Column(scale=5, elem_id="left-col"):
                    with gr.Group(elem_classes="panel"):
                        gr.Markdown("### JD 生成器")
                        gr.Markdown("输入岗位名称与要点 → 生成完整 JD，并自动匹配内置岗位评估配置")
                        jd_role = gr.Textbox(label="岗位名称", placeholder="如：AI 应用开发工程师（初级）")
                        jd_notes = gr.Textbox(
                            label="岗位要点（可选）",
                            lines=4,
                            placeholder="如：做 RAG 知识库问答产品；需要 Python + LangChain；2 年以上经验",
                        )
                        jd_btn = gr.Button("生成 JD", elem_id="start-btn", variant="primary")
                        jd_output = gr.Markdown("生成的 JD 将显示在这里")
                    with gr.Group(elem_classes="panel"):
                        gr.Markdown("### 面试题生成器")
                        gr.Markdown("按岗位评估维度生成分级题库（基础/进阶/深度），供面试官参考")
                        with gr.Row():
                            q_profile = gr.Dropdown(
                                choices=[p["id"] for p in PROFILES],
                                value="ai-dev",
                                label="招聘岗位",
                                scale=6,
                            )
                            q_count = gr.Slider(1, 5, value=3, step=1, label="每维度题目数", scale=4)
                        q_btn = gr.Button("生成面试题库", elem_id="search-btn", variant="primary")
                        q_output = gr.Markdown("生成的题库将显示在这里")
                with gr.Column(scale=7, elem_id="right-col"):
                    with gr.Group(elem_classes="panel"):
                        gr.Markdown("### 招聘数据看板")
                        gr.Markdown("全部流程数据自动汇总（读库统计）：面试、初筛、邀约发送")
                        stats_refresh_btn = gr.Button("刷新看板", elem_id="search-btn", variant="primary")
                        stats_output = gr.Markdown("点击「刷新看板」查看统计")

    session_state = gr.State(None)
    screen_state = gr.State(None)   # 批量初筛本轮结果（含 by_label 反查）
    interview_queue = gr.State([])  # 初筛通过队列：[{screening_id, name, source, resume_text, total}]
    invite_state = gr.State(None)   # 待确认发送的通知：{iid, verdict, candidate}
    pending_state = gr.State(None)  # 待审核记录审核中：{iid, candidate, job}

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
        outputs=[chatbot, session_state, radar_plot, invite_input, invite_state, status],
        show_progress="hidden",
    )
    send_invite_btn.click(
        confirm_invite,
        inputs=[invite_input, chatbot, session_state, radar_plot, invite_state],
        outputs=[chatbot, session_state, radar_plot, invite_input, invite_state, status],
        show_progress="hidden",
    )
    # 待审核队列（从库加载，逐条审核；审核决定与意见复用上方的 radio/comment）
    demo.load(refresh_pending, outputs=[pending_dropdown], show_progress="hidden")
    pending_refresh_btn.click(refresh_pending, outputs=[pending_dropdown], show_progress="hidden")
    pending_load_btn.click(
        load_pending,
        inputs=[pending_dropdown],
        outputs=[pending_detail, invite_input, pending_state, status],
        show_progress="hidden",
    )
    pending_submit_btn.click(
        submit_pending,
        inputs=[review_radio, review_comment, invite_input, pending_state],
        outputs=[invite_input, invite_state, pending_state, status],
        show_progress="hidden",
    )
    # 批量初筛（带 gr.Progress 进度条，不用 hidden）
    screen_btn.click(
        run_bulk_screen,
        inputs=[screen_files, screen_paste, screen_profile],
        outputs=[screen_table, screen_state, screen_check, screen_status],
    )
    queue_btn.click(
        send_to_queue,
        inputs=[screen_check, screen_state],
        outputs=[interview_queue, screen_status, queue_display],
        show_progress="hidden",
    )
    # 页面加载/刷新时从库中恢复面试队列（HR 复核结论持久化，不丢）
    demo.load(restore_queue, outputs=[interview_queue, queue_display], show_progress="hidden")
    # 一键面试：对话直播在本页「一键面试直播」框，队列展示实时更新
    queue_interview_btn.click(
        run_queue_interviews,
        inputs=[interview_queue, screen_profile, queue_chatbot, session_state, radar_plot],
        outputs=[queue_chatbot, session_state, radar_plot, screen_status, queue_display],
    )
    # 候选人对比页
    demo.load(refresh_batches, outputs=[batch_dropdown, compare_output], show_progress="hidden")
    batch_refresh_btn.click(refresh_batches, outputs=[batch_dropdown, compare_output], show_progress="hidden")
    compare_btn.click(show_compare, inputs=[batch_dropdown], outputs=[compare_output], show_progress="hidden")
    # 招聘工具页
    jd_btn.click(run_jd_gen, inputs=[jd_role, jd_notes], outputs=[jd_output], show_progress="hidden")
    q_btn.click(run_question_gen, inputs=[q_profile, q_count], outputs=[q_output], show_progress="hidden")
    demo.load(stats_markdown, outputs=[stats_output], show_progress="hidden")
    stats_refresh_btn.click(stats_markdown, outputs=[stats_output], show_progress="hidden")


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft(), css=CSS)
