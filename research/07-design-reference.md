# 顶级暗色 SaaS 设计语言调研 · 重设计参考

> 调研日期：2026-08-06。对象：Linear / Vercel(Geist) / Raycast / Stripe
> 用途：recruit-agent（Python Gradio 招聘智能体，暗色主题）UI 重设计的可落地 token 参考
> 原则：只记录真实查证到的信息；多源交叉验证的标 ✓，单源第三方标 △，无法确认的如实说明

---

## 一、信息可信度说明

| 来源 | 类型 | 可信度 |
|---|---|---|
| Linear 官方品牌页 linear.app/brand、官方博客《How we redesigned the Linear UI》 | 官方 | 高 |
| ColorArchive 品牌色库（引用各官方 brand 页） | 第三方整理 | 高（引用官方） |
| PolarDesign_OpenSource 的 Linear DESIGN.md（GitHub） | 第三方逆向 | 中高（细节极全，与官方文章吻合） |
| Geist 设计系统文档（vercel.com/geist/*）+ 第三方整理的 geist-spec-dark.md | 官方 + 第三方 | 中高 |
| shadcn.io/design/raycast、design-ai DESIGN.md、refero/seedflip 等 | 第三方逆向 | 中 |
| designlang.app 的 Linear 分析 | 第三方自动分析 | **低**（其 primary #E4F222 黄色、accent #00FF05 与 Linear 实际明显不符，判定为 AI 误判，已弃用） |

**⚠️ 诚实声明**：
- 各家都没有公开完整 design token 文档（Linear/Vercel 只公开品牌色，Geist 文档页不含 hex 值），以下深色 UI 数值多来自第三方逆向（源码/截图分析），与官方公开信息一致的已交叉验证，其余标注 △。
- Stripe 官网抓取未获得任何色值，品牌色来自 ColorArchive 引用的官方品牌资源页；字体信息未查证到。

---

## 二、Linear —— 暗色 UI 天花板

### 2.1 品牌色（官方 brand 页 ✓ + ColorArchive ✓ 双源一致）

| 名称 | 色值 | 用途 |
|---|---|---|
| Linear Indigo | `#5E6AD2` | 品牌主色，仅用于 CTA 背景与品牌标识 |
| 暗背景 | `#08090A`（近黑，brand 页 meta theme-color 实测值） | 页面底色 |
| Linear Gray 1 | `#1C1D24` | 签名近黑表面色（深灰泛蓝） |
| 墨色 | `#222326`（Nordic Gray）、`#F4F5F8`（Mercury White） | 单色 logo 使用 |
| 强调紫 | `#7170FF`（open-design.ai △） | 链接、激活态、选中项 |

### 2.2 暗色 UI token（PolarDesign 逆向 △，与官方文章定性描述吻合）

**背景三阶**（原则：纯黑不用，全部带一点蓝灰）：

| 层级 | 色值 | 用途 |
|---|---|---|
| 页面底 | `#08090A` | 画布 |
| 面板/侧栏 | `#0F1011` | sidebar、panel |
| 卡片/浮层 | `#191A1B` | card、dropdown、elevated |
| hover 面 | `#28282C` | hover 态 |
| 模态遮罩 | `rgba(0,0,0,0.85)` | modal 背板 |

**文字四阶**（一级不用纯白 #FFF）：

| 层级 | 色值 | 用途 |
|---|---|---|
| 一级 | `#F7F8F8` | 正文主色 |
| 二级 | `#D0D6E0` | 说明、次要 |
| 三级 | `#8A8F98` | 占位、元信息 |
| 四级 | `#62666D` | 时间戳、禁用 |

**边框**（暗色下全部用半透明白，**绝不用不透明深色边框**）：

| 层级 | 色值 | 用途 |
|---|---|---|
| 细微 | `rgba(255,255,255,0.05)` | 默认分隔 |
| 标准 | `rgba(255,255,255,0.08)` | 卡片、输入框 |
| 强 | `rgba(255,255,255,0.12)` | hover/聚焦 |
| 实色（少用） | `#23252A` / `#34343A` | 大区块分隔 |

**强调色使用铁律**（官方文章 ✓：accents 克制、"limit chrome"）：
- indigo `#5E6AD2` 只出现在：主按钮、选中、品牌标记。**禁止装饰性使用**
- hover 亮化 `#828FFF`；激活 `#7170FF`
- 成功绿 `#27A644`（in-progress）、`#10B981`（完成徽章）——只做状态色
- 界面上 95% 是灰色系，彩色只出现在"需要用户注意的 1~2 个点"

**圆角**（逆向 △）：2px（徽章）/ 4px（小容器）/ 6px（按钮、输入框）/ 8px（卡片）/ 12px（面板）/ 22px（大面板）/ 9999px（chip）/ 50%（圆形图标钮）。

**阴影**：极轻，靠"表面亮度阶梯"分层而不是靠投影。hover 用 `rgba(0,0,0,0.03) 0 1.2px 0`，dialog 用多层 `rgba(0,0,0,0.04~0.08)` 极淡堆叠。焦点环 `rgba(0,0,0,0.1) 0 4px 12px`。

**按钮**：**没有实色按钮**，全部是半透明白填充：
- ghost：`rgba(255,255,255,0.02)` + `1px solid #24282C`
- subtle：`rgba(255,255,255,0.04)`
- 主按钮（indigo 实色）是唯一的"彩色时刻"

**字体**：Inter Variable（正文）+ Inter Display（大标题，官方文章 ✓）+ Berkeley Mono（代码）。字重只用 400/510/590，**禁止 700**。大字号负字距（72px 用 -1.584px），16px 以下正常字距。OpenType 特性 `cv01 ss03` 全局开启。

**间距**：8px 基数，8/16/24/32 节奏；内容最大宽 ~1200px；区块垂直留白 80px+。

**图标**：线性（stroke）风格、单色（fillDominant），无渐变图标。

---

## 三、Vercel / Geist —— 黑白极简几何

### 3.1 品牌色（ColorArchive ✓ 引官方 vercel.com/design）

| 名称 | 色值 |
|---|---|
| Vercel Black | `#000000`（主色） |
| Vercel White | `#FFFFFF` |
| Gray 1 | `#FAFAFA` |
| Vercel Blue | `#0070F3`（仅链接与 CTA，克制使用） |

### 3.2 Geist 暗色 token（vercel.com/geist 官方文档的 token 名 ✓ + 第三方整理的 dark spec △）

**背景**：暗色 `--ds-background-100 = #000000`（纯黑，页面与卡片同色），`--ds-background-200` 暗色下同为纯黑——**层级靠边框和灰度表面，不靠背景色差**。

**Gray 10 步全表（暗色）**：

| Token | 色值 | 语义角色 |
|---|---|---|
| gray-100 | `#1A1A1A` | 默认背景 |
| gray-200 | `#1F1F1F` | hover 背景 |
| gray-300 | `#292929` | active 背景 |
| gray-400 | `#2E2E2E` | 默认边框 |
| gray-500 | `#454545` | hover 边框 |
| gray-600 | `#878787` | active 边框 |
| gray-700 | `#8F8F8F` | 高对比填充 / 禁用文字 |
| gray-800 | `#7D7D7D` | 高对比 hover |
| gray-900 | `#A0A0A0` | 次要文字/图标 |
| gray-1000 | `#EDEDED` | 主要文字/图标 |

**Gray-alpha 10 步（暗色边框/分隔专用，半透明白）**：
`#FFFFFF12 / 17 / 21 / 24 / 3D / 82 / 8A / 78 / 9C / EB`（对应 100~1000）。**规则：暗色下边框一律用 alpha 白，不用实色 gray**。

**强调色**（语义=用途，非装饰）：
- Blue（链接/成功/焦点）：`#006EFE`（主）、`#47A8FF`（hover/焦点环）
- Red（错误）：`#E2162A`；Amber（警告）：`#FFAE00`；Green（成功）：`#00AC3A`
- 原则原文："A correct Geist screen is mostly gray with one purposeful accent."（正确的 Geist 页面是大部分灰 + 一个有意的强调色）

**圆角**（官方文档 ✓）：6px（基础/按钮/输入框）、12px（菜单/弹窗）、16px（全屏浮层）、9999px（pill）。**一个视图只用一个圆角族**。

**阴影（暗色，△）**：极轻。卡片 `0 1px 2px rgba(0,0,0,0.16)`；弹窗/菜单 `0 4px 8px -4px rgba(0,0,0,0.04), 0 16px 24px -8px rgba(0,0,0,0.06)`；模态再加 `0 24px 32px -8px` 层。焦点环双环：`0 0 0 2px #000, 0 0 0 4px #47A8FF`。

**按钮**（recipe △，已标注）：
- Primary：`#EDEDED` 底 + `#000` 字（**黑白反转**——白色按钮在纯黑上）
- Secondary：`#000` 底 + alpha 白边框
- 高 40px（小 32 / 大 48）、radius 6px、padding `0 10px`（输入框 `0 12px`）
- 禁用：`#1A1A1A` 底 + `#8F8F8F` 字

**字体**：Geist Sans（正文/UI）、Geist Mono（代码/数据表）、Geist Pixel（展示）；**fallback Inter**。每个视图最多 2 个字重。标题族 600 字重 + 随字号收紧的负字距（heading-72 = 72px/-4.32px）。

**间距**：4px 基数（4/8/12/16/24/32/40/64/96）；组内 8、组间 16、区块间 32~40；列宽上限 1200px；卡片内边距 24px。

---

## 四、Raycast —— 深色玻璃质感 + 键盘优先

### 4.1 两套语境 token（△，来源冲突处并列标注）

**A. 官网/营销站语境（shadcn.io 逆向）**：

| 类别 | 色值 |
|---|---|
| 画布 | `#07080A`（官网实测 ✓，meta 与 WebGL 配置确认） |
| 表面阶梯 | surface `#0D0D0D` → elevated `#101111` → card `#121212` |
| 文字 | ink `#F4F4F6` / body `#CDCDCD` / mute `#9C9C9D` |
| 边框 | hairline `#242728`（1px 每张卡边）+ soft `rgba(255,255,255,0.08)` + strong `0.16` |
| 强调 | 红 `#FF6161`、蓝 `#57C1FF`、绿 `#59D499`、黄 `#FFC533`（各配 `0.15` alpha 软底） |
| hero 红色对角渐变 | `#FF5757 → #A1131A`（每页最多出现一次，是 chrome 上唯一的彩色时刻） |

**B. macOS 应用面板语境（design-ai DESIGN.md 逆向）**：
- 背景 `#1C1C1E`（窗口 95% 不透明 + `blur(40px) saturate(1.8)` 背板模糊——玻璃质感的来源）
- 输入 `#0F0F10`、hover `#3A3A3C`、边框 `#3A3A3C`、窗口描边 `0.5px rgba(255,255,255,0.12)`
- 主强调红 `#FF6363`（dark `#E54545`）——**只用于激活行标题和光标，别无他用**
- 文字：白 `#FFFFFF` / 85% 白 / 40% 白
- 窗口阴影 `0 24px 64px rgba(0,0,0,0.7)`（唯一重阴影——悬浮面板用）
- 窗口固定宽 640px、输入高 54px、结果行高 44px

### 4.2 设计规则（高共识，多个来源一致）

- **零阴影系统（营销站）**：深度完全靠 4 阶表面阶梯，无 drop shadow；面板语境只有窗体外一圈重阴影
- **圆角**：xs 4（键帽）/ sm 6（行）/ md 8（按钮输入，基准）/ lg 10~12（卡片/窗口）/ xl 16（命令面板容器）/ full 9999px（pill）。**卡片绝不超过 16px**
- **字体**：Inter（`ss03` 单层 g 是品牌签名，site-wide 开启 `calt kern liga ss03`），代码 SF Mono/JetBrains Mono；正文用 **正字距**（+0.2~0.4px，与 Linear 相反，Raycast 更宽松）
- **键盘优先**：界面上没有主按钮——所有操作靠键盘；每行右侧都有 kbd 徽章（11px/500 字重）
- **CTA 唯一性**：只有一个主行动——白色 pill 按钮 `#FFFFFF`，没有第二主色
- **图标**：线性单色 SVG，无渐变
- **无 emoji、无装饰插画、无浅色背景**（明示规则）

---

## 五、Stripe —— 补充参考

（本次仅查证到品牌色，来源 ColorArchive 引 Stripe 官方品牌资源页 ✓；官网页面本身未抓到色值；字体信息未查证到，公开资料称其使用自研字体 Stripe Sans，未经本次验证）

| 名称 | 色值 | 备注 |
|---|---|---|
| Stripe Indigo（blurple） | `#635BFF` | 品牌主色——"技术感"而非金融"信任蓝" |
| Slate Navy | `#0A2540` | 深海军蓝，Stripe 暗色区域的底色 |
| Success Green | `#00D924` | 强调/成功 |
| Off White | `#F6F9FC` | 浅色背景 |

参考价值：暗色不用纯黑而用深海军蓝 `#0A2540` 是"品牌色微染背景"的范例；blurple 用在主 CTA 上极有辨识度。

---

## 六、提炼：暗色专业 SaaS 设计规范（可直接落地的 token 清单）

> 综合四家共识（多源一致处）：近黑底色不纯黑、白字不纯白、边框用半透明白、强调色只给 1~2 个点、圆角 6/8/12、零到极轻阴影、线性单色图标、无 emoji、无渐变装饰。下面给一套**推荐值**（以 Linear 体系为主干，标注出处产品）。

### 6.1 背景三阶（页面 / 卡片 / 输入框）

```css
--bg-page:   #08090A;   /* Linear ✓ 页面底，近黑带蓝灰 */
--bg-panel:  #0F1011;   /* Linear △ 侧栏/面板/导航 */
--bg-card:   #191A1B;   /* Linear △ 卡片、下拉、弹层 */
--bg-hover:  #28282C;   /* Linear △ hover 表面 */
--bg-input:  #0F1011;   /* Raycast △ 输入框比卡片更深（反直觉但专业） */
--bg-modal:  rgba(0,0,0,0.85);  /* Linear △ 模态遮罩 */
```

### 6.2 文字三阶（+1 辅助）

```css
--text-1: #F7F8F8;   /* Linear △ 主文字（非纯白） */
--text-2: #D0D6E0;   /* Linear △ 次级 */
--text-3: #8A8F98;   /* Linear △ 占位/元信息/禁用 */
--text-4: #62666D;   /* Linear △ 时间戳 */
```

### 6.3 边框（全半透明白）

```css
--border-1: rgba(255,255,255,0.05);  /* Linear △ 默认 */
--border-2: rgba(255,255,255,0.08);  /* Linear △ 卡片/输入 */
--border-3: rgba(255,255,255,0.12);  /* Linear △ hover/强 */
--hairline: 1px;                     /* Vercel/Geist 线宽 */
```

### 6.4 强调色（克制：全界面只用 1 个主强调 + 状态色）

```css
--accent:        #5E6AD2;  /* Linear ✓ indigo，仅主按钮/选中/链接 */
--accent-hover:  #828FFF;  /* Linear △ */
--accent-active: #7170FF;  /* Linear △ */
--success: #27A644;  --danger: #E2162A;  --warning: #FFAE00;  /* 仅状态 */
```

**用量规则（原文共识）**：页面 95% 灰色系；强调色只出现在"需要用户行动/注意的点"（主按钮、当前项、链接）。装饰性彩色 = AI 感来源之一。

### 6.5 字体栈

```css
/* 英文（三选一，都有官方出处）：
   Linear: Inter Variable + Inter Display  ✓
   Vercel: Geist Sans + Geist Mono（fallback Inter）✓
   Raycast: Inter（ss03 单层 g）✓
   推荐 Geist Sans 或 Inter + Geist Mono 代码 */
--font-sans: "Geist Sans", "Inter", -apple-system, "Segoe UI", sans-serif;
/* 中文 fallback（建议，未查证）：思源黑体优先，系统黑体兜底 */
--font-sans-cn: "Source Han Sans SC", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
--font-mono: "Geist Mono", "Berkeley Mono", ui-monospace, "SF Mono", "JetBrains Mono", Consolas, monospace;
```

**字重规范**：正文 400，强调 500~590，**禁止 700+**（Linear 官方规则 ✓）。大标题 500~600 + 负字距（随字号缩放），正文正常字距（Raycast 可选 +0.2px 宽松）。

### 6.6 圆角

```css
--r-xs: 2px;    /* Linear △ 徽章 */
--r-sm: 6px;    /* Linear/Geist ✓ 按钮、输入框（基准） */
--r-md: 8px;    /* Linear △ 卡片 */
--r-lg: 12px;   /* Linear/Geist ✓ 下拉、弹窗、面板 */
--r-xl: 16px;   /* Raycast/Geist ✓ 大浮层 */
--r-full: 9999px;  /* chip/标签/头像 */
```

规则：一个视图只用一个圆角族（Geist ✓）；卡片类 8~12px 是各家共识区间。

### 6.7 阴影（克制：暗色下投影几乎不可见，靠亮度分层）

```css
/* 卡片不投影或极轻 */
--shadow-card: 0 1px 2px rgba(0,0,0,0.16);            /* Geist dark △ */
--shadow-popover: 0 4px 8px -4px rgba(0,0,0,0.04),
                  0 16px 24px -8px rgba(0,0,0,0.06);  /* Geist dark △ */
--shadow-modal: 0 8px 16px -4px rgba(0,0,0,0.04),
                0 24px 32px -8px rgba(0,0,0,0.06);    /* Geist dark △ */
--shadow-window: 0 24px 64px rgba(0,0,0,0.7);         /* Raycast △ 仅悬浮窗 */
--focus-ring: 0 0 0 2px #08090A, 0 0 0 4px #5E6AD2;   /* Geist 双环式改 */
```

### 6.8 间距

```css
--space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
--space-6: 24px; --space-8: 32px; --space-10: 40px;
/* 组内 8、组间 16、区块 32~40、内容列宽上限 1200px、卡片内边距 24px（Geist ✓） */
```

### 6.9 按钮规范

```css
/* 主按钮（全界面唯一彩色点） */
--btn-primary-bg: #5E6AD2; --btn-primary-text: #FFFFFF;
--btn-primary-hover: #828FFF;
/* 次按钮：半透明填充 + alpha 边框（Linear △：rgba(255,255,255,0.04) + 0.08 边框） */
/* 高 36~40px、radius 6px、padding 0 12~16px、禁用 = 40% 透明度 */
```

### 6.10 图标规范（无 emoji）

- 线性（outline）风格，1.5px stroke，单色——**无渐变、无多色、无实心大面积**
- 默认继承 `--text-2`，强调/激活时用 accent 色
- 界面文本、状态提示、按钮里**一律不用 emoji**；成功/错误用图标 + 文字，不用彩色 emoji
- 推荐 lucide 图标库（线性风格，Gradio 5 内置即 lucide）

---

## 七、Gradio 落地映射（建议，变量名以 Gradio 5 主题系统为准）

Gradio 5 的主题 CSS 变量可直接覆盖，推荐映射：

```css
/* gradio theme css（Theme.add_css 或 custom CSS 文件） */
--body-background-fill: #08090A;          /* 页面底 */
--body-text-color: #F7F8F8;               /* 主文字 */
--block-background-fill: #191A1B;         /* 卡片 */
--block-border-width: 1px;
--block-border-color: rgba(255,255,255,0.08);
--block-radius: 8px;
--input-background-fill: #0F1011;         /* 输入框（比卡片深） */
--input-border-color: rgba(255,255,255,0.08);
--input-radius: 6px;
--button-primary-background-fill: #5E6AD2;
--button-primary-background-fill-hover: #828FFF;
--button-primary-text-color: #FFFFFF;
--button-primary-radius: 6px;
--button-secondary-background-fill: rgba(255,255,255,0.04);
--button-secondary-border-color: rgba(255,255,255,0.08);
--button-secondary-radius: 6px;
--border-color-primary: rgba(255,255,255,0.08);
--border-color-accent: #5E6AD2;
--shadow-drop: none;                      /* 卡片零投影 */
--shadow-drop-inset: none;
--link-text-color: #7170FF;
--heading-text-color: #F7F8F8;
--font-sans-serif: "Geist Sans", "Inter", "Source Han Sans SC", "Microsoft YaHei", sans-serif;
--font-mono: "Geist Mono", ui-monospace, Consolas, monospace;
```

落地注意：
1. Gradio 自带组件（chatbot 气泡、alert）自带浅色/彩色样式，需逐个覆盖或关闭（如 `--chatbot-bubble-background-fill` 类变量）
2. 状态徽章（成功/错误）只允许出现 1~2 个彩色点，其余全灰
3. 移除所有 emoji 文案与默认彩色图标

---

## 八、来源清单

- linear.app/brand（官方品牌页，暗色 #08090A、品牌蓝描述）
- linear.app/now/how-we-redesigned-the-linear-ui（官方，LCH 三变量主题、Inter Display）
- colorarchive.org/brands/linear、/brands/stripe、/brands/vercel（品牌色，引官方）
- github.com/beichenO2/PolarDesign_OpenSource .../linear-app/DESIGN.md（Linear token 逆向）
- vercel.com/geist（token 名、radius、字体）、vercel.com/geist/colors、/geist/materials
- github.com/tylergibbs1/evilrabbitdesin .../geist-system.md、geist-spec-dark.md（Geist 全表逆向）
- raycast.com（#07090A 背景、#FF162A 品牌红，页面实测）
- shadcn.io/design/raycast、github.com/Khalidabdi1/design-ai .../raycast/DESIGN.md（Raycast 两套 token）
- 未查证项：Stripe 字体、各产品 logo 细节；△ 项均为单源第三方逆向，落地前建议对照真实产品截图抽查
