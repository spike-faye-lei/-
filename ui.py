"""Gradio 界面装配：4 个 Tab 的全部组件与事件绑定（不含业务逻辑，逻辑见 handlers.py）"""
import os

import gradio as gr

from bulk_screen import BATCH_LIMIT
from candidates import CANDIDATES
from handlers import (
    algorithm_doc_markdown,
    auto_demo,
    batch_task_status,
    compare_score_cards,
    confirm_invite,
    empty_radar_figure,
    funnel_markdown,
    hotwords_markdown,
    hr_review,
    import_resumes,
    job_profile_detail,
    load_pending,
    load_resume_file,
    notifications_markdown,
    offers_markdown,
    refresh_batches,
    refresh_candidate_statuses,
    refresh_candidate_table,
    refresh_job_profile_list,
    refresh_onboarding_dropdown,
    refresh_pending,
    refresh_performance_dropdown,
    refresh_records,
    refresh_scorecard_dropdown,
    restore_queue,
    run_bulk_screen,
    run_jd_gen,
    run_library_screen,
    run_onboarding,
    run_question_gen,
    run_queue_interviews,
    save_job_with_rules,
    score_card_markdown,
    search_candidate,
    search_resume_library,
    send_library_to_queue,
    send_reply,
    send_to_queue,
    show_compare,
    show_record,
    start_interview,
    stats_markdown,
    submit_async_screen,
    submit_hotword,
    submit_pending,
    submit_performance,
    usage_markdown,
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
              <p>筛选 · 面试 · 评估 · 录用全流程自动化 ｜ HR 只做最终决策</p>
              <div id="steps">
                <span class="step-chip">岗位管理</span>
                <span class="step-chip">简历库</span>
                <span class="step-chip">智能初筛</span>
                <span class="step-chip">自动面试</span>
                <span class="step-chip">评估审核</span>
                <span class="step-chip">看板</span>
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

                        with gr.Accordion("全自动演示（演示模式）", open=False):
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
                                info="仅采集平台公开自愿发布信息，失败自动回退内置数据（演示用途）",
                            )

                        with gr.Accordion("岗位与考官配置", open=False):
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

                        with gr.Accordion("HR 审核闸门 + 待审核队列（录用决策唯一人工点）", open=False):
                            gr.Markdown("AI 只给建议和证据，**最终决定权在 HR**。审核意见进入**反馈校准闭环**")
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
                            invite_channel = gr.Dropdown(
                                choices=["邮件", "企业微信", "短信", "站内信"],
                                value="邮件",
                                label="通知发送渠道（自动触发，生产对接企业微信/短信通道）",
                            )
                            send_invite_btn = gr.Button("确认发送", elem_id="review-btn", variant="primary")
                            gr.Markdown("---\n**待审核队列**：自动面试完成的候选人按「待HR审核」入库，从库里载入逐条审核（不依赖当前会话）")
                            with gr.Row():
                                pending_dropdown = gr.Dropdown(
                                    label="待审核记录", choices=[], scale=8,
                                    allow_custom_value=True,  # 服务重启后旧页面残留值不报错
                                )
                                pending_refresh_btn = gr.Button("刷新", scale=2)
                            pending_load_btn = gr.Button("载入待审核记录", elem_id="search-btn", variant="primary")
                            pending_detail = gr.Markdown("")
                            pending_stage = gr.Dropdown(
                                choices=["业务审批", "薪酬定薪", "最终审批"],
                                value="最终审批",
                                label="审批环节（Offer 前决策链，每环节留痕；背调在 Offer 接受后）",
                            )
                            pending_submit_btn = gr.Button("提交审核（待审核记录）", elem_id="review-btn", variant="primary")

            with gr.Tab("岗位管理"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5, elem_id="left-col"):
                        with gr.Group(elem_classes="panel"):
                            gr.Markdown("### 岗位与筛选规则配置")
                            gr.Markdown("人工输入硬性筛选条件，规则引擎逐条判定，不满足直接淘汰并给出原因")
                            job_title_input = gr.Textbox(label="岗位名称", placeholder="如：AI 应用开发工程师")
                            job_jd_input = gr.Textbox(
                                label="岗位职责/任职要求（JD 摘要，用于 TF-IDF 匹配）",
                                lines=4,
                                placeholder="如：负责 RAG 知识库产品开发；要求 Python、LangChain、向量数据库，2 年以上经验",
                            )
                            job_rubric = gr.Dropdown(
                                choices=[p["id"] for p in PROFILES],
                                value="ai-dev",
                                label="评分 rubric（评估维度与权重）",
                            )
                            job_style = gr.Dropdown(
                                choices=[(s["name"], sid) for sid, s in STYLES.items()],
                                value="tech",
                                label="岗位级面试风格（自动面试时按此风格调用 prompt 模板）",
                            )
                            with gr.Row():
                                job_edu = gr.Dropdown(
                                    choices=["不限", "大专", "本科", "硕士", "博士"],
                                    value="不限", label="最低学历", scale=3,
                                )
                                job_min_years = gr.Number(value=0, label="最低年限", precision=0, scale=3)
                                job_max_years = gr.Number(value=0, label="最高年限（0=不限）", precision=0, scale=4)
                            with gr.Row():
                                job_must_skills = gr.Textbox(
                                    label="必备技能（逗号分隔，缺一淘汰）",
                                    placeholder="python, 大模型, rag",
                                    scale=6,
                                )
                                job_max_salary = gr.Number(value=0, label="薪资上限K（0=不限）", scale=4)
                            job_exclude = gr.Textbox(
                                label="排除关键词（命中即淘汰）",
                                placeholder="如：无AI经验, 外包",
                            )
                            job_save_btn = gr.Button("保存岗位配置（写入数据库）", elem_id="start-btn", variant="primary")
                            job_save_output = gr.Markdown("")
                        with gr.Accordion("算法词表热词建议（新词提交）", open=False):
                            gr.Markdown("词表没有的新技术词 → 提交 → 管理员审核后合并入算法词表全量生效")
                            with gr.Row():
                                hotword_input = gr.Textbox(label="建议新词", placeholder="如：LangGraph", scale=5)
                                hotword_comment = gr.Textbox(label="说明（可选）", scale=5)
                            hotword_btn = gr.Button("提交热词建议", elem_id="search-btn", variant="primary")
                            hotword_output = gr.Markdown("")
                    with gr.Column(scale=7, elem_id="right-col"):
                        with gr.Group(elem_classes="panel"):
                            gr.Markdown("### 已配置岗位（数据库）")
                            gr.Markdown("智能初筛从这里选择岗位配置（JD + 筛选规则 + rubric 三合一）")
                            with gr.Row():
                                job_list_dropdown = gr.Dropdown(
                                    label="选择岗位配置查看规则", choices=[], scale=8,
                                    allow_custom_value=True,
                                )
                                job_list_refresh_btn = gr.Button("刷新", scale=2)
                            job_detail_output = gr.Markdown("暂无已保存岗位配置")

            with gr.Tab("简历库"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5, elem_id="left-col"):
                        with gr.Group(elem_classes="panel"):
                            gr.Markdown("### 简历文件批量入库")
                            gr.Markdown("扫描文件夹 → 解析文本 + 结构化字段提取 → **写入数据库**。后续初筛/面试/对比全部从数据库调用，不依赖原文件")
                            import_folder = gr.Textbox(
                                label="简历文件夹路径",
                                placeholder=r"如：C:\Users\22504\recruit-agent\demo_resumes",
                            )
                            import_btn = gr.Button("批量导入简历（写入数据库）", elem_id="start-btn", variant="primary")
                            import_output = gr.Markdown("等待导入……")
                        with gr.Group(elem_classes="panel"):
                            gr.Markdown("### 候选人库筛选与全文检索")
                            cand_search = gr.Textbox(
                                label="简历全文检索（姓名/技能/内容关键字）",
                                placeholder="如：python / 大模型 / 张伟（生产环境替换为 Elasticsearch）",
                            )
                            cand_status_filter = gr.Dropdown(
                                label="按状态过滤", choices=["全部"], value="全部",
                            )
                            cand_refresh_btn = gr.Button("刷新候选人库", elem_id="search-btn", variant="primary")
                    with gr.Column(scale=7, elem_id="right-col"):
                        cand_table = gr.Dataframe(
                            headers=["ID", "姓名", "学历", "年限", "状态", "综合分", "AI参考分", "授权来源", "备注"],
                            datatype=["number", "str", "str", "number", "str", "number", "number", "str", "str"],
                            label="候选人库（数据库 · 含授权日志）",
                            interactive=False,
                            wrap=True,
                        )

            with gr.Tab("批量初筛"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5, elem_id="left-col"):
                        with gr.Group(elem_classes="panel"):
                            gr.Markdown("### 智能初筛（从简历库 · 全算法链路）")
                            gr.Markdown("**规则引擎**（硬性判定）→ **TF-IDF 匹配**（JD↔简历）→ **AI 证据链评分**（加权总分），淘汰原因与状态写入数据库")
                            with gr.Row():
                                lib_job_dropdown = gr.Dropdown(
                                    label="岗位配置（岗位管理页保存）", choices=[], scale=7,
                                    allow_custom_value=True,
                                )
                                lib_job_refresh_btn = gr.Button("刷新", scale=2)
                            lib_status_dropdown = gr.Dropdown(
                                label="候选人范围（简历库状态）",
                                choices=["待初筛（已解析/新入库）", "已初筛（重跑）", "全部候选人"],
                                value="待初筛（已解析/新入库）",
                            )
                            lib_screen_btn = gr.Button("运行智能初筛（规则 + 混合检索 + AI 评分）", elem_id="auto-btn", variant="primary")
                            lib_screen_status = gr.Markdown("等待运行……", elem_id="status-bar")
                            with gr.Row():
                                lib_async_btn = gr.Button("提交异步任务（大批量后台处理）", elem_id="search-btn", variant="primary", scale=6)
                                lib_task_refresh_btn = gr.Button("刷新任务状态", scale=2)
                            lib_task_output = gr.Markdown("异步任务状态：暂无")
                        with gr.Group(elem_classes="panel"):
                            gr.Markdown("### 人工复核闸门（从库初筛）")
                            gr.Markdown("勾选通过初筛者 → 复核结论落库 → 面试队列。**AI 只给建议，人决定**")
                            lib_check = gr.CheckboxGroup(label="初筛结果（勾选 = 进入面试队列）", choices=[])
                            lib_queue_btn = gr.Button("勾选者送入面试队列", elem_id="search-btn", variant="primary")
                            lib_screen_note = gr.Markdown("")
                        with gr.Accordion("评分卡查询（打分全透明）", open=False):
                            gr.Markdown("初筛过的候选人自动生成**评分卡**：硬门槛判定/三层得分/AI 证据链引用/人工复核留痕——总监一眼看懂 AI 怎么算分")
                            with gr.Row():
                                scorecard_dropdown = gr.Dropdown(
                                    label="选择候选人", choices=[], scale=8,
                                    allow_custom_value=True,
                                )
                                scorecard_refresh_btn = gr.Button("刷新", scale=2)
                            scorecard_output = gr.Markdown("选择候选人后自动显示评分卡")
                        with gr.Accordion("批量简历初筛（上传/粘贴）", open=False):
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
                        lib_screen_table = gr.Dataframe(
                            headers=["排名", "姓名", "规则判定", "淘汰原因", "综合分(60/30/10)", "AI参考分", "AI建议"],
                            datatype=["number", "str", "str", "str", "number", "number", "str"],
                            label="智能初筛结果（综合分 = 规则层60% + 匹配层30% + 加分层10%，按综合分降序）",
                            interactive=False,
                            wrap=True,
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
                with gr.Accordion("评分卡对比（A 为什么比 B 高 X 分）", open=False):
                    with gr.Group(elem_classes="panel"):
                        gr.Markdown("把两个候选人的评分卡并排对照：每层得分差 + 证据引用差异")
                        with gr.Row():
                            card_a_dropdown = gr.Dropdown(
                                label="候选人 A", choices=[], scale=5, allow_custom_value=True,
                            )
                            card_b_dropdown = gr.Dropdown(
                                label="候选人 B", choices=[], scale=5, allow_custom_value=True,
                            )
                            card_refresh_btn = gr.Button("刷新", scale=1)
                        card_compare_btn = gr.Button("生成评分卡对比", elem_id="search-btn", variant="primary")
                        card_compare_output = gr.Markdown("")

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
                        with gr.Accordion("招聘数据看板", open=False):
                            stats_refresh_btn = gr.Button("刷新看板", elem_id="search-btn", variant="primary")
                            stats_output = gr.Markdown("点击「刷新看板」查看统计")

            with gr.Tab("全流程看板"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5, elem_id="left-col"):
                        with gr.Group(elem_classes="panel"):
                            gr.Markdown("### 候选人全流程漏斗")
                            gr.Markdown("状态机追踪：新入库 → 已解析 → 已初筛 → 初筛通过 → 面试中 → 待HR审核 → HR通过 → 已发通知 → 已发Offer → 已入职")
                            funnel_refresh_btn = gr.Button("刷新漏斗", elem_id="search-btn", variant="primary")
                            funnel_output = gr.Markdown("等待数据……")
                        with gr.Group(elem_classes="panel"):
                            gr.Markdown("### 通知发送记录")
                            gr.Markdown("面试邀约 / 婉拒通知 / Offer 邮件（HR 审核后自动生成，确认发送后标记）")
                            notif_refresh_btn = gr.Button("刷新通知记录", elem_id="search-btn", variant="primary")
                            notif_output = gr.Markdown("暂无通知记录")
                        with gr.Accordion("Offer 记录", open=False):
                            offer_refresh_btn = gr.Button("刷新 Offer 记录", elem_id="search-btn", variant="primary")
                            offer_output = gr.Markdown("暂无 Offer 记录")
                        with gr.Accordion("入职运营智能体（培训匹配+归档+绩效回传）", open=False):
                            gr.Markdown("Offer 待接受的候选人 → 自动匹配培训内容 + 生成入职流程清单 + 新人数据归档（第三智能体）")
                            with gr.Row():
                                onboarding_dropdown = gr.Dropdown(
                                    label="Offer 候选人", choices=[], scale=7,
                                    allow_custom_value=True,
                                )
                                onboarding_refresh_btn = gr.Button("刷新", scale=2)
                            onboarding_btn = gr.Button("生成入职计划并归档", elem_id="auto-btn", variant="primary")
                            onboarding_output = gr.Markdown("等待选择 Offer 候选人……")
                            gr.Markdown("---\n**试用期绩效回传**（录用后 3 个月绩效 vs 当初 AI 打分 —— 数据飞轮闭环）")
                            with gr.Row():
                                perf_dropdown = gr.Dropdown(
                                    label="Offer 候选人", choices=[], scale=5, allow_custom_value=True,
                                )
                                perf_rating = gr.Dropdown(
                                    choices=["超出预期", "符合预期", "未达预期"],
                                    label="绩效评级", scale=3,
                                )
                            perf_comment = gr.Textbox(label="绩效备注（可选）", lines=2)
                            perf_btn = gr.Button("回传绩效", elem_id="search-btn", variant="primary")
                            perf_output = gr.Markdown("")
                    with gr.Column(scale=7, elem_id="right-col"):
                        with gr.Group(elem_classes="panel"):
                            gr.Markdown("### 算法说明（用了什么算法）")
                            algo_output = gr.Markdown(algorithm_doc_markdown())
                        with gr.Accordion("API 用量与成本（成本控制）", open=False):
                            usage_refresh_btn = gr.Button("刷新用量统计", elem_id="search-btn", variant="primary")
                            usage_output = gr.Markdown("点击刷新查看累计调用与估算成本")

        session_state = gr.State(None)
        screen_state = gr.State(None)   # 批量初筛本轮结果（含 by_label 反查）
        interview_queue = gr.State([])  # 初筛通过队列：[{screening_id, name, source, resume_text, total}]
        invite_state = gr.State(None)   # 待确认发送的通知：{iid, verdict, candidate}
        pending_state = gr.State(None)  # 待审核记录审核中：{iid, candidate, job}
        task_state = gr.State(None)     # 异步批处理任务 id（任务状态查询）

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
            inputs=[invite_input, invite_channel, chatbot, session_state, radar_plot, invite_state],
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
            inputs=[review_radio, review_comment, invite_input, pending_state, pending_stage],
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
        # ---- 岗位管理：保存规则 + 已配置列表 + 热词建议 ----
        job_save_btn.click(
            save_job_with_rules,
            inputs=[job_title_input, job_jd_input, job_rubric, job_edu, job_min_years, job_max_years, job_must_skills, job_max_salary, job_exclude, job_style],
            outputs=[job_save_output],
            show_progress="hidden",
        )
        hotword_btn.click(submit_hotword, inputs=[hotword_input, hotword_comment], outputs=[hotword_output], show_progress="hidden")
        demo.load(hotwords_markdown, outputs=[hotword_output], show_progress="hidden")
        demo.load(refresh_job_profile_list, outputs=[job_list_dropdown, job_detail_output], show_progress="hidden")
        job_list_refresh_btn.click(refresh_job_profile_list, outputs=[job_list_dropdown, job_detail_output], show_progress="hidden")
        job_list_dropdown.change(job_profile_detail, inputs=[job_list_dropdown], outputs=[job_detail_output], show_progress="hidden")
        # ---- 简历库：批量导入 + 候选人列表 + 全文检索 ----
        import_btn.click(import_resumes, inputs=[import_folder], outputs=[import_output])
        demo.load(refresh_candidate_statuses, outputs=[cand_status_filter], show_progress="hidden")
        demo.load(search_resume_library, inputs=[cand_search, cand_status_filter], outputs=[cand_table], show_progress="hidden")
        cand_refresh_btn.click(search_resume_library, inputs=[cand_search, cand_status_filter], outputs=[cand_table], show_progress="hidden")
        cand_search.submit(search_resume_library, inputs=[cand_search, cand_status_filter], outputs=[cand_table], show_progress="hidden")
        cand_status_filter.change(search_resume_library, inputs=[cand_search, cand_status_filter], outputs=[cand_table], show_progress="hidden")
        # ---- 智能初筛（从库 · 全算法链路）----
        demo.load(refresh_job_profile_list, outputs=[lib_job_dropdown, lib_screen_note], show_progress="hidden")
        lib_job_refresh_btn.click(refresh_job_profile_list, outputs=[lib_job_dropdown, lib_screen_note], show_progress="hidden")
        lib_screen_btn.click(
            run_library_screen,
            inputs=[lib_job_dropdown, lib_status_dropdown],
            outputs=[lib_screen_table, screen_state, lib_screen_status, lib_check, screen_check],
        )
        # 异步初筛：提交即返回，后台处理，完成自动推群通知
        lib_async_btn.click(
            submit_async_screen,
            inputs=[lib_job_dropdown, lib_status_dropdown],
            outputs=[lib_screen_status, task_state],
            show_progress="hidden",
        )
        lib_task_refresh_btn.click(batch_task_status, inputs=[task_state], outputs=[lib_task_output], show_progress="hidden")
        demo.load(batch_task_status, inputs=[task_state], outputs=[lib_task_output], show_progress="hidden")
        lib_queue_btn.click(
            send_library_to_queue,
            inputs=[lib_check, screen_state],
            outputs=[interview_queue, lib_screen_note],
            show_progress="hidden",
        )
        # ---- 评分卡查询 ----
        demo.load(refresh_scorecard_dropdown, outputs=[scorecard_dropdown], show_progress="hidden")
        scorecard_refresh_btn.click(refresh_scorecard_dropdown, outputs=[scorecard_dropdown], show_progress="hidden")
        scorecard_dropdown.change(score_card_markdown, inputs=[scorecard_dropdown], outputs=[scorecard_output], show_progress="hidden")
        # ---- 评分卡对比 ----
        demo.load(refresh_scorecard_dropdown, outputs=[card_a_dropdown], show_progress="hidden")
        demo.load(refresh_scorecard_dropdown, outputs=[card_b_dropdown], show_progress="hidden")
        card_refresh_btn.click(refresh_scorecard_dropdown, outputs=[card_a_dropdown], show_progress="hidden")
        card_refresh_btn.click(refresh_scorecard_dropdown, outputs=[card_b_dropdown], show_progress="hidden")
        card_compare_btn.click(
            compare_score_cards,
            inputs=[card_a_dropdown, card_b_dropdown],
            outputs=[card_compare_output],
            show_progress="hidden",
        )
        # ---- API 用量统计 ----
        demo.load(usage_markdown, outputs=[usage_output], show_progress="hidden")
        usage_refresh_btn.click(usage_markdown, outputs=[usage_output], show_progress="hidden")
        # ---- 全流程看板 ----
        demo.load(funnel_markdown, outputs=[funnel_output], show_progress="hidden")
        funnel_refresh_btn.click(funnel_markdown, outputs=[funnel_output], show_progress="hidden")
        demo.load(notifications_markdown, outputs=[notif_output], show_progress="hidden")
        notif_refresh_btn.click(notifications_markdown, outputs=[notif_output], show_progress="hidden")
        demo.load(offers_markdown, outputs=[offer_output], show_progress="hidden")
        offer_refresh_btn.click(offers_markdown, outputs=[offer_output], show_progress="hidden")
        # ---- 入职运营智能体 ----
        demo.load(refresh_onboarding_dropdown, outputs=[onboarding_dropdown], show_progress="hidden")
        onboarding_refresh_btn.click(refresh_onboarding_dropdown, outputs=[onboarding_dropdown], show_progress="hidden")
        onboarding_btn.click(run_onboarding, inputs=[onboarding_dropdown], outputs=[onboarding_output], show_progress="hidden")
        # 试用期绩效回传（数据飞轮闭环）
        demo.load(refresh_performance_dropdown, outputs=[perf_dropdown], show_progress="hidden")
        perf_btn.click(
            submit_performance,
            inputs=[perf_dropdown, perf_rating, perf_comment],
            outputs=[perf_output],
            show_progress="hidden",
        )

    return demo
