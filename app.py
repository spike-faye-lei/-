"""招聘智能体 Demo：全自动演示 + 手动模式（岗位配置 · 证据链评分 · HR 人工审核闸门）
运行：双击 start.bat 或执行 python app.py，浏览器打开 http://localhost:7860
"""
import json
import os
import time

import gradio as gr

from candidates import CANDIDATES
from candidate_bot import reply as candidate_reply
from db import get_interview, init_db, list_interviews, save_interview
from evaluator import evaluate
from file_parser import extract_text
from interviewer import STYLES, InterviewSession, first_message, is_finished, next_message
from job_profile import PROFILES, add_hr_feedback, get_profile
from resume_parser import format_resume_summary, parse_resume, pre_screen

init_db()  # 启动时初始化 SQLite

ASSETS = os.path.join(os.path.dirname(__file__), "assets")

COMPLIANCE = (
    "**【合规】** 已获得候选人授权同意，简历与对话数据仅用于本次招聘评估，"
    "存储于企业内网，候选人可随时要求删除（符合《个人信息保护法》要求）"
)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

/* ===== Linear 风格设计 token（参考 research/07-design-reference.md） ===== */
:root {
  --bg-page: #08090A;        /* 页面底（近黑带蓝灰） */
  --bg-panel: #0F1011;       /* 面板 */
  --bg-card: #191A1B;        /* 卡片 */
  --bg-hover: #28282C;       /* hover 表面 */
  --bg-input: #0F1011;       /* 输入框（比卡片深） */
  --text-1: #F7F8F8;         /* 主文字（非纯白） */
  --text-2: #D0D6E0;         /* 次级文字 */
  --text-3: #8A8F98;         /* 占位/元信息 */
  --border-1: rgba(255,255,255,0.05);
  --border-2: rgba(255,255,255,0.08);
  --border-3: rgba(255,255,255,0.12);
  --accent: #5E6AD2;         /* 唯一强调色：indigo */
  --accent-hover: #828FFF;
  --success: #27A644; --danger: #E2162A; --warning: #FFAE00;
  --r-sm: 6px; --r-md: 8px; --r-lg: 12px;
}

body { background: var(--bg-page) !important; }

.gradio-container {
  max-width: 1320px !important; margin: 0 auto !important; padding: 18px 20px 32px !important;
  background: transparent !important;
  font-family: "Inter", -apple-system, "Segoe UI", "Noto Sans SC", "Microsoft YaHei", sans-serif !important;
  color: var(--text-1) !important;
  font-weight: 400;
}

/* 卡片：近黑分层 + hairline 边框，靠亮度分层不靠投影 */
.panel, .gr-box, .form, .wrap, .gr-group {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-2) !important;
  border-radius: var(--r-md) !important;
  box-shadow: 0 1px 2px rgba(0,0,0,0.16) !important;
  padding: 16px !important;
}
#left-col, #right-col { gap: 12px; }

/* 顶部横幅：深色面板 + 强调色左边条（无渐变、无装饰光效） */
#banner {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border-2) !important;
  border-left: 3px solid var(--accent) !important;
  border-radius: var(--r-lg) !important;
  padding: 18px 22px; margin-bottom: 14px;
  display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;
}
#banner h1 { margin: 0; font-size: 20px; font-weight: 600; letter-spacing: -0.02em; color: var(--text-1); }
#banner p { margin: 4px 0 0; font-size: 12.5px; color: var(--text-3); }
#steps { display: flex; gap: 6px; flex-wrap: wrap; }
.step-chip {
  background: var(--bg-card); border: 1px solid var(--border-2);
  border-radius: var(--r-full); padding: 4px 12px; font-size: 11.5px; color: var(--text-2);
  font-variant-numeric: tabular-nums;
}

/* 按钮：纯色强调，无渐变；绿/橙仅作状态色 */
#auto-btn button, #start-btn button, #send-btn button, #search-btn button {
  background: var(--accent) !important;
  border: none !important; color: #fff !important; font-weight: 500; border-radius: var(--r-sm) !important;
  transition: background .15s ease !important;
  cursor: pointer;
}
#auto-btn button:hover, #start-btn button:hover, #send-btn button:hover, #search-btn button:hover { background: var(--accent-hover) !important; }
#auto-btn button { background: var(--success) !important; font-size: 14px; padding: 9px !important; }
#auto-btn button:hover { background: #2DB84C !important; }
#review-btn button { background: var(--warning) !important; color: #000 !important; }
#review-btn button:hover { background: #FFBE26 !important; }

/* 状态条：面板色 */
#status-bar {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border-2) !important; border-radius: var(--r-md) !important; padding: 9px 14px !important;
}
#status-bar p { margin: 0; font-size: 12.5px; color: var(--text-2); }

/* 聊天区：气泡近黑分层 */
#chat { border-radius: var(--r-md) !important; background: var(--bg-panel) !important; }
#chat .message.bot { background: var(--bg-card) !important; border: 1px solid var(--border-1); color: var(--text-1) !important; }
#chat .message.user { background: var(--accent) !important; color: #fff !important; }
#radar { border-radius: var(--r-md); background: var(--bg-panel); border: 1px solid var(--border-2); padding: 6px; }

/* 文字与表单控件 */
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
    """手动模式：解析简历 -> 初筛 -> AI 主动联系（含合规声明）"""
    if not resume_text or not resume_text.strip():
        return history, None, None, "请先粘贴简历、上传文件或从简历库检索"

    profile = get_profile(profile_id)
    try:
        resume = parse_resume(resume_text)
        screen = pre_screen(resume)
        session = InterviewSession(resume, profile, style=style_id)
        msg = first_message(session)
        history = [
            {"role": "assistant", "content": COMPLIANCE},
            {"role": "assistant", "content": f"**【简历解析】**\n\n{format_resume_summary(resume)}"},
            {"role": "assistant", "content": f"**【自动初筛】**\n\n{screen}"},
            {"role": "assistant", "content": f"**【AI 主动联系】**\n\n{msg}"},
        ]
        return history, session, None, f"招聘进行中 —— AI 正在与候选人沟通（第 {session.round} 轮）"
    except Exception as e:
        return history, None, None, f"启动失败：{e}"


def send_reply(user_input, history, session_state, plot_output):
    """手动模式：候选人回答 -> AI 推进 -> 结束后出报告+雷达图"""
    if session_state is None:
        return history, session_state, plot_output, "请先添加简历并点击「开始招聘」"
    if not user_input or not user_input.strip():
        return history, session_state, plot_output, "请输入候选人回答"

    session = session_state
    try:
        reply = next_message(session, user_input)
        history = history + [{"role": "user", "content": user_input}]
        if is_finished(session, reply):
            report, fig = evaluate(session, session.profile)
            history = history + [
                {"role": "assistant", "content": reply},
                {"role": "assistant", "content": report},
                {"role": "assistant", "content": "**报告已生成，等待 HR 在下方审核后发送最终决定**"},
            ]
            return history, session, fig, "筛选完成 —— 请在下方进行 HR 审核"
        history = history + [{"role": "assistant", "content": reply}]
        return history, session, plot_output, (
            f"招聘进行中（第 {session.round} 轮 · {session.style['name']}风格 · 追问难度：{session.difficulty_name}）"
        )
    except Exception as e:
        return history, session_state, plot_output, f"调用失败：{e}"


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


def auto_demo(history, session_state, plot_output, demo_scope):
    """全自动演示：AI 主动检索简历池 -> 逐份初筛 -> 合适的自动互相聊天 -> 报告（全部入库）"""
    candidates = CANDIDATES if demo_scope == "完整 5 人" else CANDIDATES[:3]
    history = [{"role": "assistant", "content": COMPLIANCE}]
    yield history, session_state, None, "全自动招聘演示启动……"

    for cand in candidates:
        name = cand["label"].split("·")[0].strip()
        # 1. 主动检索（附候选人档案）
        history = history + [{
            "role": "assistant",
            "content": (
                f"**【主动检索】**\n\n从 **{cand['source']}** 检索到候选人：**{name}**\n\n"
                f"**候选人档案：** {cand['profile']}\n\n{cand['resume'][:320]}"
            ),
        }]
        yield history, session_state, None, f"正在初筛 {name}……"
        time.sleep(0.5)

        # 2. 解析 + 初筛
        try:
            resume = parse_resume(cand["resume"])
            screen = pre_screen(resume)
            history = history + [
                {"role": "assistant", "content": f"**【简历解析】**\n\n{format_resume_summary(resume)}"},
                {"role": "assistant", "content": f"**【自动初筛】**\n\n{screen}"},
            ]
            yield history, session_state, None, f"初筛完成：{name}"

            if "低" in screen:
                history = history + [{"role": "assistant", "content": f"**【跳过】** **{name} 匹配度低，不进入沟通，自动跳过**"}]
                save_interview(name, cand["source"], "AI 应用开发工程师", "自动初筛跳过", "跳过", None, "", history, "")
                yield history, session_state, None, f"{name} 已跳过（低匹配）"
                continue

            # 3. AI 互相聊天：招聘官 AI vs 候选人 AI
            profile = get_profile("ai-dev")
            session = InterviewSession(resume, profile)
            q = first_message(session)
            history = history + [{"role": "assistant", "content": f"**【AI 招聘官】** → {name}\n\n{q}"}]
            yield history, session_state, None, f"{name}：AI 互相聊天中……"

            while not is_finished(session, q):
                answer = candidate_reply(name, cand["resume"], session.history, q)
                history = history + [{"role": "user", "content": f"**{name}（候选人 AI）：**\n\n{answer}"}]
                yield history, session_state, None, f"{name} 回答中……"
                time.sleep(0.3)

                q = next_message(session, answer)
                role = "**AI 招聘官**" if not is_finished(session, q) else "**AI 招聘官 · 收口**"
                history = history + [{"role": "assistant", "content": f"{role} → {name}\n\n{q}"}]
                yield history, session_state, None, f"{name}：AI 招聘官回复中……"
                time.sleep(0.3)

            # 4. 决策报告 + 雷达图（自动入库）
            report, fig = evaluate(session, profile)
            decision = session.report.get("decision", "通过")
            save_interview(name, cand["source"], profile["job"], session.style["name"], decision, session.report.get("total"), "", history, report)
            history = history + [
                {"role": "assistant", "content": f"**【筛选决策报告】** **{name}**\n\n{report}"},
                {"role": "assistant", "content": f"**{name} 的报告已提交 HR 审核**（可在下方人工审核）"},
            ]
            yield history, session, fig, f"{name} 处理完成 —— 待 HR 审核"
        except Exception as e:
            history = history + [{"role": "assistant", "content": f"处理 {name} 失败：{e}"}]
            yield history, session_state, None, f"{name} 处理失败"

    yield history, session_state, None, "**全自动招聘演示结束** —— 全部结果已存档，可在左侧「面试记录」回看"


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
                    record_dropdown = gr.Dropdown(label="选择记录", choices=[], scale=8)
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

            radar_plot = gr.Plot(label="候选人能力雷达图")

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

    auto_btn.click(
        auto_demo,
        inputs=[chatbot, session_state, radar_plot, scope_dropdown],
        outputs=[chatbot, session_state, radar_plot, status],
    )
    demo.load(refresh_records, outputs=[record_dropdown, record_detail])
    refresh_btn.click(refresh_records, outputs=[record_dropdown, record_detail])
    record_dropdown.change(show_record, inputs=record_dropdown, outputs=record_detail)
    resume_file.change(
        load_resume_file,
        inputs=[resume_file, chatbot, session_state],
        outputs=[resume_input, session_state, status],
    )
    search_btn.click(
        search_candidate,
        inputs=[candidate_dropdown, chatbot, session_state],
        outputs=[resume_input, session_state, status],
    )
    start_btn.click(
        start_interview,
        inputs=[resume_input, profile_dropdown, style_dropdown, chatbot, session_state],
        outputs=[chatbot, session_state, radar_plot, status],
    )
    send_btn.click(
        send_reply,
        inputs=[answer_input, chatbot, session_state, radar_plot],
        outputs=[chatbot, session_state, radar_plot, status],
    )
    answer_input.submit(
        send_reply,
        inputs=[answer_input, chatbot, session_state, radar_plot],
        outputs=[chatbot, session_state, radar_plot, status],
    )
    review_btn.click(
        hr_review,
        inputs=[review_radio, review_comment, chatbot, session_state, radar_plot],
        outputs=[chatbot, session_state, radar_plot, status],
    )


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft(), css=CSS)
