"""UI 主题与全局常量：CSS 设计 token、合规声明、静态资源路径"""
import os

ASSETS = os.path.join(os.path.dirname(__file__), "assets")

COMPLIANCE = (
    "**【合规】** 演示环境仅使用公开信息与内置模拟数据；生产环境须获得候选人授权同意，"
    "简历与对话数据仅用于招聘评估、加密存储于企业内网，候选人可随时要求删除（《个人信息保护法》）"
)

CSS = """
/* 注：不引入 Google Fonts（国内直连被墙会阻塞页面渲染），字体走系统栈 */

/* ===== 企业产品级设计 token（参考 Moka/飞书等中文企业工具：冷灰底 / 品牌色 / 细边分层） ===== */
:root {
  --bg-page: #F5F6F8;        /* 冷灰页面底（非纯白非暖米，企业工具质感） */
  --bg-panel: #FFFFFF;       /* 卡片白 */
  --bg-hover: #F1F2F5;       /* hover 表面 */
  --bg-input: #FFFFFF;       /* 输入框 */
  --text-1: #1A1D24;         /* 主文字（近黑带蓝灰） */
  --text-2: #5A6472;         /* 次级文字 */
  --text-3: #9AA3AF;         /* 占位/元信息 */
  --border-1: #E8EAEF;       /* hairline 细边（冷灰） */
  --border-2: #D4D8E0;       /* 略深细边 */
  --accent: #4F46E5;         /* 品牌强调色：indigo */
  --accent-hover: #4338CA;   /* 强调色 hover（深一档） */
  --accent-soft: #EEF0FE;    /* 强调色浅底（选中/激活态） */
  --success: #16A34A; --danger: #DC2626; --warning: #D97706;
  --r-sm: 8px; --r-md: 10px; --r-lg: 12px;
  --shadow-card: 0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 3px rgba(16, 24, 40, 0.03);
}

body { background: var(--bg-page) !important; }

.gradio-container {
  max-width: 1340px !important; margin: 0 auto !important; padding: 20px 24px 48px !important;
  background: transparent !important;
  font-family: -apple-system, "Segoe UI", "Noto Sans SC", "Microsoft YaHei", sans-serif !important;
  color: var(--text-1) !important;
  font-weight: 400;
  font-size: 13.5px;
}

/* 卡片：白底 + 细边 + 极轻阴影（分层靠阴影而非纯留白，层级更清晰） */
.panel, .gr-box, .form, .wrap, .gr-group {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border-1) !important;
  border-radius: var(--r-md) !important;
  box-shadow: var(--shadow-card) !important;
  padding: 16px 18px !important;
}
#left-col, #right-col { gap: 12px; }

/* 顶部工具条：白底细边横条（不再是横幅卡片），左侧品牌名 + 右侧流程指示 */
#banner {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border-1) !important;
  border-radius: var(--r-md) !important;
  box-shadow: var(--shadow-card) !important;
  padding: 14px 20px; margin-bottom: 14px;
  display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;
}
#banner h1 {
  margin: 0; font-size: 17px; font-weight: 700; letter-spacing: -0.01em; color: var(--text-1);
  display: flex; align-items: center; gap: 8px;
}
#banner h1::before {
  content: ""; width: 6px; height: 18px; border-radius: 3px;
  background: var(--accent); display: inline-block;
}
#banner p { margin: 2px 0 0 14px; font-size: 12px; color: var(--text-3); display: inline; }
#steps { display: flex; gap: 4px; flex-wrap: wrap; }
.step-chip {
  background: var(--bg-hover); border: none;
  border-radius: 6px; padding: 4px 10px; font-size: 11.5px; color: var(--text-2);
  font-variant-numeric: tabular-nums; white-space: nowrap;
}

/* Tab 栏：文字选中态 + 品牌色下划线（企业产品惯例） */
.gradio-container .tabs > div > button {
  font-size: 13.5px !important; font-weight: 500 !important; color: var(--text-2) !important;
  border: none !important; background: transparent !important;
  padding: 8px 14px !important; border-radius: 6px 6px 0 0 !important;
  transition: color .12s ease !important;
}
.gradio-container .tabs > div > button:hover { color: var(--text-1) !important; background: var(--bg-hover) !important; }
.gradio-container .tabs > div > button.selected {
  color: var(--accent) !important; font-weight: 600 !important;
  box-shadow: inset 0 -2px 0 var(--accent) !important;
}

/* 按钮：品牌色主按钮（企业产品惯例：动作即品牌色）+ 白底细边次按钮 */
#auto-btn, #start-btn, #send-btn, #search-btn {
  background: var(--accent) !important;
  border: none !important; color: #fff !important; font-weight: 500; border-radius: var(--r-sm) !important;
  transition: background .15s ease !important;
  cursor: pointer;
}
#auto-btn:hover, #start-btn:hover, #send-btn:hover, #search-btn:hover { background: var(--accent-hover) !important; }
#auto-btn { font-size: 13.5px; padding: 9px 14px !important; }
#review-btn {
  background: var(--bg-panel) !important; color: var(--text-1) !important;
  border: 1px solid var(--border-2) !important; font-weight: 500;
}
#review-btn:hover { background: var(--bg-hover) !important; }

/* 状态条：白底 + 左侧品牌色竖条（流程状态一眼可见） */
#status-bar {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border-1) !important; border-left: 3px solid var(--accent) !important;
  border-radius: var(--r-md) !important; padding: 9px 14px !important;
}
#status-bar p { margin: 0; font-size: 12.5px; color: var(--text-2); }

/* 聊天区：AI 白底细边 / 用户品牌色底白字 */
#chat { border-radius: var(--r-md) !important; background: var(--bg-panel) !important; border: 1px solid var(--border-1) !important; }
#chat .message.bot { background: var(--bg-panel) !important; border: 1px solid var(--border-1) !important; color: var(--text-1) !important; }
#chat .message.user { background: var(--accent) !important; color: #fff !important; }
#radar { border-radius: var(--r-md); background: var(--bg-panel); border: 1px solid var(--border-1); padding: 8px; }

/* 表单控件：细边 + 聚焦品牌色（可读性优先） */
.gradio-container label, .gradio-container .label, .gradio-container legend { color: var(--text-2) !important; font-weight: 500; font-size: 12.5px !important; }
.gradio-container h1, .gradio-container h2, .gradio-container h3, .gradio-container h4 { color: var(--text-1) !important; font-weight: 600 !important; letter-spacing: -0.01em !important; }
.gradio-container input, .gradio-container textarea, .gradio-container select {
  background: var(--bg-input) !important; color: var(--text-1) !important;
  border: 1px solid var(--border-2) !important; border-radius: var(--r-sm) !important;
  font-size: 13px !important;
}
.gradio-container input:focus, .gradio-container textarea:focus, .gradio-container select:focus {
  border-color: var(--accent) !important; box-shadow: 0 0 0 3px var(--accent-soft) !important;
}
.gradio-container input::placeholder, .gradio-container textarea::placeholder { color: var(--text-3) !important; }
.gradio-container .selected { background: var(--bg-hover) !important; }

/* 表格：表头加粗 + 行 hover 浅灰 + 行高舒适 */
.gradio-container table { font-size: 12.5px !important; }
.gradio-container table thead th {
  font-weight: 600 !important; color: var(--text-2) !important;
  background: var(--bg-hover) !important; padding: 8px 12px !important;
}
.gradio-container table tbody td { padding: 8px 12px !important; }
.gradio-container table tbody tr:hover { background: var(--bg-hover) !important; }

/* 折叠区（Accordion）标题：紧凑但清晰 */
.gradio-container .accordion { border: 1px solid var(--border-1) !important; border-radius: var(--r-md) !important; }
.gradio-container .accordion > button { color: var(--text-2) !important; font-weight: 500 !important; padding: 8px 12px !important; }
.gradio-container .accordion > button:hover { background: var(--bg-hover) !important; color: var(--text-1) !important; }

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
  --input-shadow-focus: 0 0 0 3px var(--accent-soft);
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

