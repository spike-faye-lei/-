"""Gradio 界面装配：4 个 Tab 的全部组件与事件绑定（不含业务逻辑，逻辑见 handlers.py）"""
import os

import gradio as gr

from bulk_screen import BATCH_LIMIT
from candidates import CANDIDATES
from handlers import (
    auto_demo,
    confirm_invite,
    empty_radar_figure,
    hr_review,
    load_pending,
    load_resume_file,
    refresh_batches,
    refresh_pending,
    refresh_records,
    restore_queue,
    run_bulk_screen,
    run_jd_gen,
    run_question_gen,
    run_queue_interviews,
    search_candidate,
    send_reply,
    send_to_queue,
    show_compare,
    show_record,
    start_interview,
    stats_markdown,
    submit_pending,
)
from interviewer import STYLES
from job_profile import PROFILES, get_profile
from ui_theme import ASSETS


def build_ui():
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
                        queue_live = gr.Markdown(
                            "一键面试开始后，这里实时显示 **AI 招聘官 × 候选人** 的完整问答对话……",
                            elem_classes="panel",
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
            outputs=[chatbot, session_state, radar_plot, review_radio, status],
            show_progress="hidden",
        )
        answer_input.submit(
            send_reply,
            inputs=[answer_input, chatbot, session_state, radar_plot],
            outputs=[chatbot, session_state, radar_plot, review_radio, status],
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
            outputs=[pending_detail, invite_input, pending_state, status, review_radio],
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
            inputs=[interview_queue, screen_profile, queue_live, session_state, radar_plot],
            outputs=[queue_live, session_state, radar_plot, screen_status, queue_display],
        )
        # 候选人对比页：页面加载即自动生成最新批次报告；手动生成时显示进度（LLM 需要十几秒）
        demo.load(refresh_batches, outputs=[batch_dropdown], show_progress="hidden")
        demo.load(show_compare, inputs=[batch_dropdown], outputs=[compare_output], show_progress="hidden")
        batch_refresh_btn.click(refresh_batches, outputs=[batch_dropdown], show_progress="hidden")
        compare_btn.click(show_compare, inputs=[batch_dropdown], outputs=[compare_output])
        # 招聘工具页
        jd_btn.click(run_jd_gen, inputs=[jd_role, jd_notes], outputs=[jd_output], show_progress="hidden")
        q_btn.click(run_question_gen, inputs=[q_profile, q_count], outputs=[q_output], show_progress="hidden")
        demo.load(stats_markdown, outputs=[stats_output], show_progress="hidden")
        stats_refresh_btn.click(stats_markdown, outputs=[stats_output], show_progress="hidden")

    return demo
