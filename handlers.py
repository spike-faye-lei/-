"""Gradio 事件处理函数：AI 面试官 / 批量初筛 / 候选人对比 / 招聘工具的全部业务接线

纯函数 + generator：不持有界面组件引用，所有状态经参数传入传出（便于测试与复用）。
"""
import json
import os
import random
import re
import time

import gradio as gr

from algorithms import (
    ALGORITHM_DOC,
    bonus_layer_score,
    check_rules,
    composite_score,
    extract_fields,
    match_layer_score,
    rule_layer_score,
    tfidf_similarity,
)
from bulk_screen import BATCH_LIMIT, screen_batch, screen_resume
from candidates import CANDIDATES
from candidate_bot import reply_stream as candidate_reply_stream
from compare import compare_report
from config import chat
from crawler import fetch_gitee_seekers, fetch_jobs, fetch_seekers, match_profile
from db import (
    RESUME_DIR,
    add_batch_report,
    add_candidate,
    cleanup_old_score_cards,
    create_batch_task,
    find_unfinished_interview,
    funnel_stats,
    get_batch,
    get_batch_task,
    get_candidate,
    get_candidate_by_name,
    get_hr_decision,
    get_interview,
    get_job_profile,
    get_latest_job_style,
    get_score_card,
    get_stats,
    list_batch_tasks,
    list_batches,
    list_candidates,
    list_interviews,
    list_job_profiles,
    list_notifications,
    list_offers,
    list_pending,
    list_screening_queue,
    list_hotword_suggestions,
    load_session_state,
    mark_notification_sent,
    record_approval,
    record_performance,
    save_hotword_suggestion,
    save_interview,
    save_session_state,
    save_job_profile,
    save_notification,
    save_offer,
    save_score_card,
    save_screening,
    screening_in_queue,
    search_candidates,
    set_invite,
    update_batch_task,
    update_candidate,
    update_interview_hr,
    update_interview_result,
    update_screening_hr,
)
from notify_channels import notify as channel_notify
from notify_channels import screening_done_message
from evaluator import evaluate, radar_figure
from file_parser import extract_text
from interviewer import STYLES, InterviewSession, is_finished, stream_first_message, stream_next_message
from jd_generator import generate_jd, generate_questions, jd_to_markdown, match_rubric_markdown
from job_profile import PROFILES, add_hr_feedback, get_profile
from onboarding import onboarding_plan, pending_offers_markdown
from resume_parser import format_resume_summary, parse_resume, pre_screen
from ui_theme import COMPLIANCE


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
    """手动模式：候选人回答 -> AI 流式推进 -> 结束后出报告+雷达图（并把审核单选默认值设为 AI 决策）"""
    if session_state is None:
        yield history, session_state, plot_output, gr.update(), "请先添加简历并点击「开始招聘」"
        return
    if not user_input or not user_input.strip():
        yield history, session_state, plot_output, gr.update(), "请输入候选人回答"
        return

    plot_output = plot_output or _placeholder_radar()
    session = session_state
    hist = history + [{"role": "user", "content": user_input}]
    # 立即反馈：AI 思考占位（不等待 API）
    yield hist + [{"role": "assistant", "content": "（AI 思考中……）"}], session, plot_output, gr.update(), "AI 思考中……"
    try:
        # AI 流式回复（打字机效果，实时可见）
        reply = ""
        for partial, done in stream_next_message(session, user_input):
            reply = partial
            yield hist + [{"role": "assistant", "content": partial}], session, plot_output, gr.update(), "AI 回复中……"
            if done:
                break
        if is_finished(session, reply):
            report, fig = evaluate(session, session.profile)
            history = hist + [
                {"role": "assistant", "content": reply},
                {"role": "assistant", "content": report},
                {"role": "assistant", "content": "**报告已生成，等待 HR 在下方审核后发送最终决定**"},
            ]
            # 审核单选默认值跟随 AI 决策（HR 可改，AI 只建议）
            radio = gr.update(value=_radio_value(session.report.get("decision", "")))
            yield history, session, fig, radio, "筛选完成 —— 请在下方进行 HR 审核"
            return
        yield hist + [{"role": "assistant", "content": reply}], session, plot_output, gr.update(), (
            f"招聘进行中（第 {session.round} 轮 · {session.style['name']}风格 · 追问难度：{session.difficulty_name}）"
        )
    except Exception as e:
        yield history, session_state, plot_output, gr.update(), f"调用失败：{e}"


def hr_review(decision, comment, history, session_state, plot_output):
    """HR 人工审核闸门：AI 不决定，人决定。审核后通知文本可编辑，确认发送才算数"""
    if session_state is None or session_state.report is None:
        return history, session_state, plot_output, "", None, "请先完成面试并生成报告，再提交审核"

    session = session_state
    data = session.report
    verdict = "通过" if decision.startswith("通过") else "驳回"
    invite = data.get("invite", "—")
    note = ""
    # 一致性守卫：HR 结论与 AI 决策相反时，草稿是反方向的话术，必须按 HR 结论重新起草
    if _verdict_mismatch(verdict, data.get("decision")):
        invite = _redraft_invite(verdict)
        note = f"\n\n> ⚠️ AI 建议为「{data.get('decision', '?')}」，与您的结论相反，通知已按您的结论重新起草，请核对后再发送"
    kind = "线下面试邀约" if verdict == "通过" else "婉拒通知"
    msg = (
        f"**【HR 审核】{verdict}**\n\n"
        f"AI 起草的{kind}已填入下方文本框（可编辑），确认后点击「确认发送」{note}\n\n"
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
    # 全流程联动：候选人状态机 + 通知/Offer 自动生成（HR 审核即触发，无需人工逐项操作）
    nid = _link_candidate_flow(candidate_name, session.profile["job"], verdict, invite)
    pending = {"iid": iid, "verdict": verdict, "candidate": candidate_name, "nid": nid}
    return history, session, plot_output, invite, pending, f"审核完成（{verdict}）—— 请确认通知文本后点击「确认发送」"


def _link_candidate_flow(candidate_name, job, verdict, invite_text):
    """HR 审核联动：候选人状态机推进 + 通知入库 + 通过时自动生成 Offer 草稿。

    找不到候选人记录时静默跳过（手动模式的内置候选人可能不在 candidates 表）。
    返回通知记录 id（确认发送后回写已发送）。
    """
    cand = get_candidate_by_name(candidate_name)
    if not cand:
        return None
    ntype = "面试邀约" if verdict == "通过" else "婉拒通知"
    update_candidate(cand["id"], status="HR通过" if verdict == "通过" else "HR驳回")
    nid = save_notification(cand["id"], candidate_name, ntype, invite_text or "")
    if verdict == "通过":
        # 自动生成 Offer 草稿：薪资取候选人期望区间低值（代码侧解析字段），无则面议
        try:
            parsed = json.loads(cand.get("parsed") or "{}")
            sal = parsed.get("expected_salary")
            salary = f"{sal[0]:.0f}K" if sal else "面议"
        except (json.JSONDecodeError, TypeError, IndexError):
            salary = "面议"
        save_offer(cand["id"], candidate_name, job, salary)
    return nid


def confirm_invite(invite_text, channel, history, session_state, plot_output, invite_state):
    """确认发送：邀约/婉拒文本回写存档 + 通知渠道与状态回写 + 候选人状态机推进

    channel：企业微信 / 短信 / 邮件 / 站内信（本地为模拟发送，记录渠道与发送日志；
    生产环境在此对接企业微信机器人/短信服务商 API——见 docs/02 平台对接方案）。
    """
    if not invite_state:
        return history, session_state, plot_output, invite_text, invite_state, "没有待发送的通知 —— 请先提交 HR 审核"
    if not invite_text or not invite_text.strip():
        return history, session_state, plot_output, invite_text, invite_state, "通知文本为空 —— 请填写后发送"
    set_invite(invite_state["iid"], invite_text.strip())
    if invite_state.get("nid"):
        mark_notification_sent(invite_state["nid"], channel or "邮件")
    cand = get_candidate_by_name(invite_state["candidate"], status="HR通过" if invite_state["verdict"] == "通过" else "HR驳回")
    if cand:
        update_candidate(cand["id"], status="已发通知")
    kind = "线下面试邀约" if invite_state["verdict"] == "通过" else "婉拒通知"
    # 外部渠道推送（钉钉/飞书/企业微信群机器人）：HR 不用打开网页也能收到结果
    push_result = ""
    if channel in ("钉钉", "飞书", "企业微信"):
        push_result = channel_notify(channel, f"【AI 招聘】{invite_state['candidate']} 的{kind}已确认发送，全文见系统记录。")
    history = history + [{
        "role": "assistant",
        "content": f"**【已发送】** {invite_state['candidate']} 的{kind}（渠道：{channel or '邮件'}）：\n\n{invite_text.strip()}\n\n{push_result}",
    }]
    return history, session_state, plot_output, invite_text, None, f"{kind}已通过「{channel or '邮件'}」发送，发送日志已存档（全流程看板可查）"


# ==================== 待审核队列：从库加载、逐条人工审核 ====================

def refresh_pending():
    """刷新待 HR 审核记录下拉列表（自动面试完成的候选人都在这里排队，含超时提示）"""
    from datetime import datetime
    now = datetime.now()
    choices = []
    for r in list_pending():
        try:
            created = datetime.strptime(r.get("created_at") or "", "%Y-%m-%d %H:%M")
            hours = max(0, (now - created).total_seconds() / 3600)
            overdue = f" ⏰待审{hours:.0f}小时" if hours >= 24 else ""
        except (ValueError, TypeError):
            overdue = ""
        choices.append((f"#{r['id']} {r['candidate']} · {r['job']} · {r['score'] or '-'}分{overdue}", r["id"]))
    return choices


def _extract_invite(report_md: str) -> str:
    """从报告 markdown 提取 AI 起草的通知文本（邀约/婉拒）"""
    m = re.search(r"下一步（待 HR 审核确认后发送）：\*\*\s*(.+)", report_md or "")
    if m:
        return m.group(1).strip().split("\n**")[0].strip()
    return ""


def _extract_decision(report_md: str) -> str:
    """从报告 markdown 提取 AI 的筛选决策（通过/不通过，取不到返回空串）"""
    m = re.search(r"筛选决策：\s*\*{0,2}\s*(通过|不通过)", report_md or "")
    return m.group(1) if m else ""


def _verdict_mismatch(hr_verdict: str, ai_decision: str) -> bool:
    """HR 审核结论与 AI 决策是否相反（AI 无明确结论「待复核」时不算不一致）"""
    if ai_decision not in ("通过", "不通过"):
        return False
    return (hr_verdict == "通过") != (ai_decision == "通过")


_FALLBACK_INVITE = {
    "通过": "恭喜您通过本次面试评估，诚邀您于明天下午 3 点到智聘科技大厦 12 层参加线下面试，请携带相关证件，期待与您见面。",
    "驳回": "感谢您参与本次沟通。经过综合评估，我们暂时无法为您推进后续流程，感谢您的关注，祝您求职顺利。",
}


def _redraft_invite(verdict: str) -> str:
    """按 HR 结论重新起草通知文本（LLM 失败时回退固定模板，绝不中断审核流程）"""
    kind = "线下面试邀约" if verdict == "通过" else "婉拒通知"
    try:
        text = chat(
            [
                {
                    "role": "system",
                    "content": (
                        f"你是「智聘科技」的招聘专员。HR 审核结论为：{verdict}。"
                        f"请起草一段正式得体的{kind}：通过则写明线下面试时间地点"
                        "（明天下午 3 点，智聘科技大厦 12 层）；驳回则礼貌婉拒并感谢参与。"
                        "只输出通知正文，不要任何其他内容。"
                    ),
                },
                {"role": "user", "content": "请输出通知正文。"},
            ],
            temperature=0.5,
            max_tokens=300,
        )
        text = text.strip()
        if text:
            return text
    except Exception:
        pass
    return _FALLBACK_INVITE.get(verdict, "")


def _radio_value(decision: str) -> str:
    """审核单选默认值：AI 明确「不通过」时默认驳回，否则默认通过（与界面选项文本一致）"""
    return "驳回" if decision == "不通过" else "通过（进入线下面试）"


def load_pending(record_id):
    """载入一条待审核记录：完整详情 + AI 通知草稿 + 审核状态 + 审核单选默认值（供提交/确认发送使用）"""
    if isinstance(record_id, (list, tuple)):
        record_id = record_id[0] if record_id else None
    if not record_id:
        return "请先选择待审核记录", "", None, "请先选择待审核记录", gr.update()
    r = get_interview(record_id)
    if not r:
        return "记录不存在", "", None, "记录不存在", gr.update()
    detail = show_record(record_id)
    invite = _extract_invite(r["report"] or "")
    state = {"iid": r["id"], "candidate": r["candidate"], "job": r["job"]}
    # 审核单选默认值跟随 AI 决策（HR 可改，AI 只建议）
    radio = gr.update(value=_radio_value(_extract_decision(r["report"] or "")))
    return detail, invite, state, f"已载入 **{r['candidate']}** —— 上方选择审核决定、填写意见后点「提交审核（待审核记录）」", radio


def submit_pending(decision, comment, invite_text, pending_state, stage="最终审批"):
    """待审核记录的人工审核（录用决策链：业务审批 → 薪酬定薪 → 背景调查 → 最终审批）

    前三个环节记录审批轨迹（审批人+时间戳）并推进候选人状态，最终审批才写结论+发通知。
    生产环境：各环节由钉钉审批流对应节点触发（审批人身份经 SSO 注入），系统记录审批结论与时间戳留痕。
    """
    if not pending_state:
        return invite_text, None, None, "请先载入待审核记录"
    verdict = "通过" if decision.startswith("通过") else "驳回"
    stage_map = {"业务审批": "业务审批中", "薪酬定薪": "薪酬定薪中", "最终审批": None}  # 背景调查在 Offer 接受后（见入职运营）
    candidate_status = stage_map.get(stage)
    record_approval(pending_state["iid"], stage, verdict, approver="HR")
    if candidate_status:
        # 中间环节：记录轨迹 + 推进状态，不写最终结论（等最终审批）
        cand = get_candidate_by_name(pending_state["candidate"])
        if cand:
            update_candidate(cand["id"], status=candidate_status, status_note=f"{stage}：{verdict}（{comment}）")
        return invite_text, None, None, f"{stage}已记录（{verdict}，审批轨迹已留痕）——继续下一环节，或直接选「最终审批」出结论"
    # 最终审批：写结论 + 反馈校准 + 通知/Offer 联动
    update_interview_hr(pending_state["iid"], verdict, comment)
    add_hr_feedback(verdict, comment, pending_state["job"])
    note = ""
    # 一致性守卫：与 AI 决策相反时按 HR 结论重新起草（与手动模式 hr_review 同规则）
    rec = get_interview(pending_state["iid"])
    if rec and _verdict_mismatch(verdict, _extract_decision(rec["report"] or "")):
        invite_text = _redraft_invite(verdict)
        note = "（AI 建议与您的结论相反，通知已按您的结论重新起草）"
    # 全流程联动：候选人状态机 + 通知 + Offer 自动生成
    nid = _link_candidate_flow(pending_state["candidate"], pending_state["job"], verdict, invite_text)
    new_invite_state = {"iid": pending_state["iid"], "verdict": verdict, "candidate": pending_state["candidate"], "nid": nid}
    kind = "线下面试邀约" if verdict == "通过" else "婉拒通知"
    return invite_text, new_invite_state, None, f"最终审批完成（{verdict}）{note}—— AI 起草的{kind}已填入下方（可编辑），点击「确认发送」"


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


_PLACEHOLDER_RADAR = {}


def _placeholder_radar():
    """缓存的占位雷达图：流式 yield 期间保持 Plot 不空（避免 Gradio 清空组件）"""
    if _PLACEHOLDER_RADAR.get("fig") is None:
        _PLACEHOLDER_RADAR["fig"] = empty_radar_figure(get_profile("ai-dev"))
    return _PLACEHOLDER_RADAR["fig"]


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


def _interview_candidate(name, source, resume_text, resume, profile, history, session_state, plot, batch_id=None, style="tech"):
    """对单个候选人跑完 AI 互相聊天 + 决策报告（generator）——全自动演示与一键面试共用

    断点续面：面试开始时记录先建为「面试中」，每轮状态落盘（session_state）；
    中断后重试时自动从断点恢复继续面试，而不是从头再来。
    调用方逐个消费 yield：(history, session, plot, status)；循环结束后 session 即最终会话（含 report）。
    """
    session = InterviewSession(resume, profile, style=style)
    start = len(history)  # 记录本候选人在累计 history 中的起点，入库时只存自己的切片
    # 断点续面：查未完成面试 → 恢复会话；否则新建「面试中」记录
    prev = find_unfinished_interview(name, profile["job"])
    saved_state = load_session_state(prev["id"]) if prev else None
    if prev and saved_state:
        session = InterviewSession.from_state(saved_state, resume, profile, style=style)
        session.interview_id = prev["id"]
        try:
            prev_chat = json.loads(prev.get("chat") or "[]")
        except json.JSONDecodeError:
            prev_chat = []
        history = history + [{"role": "assistant", "content": f"**【断点续面】** 检测到 {name} 的未完成面试，从第 {session.round} 轮继续……"}]
        for m in prev_chat:
            history = history + [dict(m)]
    else:
        iid = save_interview(name, source, profile["job"], session.style["name"], "面试中", None, "", [], "")
        session.interview_id = iid
    iid = session.interview_id
    q = ""
    resumed = bool(prev and saved_state)
    try:
        if not resumed:
            history = history + [{"role": "assistant", "content": f"**【AI 招聘官】** → {name}\n\n"}]
            for partial, done in stream_first_message(session):
                q = partial
                history[-1]["content"] = f"**【AI 招聘官】** → {name}\n\n{partial}"
                yield [dict(m) for m in history], session_state, plot, f"{name}：AI 招聘官发言中……"
                if done:
                    break
            yield [dict(m) for m in history], session_state, plot, f"{name}：AI 互相聊天中……"
        else:
            # 恢复场景：上一轮招聘官问题已在落盘历史里，直接让候选人 AI 回答
            q = ""
            for m in reversed(session.history):
                if m.get("role") == "assistant":
                    q = m["content"]
                    break
            history = history + [{"role": "assistant", "content": f"**【AI 招聘官】（恢复）** → {name}\n\n{q}"}]
            yield [dict(m) for m in history], session_state, plot, f"{name}：断点续面，从第 {session.round + 1} 轮继续……"

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
            # 每轮落盘：断点续面的状态快照（含本轮问答）
            save_session_state(iid, session.to_state())
            if is_finished(session, q):
                history[-1]["content"] = f"**AI 招聘官 · 收口** → {name}\n\n{q}"
                yield [dict(m) for m in history], session_state, plot, f"{name}：AI 招聘官给出结论……"
            else:
                yield [dict(m) for m in history], session_state, plot, f"{name}：AI 招聘官回复完成……"

        # 决策报告 + 雷达图（回写「面试中」记录 → 待HR审核，只存本候选人自己的对话切片）
        report, fig = evaluate(session, profile)
        update_interview_result(iid, "待HR审核", session.report.get("total"), history[start:], report)
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


def history_to_markdown(history):
    """聊天历史 → 可读的问答对话流 markdown（一键面试直播用，不依赖 Chatbot 组件渲染）"""
    lines = []
    for m in history or []:
        role = "AI 招聘官" if m.get("role") == "assistant" else "候选人"
        content = m.get("content", "").strip()
        # 去掉消息内容里嵌入的角色前缀（【AI 招聘官】→ 名字 / 名字（候选人 AI）：），避免与行首标签重复
        content = re.sub(r"^\*\*【[^】]+】\*\* → .*?\n\n", "", content)
        content = re.sub(r"^\*\*[^*]*（候选人 AI）：\*\*\n\n", "", content)
        lines.append(f"**{role}：** {content}")
        lines.append("")
    return "\n".join(lines) or "（暂无对话）"


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
        return history_to_markdown(h), s, p, status, queue_markdown(queue)

    if not isinstance(history, list):
        history = []  # 输入组件是 Markdown 时传字符串，Chatbot 时传列表——统一归一化
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
        # 全流程状态机：面试开始 → 面试中
        cand_row = get_candidate_by_name(name, status="初筛通过")
        if cand_row:
            update_candidate(cand_row["id"], status="面试中")
        try:
            resume = parse_resume(item["resume_text"])
            history = history + [{"role": "assistant", "content": f"**【简历解析】**\n\n{format_resume_summary(resume)}"}]
            yield emit(history, session_state, plot, f"{name}：简历解析完成")
            # 岗位级面试风格：岗位管理配置的考官风格（技术深挖/压力面试等），默认技术深挖
            style = get_latest_job_style(profile_id)
            for h, sess, p, st in _interview_candidate(
                name, item["source"], item["resume_text"], resume, profile,
                history, session_state, plot, batch_id, style=style,
            ):
                history, session_state, plot = h, sess, p
                yield emit(history, session_state, plot, st)
            # 只有面试真正完成（记录已入库）才标记「已面试」；失败则留在队列可重试
            if getattr(session_state, "interview_id", None):
                update_screening_hr(item["screening_id"], "已面试", "自动面试完成")
                # 状态机推进：面试完成 → 待HR审核（HR 在评估审核环节做出最终决定）
                if cand_row:
                    update_candidate(cand_row["id"], status="待HR审核")
                entry = _entry_from_session(name, session_state)
                if entry:
                    entries.append(entry)
            else:
                if cand_row:
                    update_candidate(cand_row["id"], status="初筛通过", status_note="面试失败，可重试")
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
    """从库中取一批面试的结构化结果，生成横向对比报告；未选批次时自动用最新批次"""
    if isinstance(batch_id, (list, tuple)):  # 新版 Gradio Dropdown 值可能是 list
        batch_id = batch_id[0] if batch_id else None
    if not batch_id:
        batches = list_batches()
        if not batches:
            return "暂无面试批次 —— 跑完一批面试（≥1 人完成报告）后自动存档"
        batch_id = batches[0]["batch_id"]  # 自动用最新批次
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


# ==================== 全流程扩展：岗位管理 / 简历库 / 智能初筛 / 看板 ====================

def _copy_resume_file(src_path, name):
    """简历原文件落盘到 resumes/ 目录（保留原始文件，DB 存路径）"""
    os.makedirs(RESUME_DIR, exist_ok=True)
    ext = os.path.splitext(src_path)[1].lower() or ".txt"
    safe_name = re.sub(r"[^\w\u4e00-\u9fa5-]", "_", name)[:40]
    dst = os.path.join(RESUME_DIR, f"{safe_name}{ext}")
    if not os.path.exists(dst):
        import shutil
        shutil.copy2(src_path, dst)
    return dst


def import_resumes(folder_path, progress=gr.Progress()):
    """批量导入：扫描文件夹 → 解析文本 → 代码侧字段提取 → 候选人入库（状态机：新入库→已解析）

    支持 pdf/docx/txt/md；文件落盘 resumes/（DB 存路径），解析文本与结构化字段入库，
    后续初筛/面试全部从数据库调用，不依赖原文件。
    """
    if not folder_path or not os.path.isdir(folder_path):
        return "请填写有效的文件夹路径（如：C:\\Users\\22504\\recruit-agent\\demo_resumes）"
    exts = {".pdf", ".docx", ".txt", ".md"}
    files = [f for f in os.listdir(folder_path) if os.path.splitext(f)[1].lower() in exts]
    if not files:
        return "该文件夹下没有简历文件（支持 PDF/DOCX/TXT/MD）"
    ok = fail = manual = 0
    detail = []
    for i, fn in enumerate(sorted(files), 1):
        progress(i / len(files), desc=f"导入中 {i}/{len(files)}")
        path = os.path.join(folder_path, fn)
        try:
            text = extract_text(path)
            if not text.strip():
                raise ValueError("文件为空或扫描件无法提取文本")
            fields = extract_fields(text)  # 代码侧结构化提取（规则引擎输入）
            name = fields.get("name") or os.path.splitext(fn)[0].split("_")[-1] or fn
            stored = _copy_resume_file(path, name)
            add_candidate(name, text, source="文件夹批量导入", resume_file=stored, parsed=fields)
            ok += 1
            detail.append(f"- **{name}**（{fn}）→ 入库成功：学历 {fields.get('education') or '?'} · 年限 {fields.get('years')} 年 · 技能 {len(fields.get('skills', []))} 项")
        except Exception as e:
            # 兜底：解析失败不丢弃（避免误杀优秀候选人=假阴性），入库标记「待人工复核」
            name = os.path.splitext(fn)[0].split("_")[-1] if "_" in fn else os.path.splitext(fn)[0]
            try:
                stored = _copy_resume_file(path, name)
            except Exception:
                stored = ""
            cid = add_candidate(name, "", source="文件夹批量导入", resume_file=stored)
            update_candidate(cid, status="待人工复核", status_note=f"解析失败需人工复核：{e}")
            manual += 1
            detail.append(f"- {fn} → 解析失败，已入库标记**待人工复核**（原因：{e}）")
    return (
        f"### 导入完成：成功 **{ok}** 份，待人工复核 {manual} 份，丢弃 {fail} 份\n\n"
        f"解析失败的文件不会丢弃——已入库标记「待人工复核」（防止误杀优秀候选人，HR 可在简历库查看原因后手动处理）。\n\n" + "\n".join(detail)
    )


def refresh_candidate_table(status_filter="全部"):
    """候选人库列表（Dataframe：id/姓名/来源/学历/年限/状态/匹配分/初筛分/淘汰原因）"""
    rows = list_candidates()
    if status_filter and status_filter != "全部":
        rows = [r for r in rows if r["status"] == status_filter]
    data = []
    for r in rows:
        try:
            parsed = json.loads(r["parsed"] or "{}")
        except json.JSONDecodeError:
            parsed = {}
        data.append([
            r["id"], r["name"], parsed.get("education", "?"), parsed.get("years", 0),
            r["status"], r.get("match_score") or "", r.get("screen_score") or "",
            (r.get("status_note") or "")[:40],
        ])
    return data


def refresh_candidate_statuses():
    """候选人库状态筛选下拉的选项（含当前库中实际存在的状态）"""
    seen = ["全部"]
    for r in list_candidates(limit=1000):
        if r["status"] not in seen:
            seen.append(r["status"])
    return gr.update(choices=seen, value="全部")


# ---------- 岗位管理：JD + 筛选规则配置（人工输入筛选条件） ----------

def save_job_with_rules(job_title, jd_text, rubric_id, min_education, min_years, max_years, must_skills, max_salary, exclude_keywords, interview_style="tech"):
    """保存岗位配置：JD + 硬性筛选规则 + 岗位级面试风格 → job_profiles 表（供智能初筛/自动面试调用）"""
    if not job_title or not job_title.strip():
        return "请填写岗位名称"
    rules = {
        "min_education": min_education or "",
        "min_years": int(min_years or 0) or 0,
        "max_years": int(max_years or 0) or 0,
        "must_skills": [s.strip().lower() for s in (must_skills or "").replace("，", ",").split(",") if s.strip()],
        "max_salary": float(max_salary or 0) or 0,
        "exclude_keywords": [k.strip().lower() for k in (exclude_keywords or "").replace("，", ",").split(",") if k.strip()],
    }
    jid = save_job_profile(job_title.strip(), jd_text or "", rubric_id, rules, interview_style=interview_style)
    style_name = STYLES.get(interview_style, STYLES["tech"])["name"]
    rule_lines = "\n".join(
        f"- {k}：{v if v not in (0, '', []) else '（不限）'}" for k, v in rules.items()
    )
    return f"### 岗位配置已保存（#{jid}）\n\n**岗位：** {job_title} ｜ rubric：{rubric_id} ｜ 面试风格：{style_name}\n\n**筛选规则（规则引擎硬性判定）：**\n{rule_lines}"


def submit_hotword(word, comment):
    """热词建议提交（HR 提交 → 待审核 → 管理员合并入 SKILL_LEXICON 后全量生效）"""
    if not word or not word.strip():
        return "请填写建议的新词（如：LangGraph）"
    save_hotword_suggestion(word, comment)
    return f"热词「{word.strip()}」已提交，状态：**待审核**——管理员审核通过后合并入算法词表，全量生效"


def hotwords_markdown():
    """热词建议列表（审核状态）"""
    rows = list_hotword_suggestions()
    if not rows:
        return "暂无热词建议 —— 遇到词表没有的新技术词（如 LangGraph），提交后待审核合并入词表"
    lines = ["### 热词建议（词表更新入口）", "", "| 词 | 说明 | 状态 | 提交时间 |", "| --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r['word']} | {r['comment'] or '—'} | {r['status']} | {r['created_at']} |")
    return "\n".join(lines)


def refresh_job_profile_list():
    """已保存岗位配置列表（供智能初筛下拉选择）"""
    profiles = list_job_profiles()
    if not profiles:
        return gr.update(choices=[], value=None), "暂无已保存岗位配置 —— 请先在左侧保存"
    choices = [(f"#{p['id']} {p['title']}" + ("（停用）" if p["status"] != "启用" else ""), p["id"]) for p in profiles]
    return gr.update(choices=choices, value=profiles[0]["id"]), f"共 {len(profiles)} 个岗位配置"


def job_profile_detail(jid):
    """查看已保存岗位配置的规则明细"""
    if isinstance(jid, (list, tuple)):
        jid = jid[0] if jid else None
    if not jid:
        return "请选择岗位配置"
    p = get_job_profile(jid)
    if not p:
        return "岗位配置不存在"
    try:
        rules = json.loads(p["rules"] or "{}")
    except json.JSONDecodeError:
        rules = {}
    rule_lines = "\n".join(f"- **{k}**：{v if v not in (0, '', []) else '（不限）'}" for k, v in rules.items())
    return f"### #{p['id']} {p['title']}\n\n- rubric：{p['rubric_id']} ｜ 状态：{p['status']}\n- 创建：{p['created_at']}\n\n**筛选规则：**\n{rule_lines}"


# ---------- 智能初筛：规则引擎 + TF-IDF + AI 评分（从数据库调用候选人） ----------

def _screen_pool_core(pool, rules, rubric, jd_text, job_title, progress_cb=None):
    """初筛核心（同步/异步共用）：规则引擎 + 混合检索匹配 + 加分 + AI 证据链评分 + 评分卡落库

    返回 (rows, by_label)。progress_cb(done, total) 供进度上报。
    """
    rows, by_label = [], {}
    total = len(pool)
    resume_texts = [r["resume_text"] or "" for r in pool]
    # 分层打分：规则层（60%）+ 语义匹配层（30%，BM25+TF-IDF 混合检索）+ 加分层（10%）
    match_scores = match_layer_score(jd_text, resume_texts)
    for i, (r, mscore) in enumerate(zip(pool, match_scores), 1):
        if progress_cb:
            progress_cb(i, total)
        try:
            parsed = json.loads(r["parsed"] or "{}")
        except json.JSONDecodeError:
            parsed = {}
        rule_res = rule_layer_score(parsed, rules)      # 规则层：硬门槛 + 满足度评分
        bonus = bonus_layer_score(parsed, r["resume_text"])  # 加分层：大厂/证书/项目复杂度
        comp = composite_score(rule_res, mscore, bonus, rules.get("layer_weights"))
        if not comp["passed"]:
            reasons = "；".join(rule_res.get("reasons", []))
            update_candidate(r["id"], status="初筛淘汰", status_note=reasons, match_score=comp["total"])
            save_score_card(r["id"], r["name"], job_title, 0.0, f"规则淘汰：{reasons}",
                            {"硬门槛": {"status": "不通过", "detail": reasons}}, [])
            rows.append([i, r["name"], "❌ 规则淘汰", reasons, comp["total"], "—", "—"])
            label = f"⚠️申诉 #{r['id']} {r['name']}（被淘汰：{reasons[:24]}）"
            by_label[label] = {"cid": r["id"], "name": r["name"], "resume_text": r["resume_text"],
                                "source": r.get("source", ""), "total": comp["total"], "appeal": True}
            continue
        try:
            res = screen_resume(r["resume_text"], rubric)  # AI 证据链评分（参考分，与分层打分互相校验）
            ai_total = res.get("total", 0)
            decision = res.get("decision", "")
            comment = (res.get("comment") or "")[:30]
        except Exception as e:
            update_candidate(r["id"], status="初筛淘汰", status_note=f"AI 评分失败：{e}", match_score=comp["total"])
            rows.append([i, r["name"], "❌ 评分失败", str(e)[:40], comp["total"], "—", "—"])
            label = f"⚠️申诉 #{r['id']} {r['name']}（评分失败：{str(e)[:20]}）"
            by_label[label] = {"cid": r["id"], "name": r["name"], "resume_text": r["resume_text"],
                                "source": r.get("source", ""), "total": comp["total"], "appeal": True}
            continue
        update_candidate(r["id"], status="已初筛", match_score=comp["total"], screen_score=ai_total)
        card = {
            "硬门槛": {"status": "通过", "detail": f"学历 {parsed.get('education') or '?'} 达标，年限 {parsed.get('years')} 年在范围内，必备技能命中"},
            "规则层(60%)": {"score": rule_res["score"], "detail": "必备技能命中率×60 + 学历富余×20 + 年限匹配×20"},
            "语义匹配层(30%)": {"score": mscore, "detail": f"混合检索（BM25+TF-IDF）匹配分 {mscore / 100:.3f}"},
            "加分层(10%)": {"score": bonus, "detail": "大厂背景/证书/项目复杂度人工规则加权"},
        }
        card_evidence = [f"{k}：{v}" for k, v in (res.get("evidence") or {}).items()]
        save_score_card(r["id"], r["name"], job_title, comp["total"],
                        f"综合 {comp['total']} 分 · AI 建议 {decision}", card, card_evidence)
        label = f"#{r['id']} {r['name']}（综合 {comp['total']} 分）"
        by_label[label] = {"cid": r["id"], "name": r["name"], "resume_text": r["resume_text"],
                            "source": r.get("source", ""), "total": comp["total"]}
        rows.append([i, r["name"], "✅ 通过", "", comp["total"], ai_total, f"{decision} · {comment}"])
    rows.sort(key=lambda x: (x[4] if isinstance(x[4], (int, float)) else -1), reverse=True)
    for i, row in enumerate(rows, 1):
        row[0] = i
    return rows, by_label


def _load_job_context(job_profile_id):
    """加载岗位配置上下文（规则/rubric/JD），同步异步共用"""
    if isinstance(job_profile_id, (list, tuple)):
        job_profile_id = job_profile_id[0] if job_profile_id else None
    if not job_profile_id:
        return None, "请先选择岗位配置（岗位管理页保存后可用）"
    jp = get_job_profile(job_profile_id)
    if not jp:
        return None, "岗位配置不存在"
    try:
        rules = json.loads(jp["rules"] or "{}")
    except json.JSONDecodeError:
        rules = {}
    rubric = get_profile(jp["rubric_id"] or "ai-dev")
    jd_text = jp.get("jd_text") or f"{jp['title']} 岗位职责与任职要求"
    return {"jp": jp, "rules": rules, "rubric": rubric, "jd_text": jd_text}, None


def _screenable_pool():
    """待初筛候选人（已解析/已初筛/新入库/HR驳回 可初筛；待人工复核由 HR 手工处理不参与）"""
    return [r for r in list_candidates() if r["status"] in ("已解析", "已初筛", "新入库", "HR驳回")]


def run_library_screen(job_profile_id, status_filter, progress=gr.Progress()):
    """从数据库取候选人 → 规则引擎 → 混合检索匹配 → AI 评分 → 排序表（同步，带进度条）"""
    ctx, err = _load_job_context(job_profile_id)
    if err:
        return None, None, err
    pool = _screenable_pool()
    if not pool:
        return None, None, "简历库中没有待初筛候选人 —— 请先到「简历库」页批量导入"

    def cb(i, total):
        progress(i / total, desc=f"初筛中 {i}/{total}")

    rows, by_label = _screen_pool_core(pool, ctx["rules"], ctx["rubric"], ctx["jd_text"], ctx["jp"]["title"], cb)
    state = {"by_label": by_label, "job_title": ctx["jp"]["title"], "rubric_id": ctx["jp"]["rubric_id"]}
    note = (
        f"初筛完成：{len(pool)} 人 → 规则通过 {len(by_label)} 人 / 淘汰 {len(pool) - len(by_label)} 人\n\n"
        f"打分口径：**综合分 = 规则层 60% + 语义匹配层 30%（BM25+TF-IDF 混合检索）+ 加分层 10%**"
        f"（AI 证据链评分为参考分，淘汰原因与各层得分已写入数据库）\n\n"
        f"**申诉通道**：被淘汰的候选人（⚠️申诉项）也可由 HR 勾选进入面试队列——AI 淘汰≠最终结论"
    )
    return rows, state, note, gr.update(choices=[], value=[]), gr.update(choices=[], value=[])


def _async_screen_worker(tid, job_profile_id):
    """异步初筛后台线程：处理大批量简历不阻塞界面，完成自动推送群通知"""
    try:
        ctx, err = _load_job_context(job_profile_id)
        if err:
            update_batch_task(tid, status="失败", result=err)
            return
        pool = _screenable_pool()
        if not pool:
            update_batch_task(tid, status="完成", progress=100, result="没有待初筛候选人")
            return
        update_batch_task(tid, status="执行中", progress=0)

        def cb(i, total):
            update_batch_task(tid, progress=int(i / total * 100))

        rows, by_label = _screen_pool_core(pool, ctx["rules"], ctx["rubric"], ctx["jd_text"], ctx["jp"]["title"], cb)
        result = f"{ctx['jp']['title']}：{len(pool)} 人 → 通过 {len(by_label)} 人 / 淘汰 {len(pool) - len(by_label)} 人（评分卡与淘汰原因已落库，请勾选进入面试队列）"
        update_batch_task(tid, status="完成", progress=100, result=result)
        channel_notify("钉钉", screening_done_message(ctx["jp"]["title"], len(pool), len(by_label), len(pool) - len(by_label)))
    except Exception as e:
        update_batch_task(tid, status="失败", result=f"处理异常：{e}")


def submit_async_screen(job_profile_id, status_filter):
    """提交异步初筛任务：立即返回，后台线程执行，完成自动推送到群（大批量处理不阻塞）"""
    ctx, err = _load_job_context(job_profile_id)
    if err:
        return err, None
    import threading
    tid = create_batch_task(f"智能初筛：{ctx['jp']['title']}")
    threading.Thread(target=_async_screen_worker, args=(tid, job_profile_id), daemon=True).start()
    return f"任务 **#{tid}** 已提交，后台处理中（{ctx['jp']['title']}）——完成自动推送群通知，点「刷新任务状态」查看进度", tid


def batch_task_status(tid):
    """异步任务状态查询"""
    if isinstance(tid, (list, tuple)):
        tid = tid[0] if tid else None
    if not tid:
        tasks = list_batch_tasks()
        if not tasks:
            return "暂无异步任务 —— 提交「异步初筛」后在此查看进度"
        lines = ["### 最近异步任务", "", "| ID | 类型 | 状态 | 进度 | 结果 |", "| --- | --- | --- | --- | --- |"]
        for t in tasks[:10]:
            lines.append(f"| #{t['id']} | {t['task_type']} | {t['status']} | {t['progress']}% | {(t['result'] or '')[:40]} |")
        return "\n".join(lines)
    t = get_batch_task(tid)
    if not t:
        return f"任务 #{tid} 不存在"
    return (
        f"### 任务 #{t['id']}：{t['task_type']}\n\n"
        f"- 状态：**{t['status']}** ｜ 进度：**{t['progress']}%** ｜ 提交：{t['created_at']}\n"
        f"- 结果：{t['result'] or '处理中……'}"
    )


def send_library_to_queue(selected, lib_state):
    """智能初筛结果勾选 → screenings 入库（HR 复核落库）+ 候选人状态 → 初筛通过"""
    if not lib_state or not lib_state.get("by_label"):
        return None, "请先运行「从简历库智能初筛」"
    if not selected:
        return None, "请先勾选通过初筛的候选人（人工复核是必须环节）"
    count = appeal = skipped = 0
    for label in selected:
        item = lib_state["by_label"].get(label)
        if not item:
            continue
        if screening_in_queue(item["name"], lib_state["job_title"]):
            skipped += 1
            continue
        is_appeal = item.get("appeal", False)  # 申诉复审：AI 淘汰但 HR 勾选推翻
        sid = save_screening(item["name"], item["source"], lib_state["job_title"],
                             {}, item["total"], "建议进入面试", resume_text=item["resume_text"])
        hr_note = "HR 申诉复审通过（推翻 AI 淘汰结论）" if is_appeal else "HR 人工复核通过"
        update_screening_hr(sid, "进入面试队列", hr_note)
        update_candidate(item["cid"], status="初筛通过",
                          status_note=("申诉复审通过（HR 推翻 AI 淘汰）" if is_appeal else ""))
        if is_appeal:
            appeal += 1
        count += 1
    queue = list_screening_queue()
    note = f"已勾选 {count} 人进入面试队列" + (f"（其中申诉复审 {appeal} 人，HR 推翻 AI 淘汰结论）" if appeal else "")
    note += f"（复核结论已落库）" + (f"；{skipped} 人已在队列跳过" if skipped else "")
    note += f"；当前面试队列共 {len(queue)} 人"
    return queue, note


# ---------- 全流程看板：漏斗 + 算法说明 + 通知/Offer ----------

def funnel_markdown():
    """候选人全流程漏斗（状态机计数，读库）"""
    rows = funnel_stats()
    if not rows:
        return "暂无候选人数据 —— 请先到「简历库」页导入简历"
    total = sum(c for _, c in rows)
    lines = ["### 候选人全流程漏斗", "", "| 流程阶段 | 人数 | 占比 | 漏斗 |", "| --- | --- | --- | --- |"]
    for status, cnt in rows:
        pct = round(cnt / total * 100, 1) if total else 0
        bar = "█" * max(1, int(pct / 4)) if cnt else ""
        lines.append(f"| {status} | **{cnt}** | {pct}% | {bar} |")
    lines += ["", f"**共 {total} 位候选人**进入流程追踪（状态机持久化于数据库）"]
    return "\n".join(lines)


def channel_analysis_markdown():
    """渠道效果分析（结果数据）：各来源的初筛通过率——招聘预算该往哪投"""
    rows = list_candidates()
    if not rows:
        return "暂无候选人数据 —— 请先到「简历库」页导入简历"
    from collections import defaultdict
    agg = defaultdict(lambda: {"total": 0, "passed": 0, "eliminated": 0})
    for r in rows:
        src = (r.get("source") or "未知渠道")
        a = agg[src]
        a["total"] += 1
        if r["status"] in ("初筛通过", "面试中", "待HR审核", "HR通过", "已发通知", "已发Offer", "Offer已接受", "已入职"):
            a["passed"] += 1
        elif r["status"] in ("初筛淘汰", "HR驳回"):
            a["eliminated"] += 1
    lines = ["### 渠道效果分析（钱该往哪投）", "", "| 渠道 | 候选人 | 通过初筛 | 通过率 | 淘汰 |", "| --- | --- | --- | --- | --- |"]
    for src, a in sorted(agg.items(), key=lambda kv: -kv[1]["passed"]):
        rate = round(a["passed"] / a["total"] * 100, 1) if a["total"] else 0
        lines.append(f"| {src} | {a['total']} | {a['passed']} | **{rate}%** | {a['eliminated']} |")
    lines += ["", "> 通过率高的渠道优先加大投入；通过率持续偏低的渠道建议核验投递质量或停投。"]
    return "\n".join(lines)


def algorithm_doc_markdown():
    """算法说明面板（静态文档，写清每一步用什么算法）"""
    return ALGORITHM_DOC


def notifications_markdown():
    """通知发送记录（面试邀约/婉拒/Offer 邮件，模拟发送）"""
    rows = list_notifications()
    if not rows:
        return "暂无通知记录 —— HR 审核通过/驳回后自动生成，确认发送后标记已发送"
    lines = ["### 通知发送记录", "", "| 时间 | 候选人 | 类型 | 状态 |", "| --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r['created_at']} | {r['candidate_name']} | {r['ntype']} | {r['status']} |")
    return "\n".join(lines)


def offers_markdown():
    """Offer 发放记录"""
    rows = list_offers()
    if not rows:
        return "暂无 Offer 记录 —— HR 审核通过后自动生成 Offer 草稿"
    lines = ["### Offer 记录", "", "| 时间 | 候选人 | 岗位 | 薪资 | 状态 |", "| --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r['created_at']} | {r['candidate_name']} | {r['job_title']} | {r['salary']} | {r['status']} |")
    return "\n".join(lines)


# ---------- 入职运营智能体（第三智能体：培训匹配 → 入职引导 → 归档） ----------

def refresh_onboarding_dropdown():
    """待入职运营的候选人下拉（Offer 待接受的候选人）"""
    choices = [o["candidate_name"] for o in list_offers() if o["status"] in ("待接受",)]
    return gr.update(choices=choices, value=choices[0] if choices else None)


def run_onboarding(candidate_name):
    """入职运营：培训内容匹配 + 入职流程清单 + 新人数据归档（状态机 → 已入职）"""
    if not candidate_name:
        return "请先选择 Offer 候选人（Offer 待接受的候选人自动出现在下拉中）"
    return onboarding_plan(candidate_name)


def score_card_markdown(candidate_id):
    """评分卡展示：把打分全过程的中间结果摊开给 HR/总监看（可审计证据链）

    含：硬门槛判定 / 规则层分 / 语义匹配分 / 加分层分 / AI 证据链引用 / 人工复核留痕。
    """
    if isinstance(candidate_id, (list, tuple)):
        candidate_id = candidate_id[0] if candidate_id else None
    if not candidate_id:
        return "请选择候选人（初筛过的候选人自动出现在下拉中）"
    card = get_score_card(candidate_id)
    if not card:
        return "该候选人暂无评分卡 —— 先运行「智能初筛」生成"
    try:
        breakdown = json.loads(card["breakdown"] or "{}")
        evidence = json.loads(card["evidence"] or "[]")
    except json.JSONDecodeError:
        breakdown, evidence = {}, []
    lines = [
        f"## 评分卡：{card['candidate_name']}（{card['job_title']}）",
        "",
        f"**最终得分：{card['final_score']} 分** ｜ **结论：{card['decision']}** ｜ 生成时间：{card['created_at']}",
        "",
        "### 打分拆解（中间结果全透明）",
        "",
        "| 层 | 得分/判定 | 依据 |",
        "| --- | --- | --- |",
    ]
    for layer, info in breakdown.items():
        if isinstance(info, dict):
            score = info.get("score", "—")
            status = info.get("status", "")
            detail = info.get("detail", "")
            cell = f"{status} {score}" if status else f"{score} 分"
            lines.append(f"| {layer} | {cell} | {detail} |")
        else:
            lines.append(f"| {layer} | {info} | — |")
    lines += ["", "### 证据链（AI 维度评分引用）"]
    if evidence:
        lines += [f"- {e}" for e in evidence]
    else:
        lines += ["- （规则淘汰，无 AI 维度证据）"]
    lines += [
        "",
        f"### 人工复核（待 HR 填写）",
        "",
        f"{card['human_review'] or '（未复核）'}",
        "",
        "> 评分卡入库留痕：同一候选人每次初筛生成一张卡，可追溯评估时点的系统版本与算法输出。",
    ]
    return "\n".join(lines)


def refresh_scorecard_dropdown():
    """评分卡查询下拉：只列出有评分卡的候选人"""
    from db import _conn
    with _conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT candidate_id, candidate_name FROM score_cards ORDER BY id DESC LIMIT 200"
        ).fetchall()
    choices = [(f"#{r['candidate_id']} {r['candidate_name']}", r["candidate_id"]) for r in rows]
    return gr.update(choices=choices, value=choices[0][1] if choices else None)


def compare_score_cards(candidate_a, candidate_b):
    """评分卡并排对比：回答总监的「A 为什么比 B 高 X 分」"""
    def _unwrap(v):
        if isinstance(v, (list, tuple)):
            return v[0] if v else None
        return v

    def _cell(info):
        if isinstance(info, dict):
            score = info.get("score", "—")
            status = info.get("status", "")
            return f"{status} {score}".strip() if status else f"{score} 分"
        return str(info or "—")

    def _load(card):
        try:
            return json.loads(card["breakdown"] or "{}"), json.loads(card["evidence"] or "[]")
        except json.JSONDecodeError:
            return {}, []

    a_id, b_id = _unwrap(candidate_a), _unwrap(candidate_b)
    if not a_id or not b_id:
        return "请选择两个候选人（初筛过的候选人自动出现在下拉中）"
    if a_id == b_id:
        return "请选择两个不同的候选人"
    ca, cb = get_score_card(a_id), get_score_card(b_id)
    if not ca or not cb:
        return "所选候选人中有人暂无评分卡 —— 先运行「智能初筛」生成"
    ba, ea = _load(ca)
    bb, eb = _load(cb)
    diff = round((ca["final_score"] or 0) - (cb["final_score"] or 0), 1)
    lines = [
        f"## 评分卡对比：{ca['candidate_name']} vs {cb['candidate_name']}",
        "",
        f"**{ca['candidate_name']}：{ca['final_score']} 分** ｜ **{cb['candidate_name']}：{cb['final_score']} 分** ｜ **分差：{diff} 分**",
        "",
        "| 打分层 | " + ca["candidate_name"] + " | " + cb["candidate_name"] + " | 差异来源 |",
        "| --- | --- | --- | --- |",
    ]
    all_layers = list(ba.keys()) + [k for k in bb.keys() if k not in ba]
    for layer in all_layers:
        ia, ib = ba.get(layer), bb.get(layer)
        cell_a, cell_b = _cell(ia), _cell(ib)
        sa = ia.get("score") if isinstance(ia, dict) else None
        sb = ib.get("score") if isinstance(ib, dict) else None
        if isinstance(sa, (int, float)) and isinstance(sb, (int, float)):
            reason = f"{ca['candidate_name'] if sa >= sb else cb['candidate_name']} 此层高 {abs(round(sa - sb, 1))} 分"
        else:
            reason = "判定不同" if (cell_a != cell_b) else "—"
        lines.append(f"| {layer} | {cell_a} | {cell_b} | {reason} |")
    lines += ["", f"### 证据链对照", "", f"**{ca['candidate_name']}：**"]
    lines += [f"- {e}" for e in ea] or ["- （规则淘汰，无 AI 维度证据）"]
    lines += ["", f"**{cb['candidate_name']}：**"]
    lines += [f"- {e}" for e in eb] or ["- （规则淘汰，无 AI 维度证据）"]
    lines += ["", f"> 分差 {diff} 分的来源就在上表「差异来源」列——每一层的得分差都说得清。"]
    return "\n".join(lines)


def refresh_performance_dropdown():
    """试用期绩效回传下拉：已发 Offer 的候选人"""
    choices = [(f"#{o['id']} {o['candidate_name']}（{o['job_title']}）", o["id"]) for o in list_offers()]
    return gr.update(choices=choices, value=choices[0][1] if choices else None)


def submit_performance(offer_id, rating, comment):
    """试用期绩效回传：录用后 3 个月表现 vs 当初 AI 打分——数据闭环的证据链"""
    if isinstance(offer_id, (list, tuple)):
        offer_id = offer_id[0] if offer_id else None
    if not offer_id:
        return "请选择 Offer 候选人"
    if not rating:
        return "请选择绩效评级"
    record_performance(offer_id, rating, comment)
    return f"绩效已回传（评级：{rating}）——该数据将用于每月《AI 打分 vs 入职表现 一致率报告》（数据飞轮闭环）"


def cleanup_scorecards():
    """评分卡清理（保留策略：最近 180 天），返回清理结果"""
    n = cleanup_old_score_cards(keep_days=180)
    return f"已清理 {n} 张过期评分卡（保留最近 180 天）——数据保留策略见 README"


def usage_markdown():
    """API 用量与成本统计（成本控制：每次操作花了多少钱一目了然）"""
    from config import get_api_usage
    u = get_api_usage()
    lines = [
        "### API 用量与成本（DeepSeek）",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
        f"| 累计调用次数 | **{u['calls']}** 次 |",
        f"| 估算输入 token | {u['input_tokens']:,} |",
        f"| 估算输出 token | {u['output_tokens']:,} |",
        f"| **估算累计成本** | **¥{u['estimated_cost_yuan']}** |",
        "",
        f"> 价格按 deepseek-chat 刊例（输入 ¥2/百万 token，输出 ¥8/百万 token），token 按字符数粗估（中文 ≈1.2 token/字符）。",
        f"> 参考量级：批量初筛 1 人 ≈ 1 次 LLM 调用；1 场 AI 面试 ≈ 15-25 次调用；1000 份简历初筛 ≈ 1000 次调用 ≈ ¥10-20。",
    ]
    return "\n".join(lines)


def search_resume_library(keyword, status_filter):
    """简历库全文检索（关键字 → 姓名/技能/简历内容命中；生产替换位：Elasticsearch）"""
    rows = search_candidates(keyword)
    if status_filter and status_filter != "全部":
        rows = [r for r in rows if r["status"] == status_filter]
    data = []
    for r in rows:
        try:
            parsed = json.loads(r["parsed"] or "{}")
        except json.JSONDecodeError:
            parsed = {}
        data.append([
            r["id"], r["name"], parsed.get("education", "?"), parsed.get("years", 0),
            r["status"], r.get("match_score") or "", r.get("screen_score") or "",
            r.get("auth_source") or "", (r.get("status_note") or "")[:30],
        ])
    return data
