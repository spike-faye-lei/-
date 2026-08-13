"""UI 主题与全局常量：CSS 设计 token、合规声明、静态资源路径"""
import os

ASSETS = os.path.join(os.path.dirname(__file__), "assets")

COMPLIANCE = (
    "**【合规】** 演示环境仅使用公开信息与内置模拟数据；生产环境须获得候选人授权同意，"
    "简历与对话数据仅用于招聘评估、加密存储于企业内网，候选人可随时要求删除（《个人信息保护法》）"
)

CSS = """
/* 注：不引入 Google Fonts（国内直连被墙会阻塞页面渲染），字体走系统栈 */

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
