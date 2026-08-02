// ============================================
// SmartKitchen Design System (Material 3 + HarmonyOS)
// 统一设计变量：颜色 / 圆角 / 间距 / 字体
// 支持：浅色/深色/跟随系统  +  字体缩放（小/标准/大/特大）
// ============================================

export class Theme {
  // —— 主题模式（AppStorage: themeMode = light|dark|system）——
  static isDark(): boolean {
    let mode = AppStorage.get<string>('themeMode') || 'system'
    if (mode === 'dark') return true
    if (mode === 'light') return false
    // system: 跟随系统深浅色
    return AppStorage.get<boolean>('systemDark') || false
  }

  // —— 页面背景（传 themeMode 参数，让 build() 建立响应式依赖：切主题 → 组件重绘）——
  static bg(mode: string): string {
    return mode === 'dark' ? '#1F1E1D' : '#F7F5F0'
  }

  // —— 字体缩放依赖哨兵：值恒为 1，仅用于让 build() 依赖 fontScale（缩放变化 → 强制重绘）——
  static scaleDep(scale: number): number {
    return scale > 0 ? 1 : 1
  }

  // —— 液态玻璃卡片（半透明白 + 背景模糊）：背景深色时卡片自动变深灰、浅色时自动变白，
  //    不依赖主题刷新机制，随页面背景自动适配 ——
  // 风格：glass 液态玻璃（半透明+模糊）/ minimal Claude 简约（纯色无模糊）
  static get GLASS_BG(): string {
    if ((AppStorage.get<string>('styleMode') || 'glass') === 'minimal') {
      return Theme.isDark() ? '#2A2928' : '#FFFFFF'
    }
    return 'rgba(255,255,255,0.08)'
  }
  static get GLASS_BLUR(): number {
    return (AppStorage.get<string>('styleMode') || 'glass') === 'minimal' ? 0 : 24
  }
  // 玻璃卡片描边（浅色深灰细线 / 深色半透明白线，提升玻璃质感）
  static get GLASS_BORDER(): string {
    let style = AppStorage.get<string>('styleMode') || 'glass'
    if (style === 'minimal') {
      return Theme.isDark() ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)'
    }
    return Theme.isDark() ? 'rgba(255,255,255,0.18)' : 'rgba(0,0,0,0.06)'
  }

  // —— 文字色（系统资源，渲染引擎按 App 颜色模式自动解析，深浅色自动切换）——
  static readonly TEXT_SYS: Resource = $r('sys.color.ohos_id_color_text_primary')
  static readonly TEXT_SYS_SECONDARY: Resource = $r('sys.color.ohos_id_color_text_secondary')
  static readonly TEXT_SYS_TERTIARY: Resource = $r('sys.color.ohos_id_color_text_tertiary')

  // —— 字体缩放（AppStorage: fontScale = 0.85|1|1.15|1.3）——
  static scale(): number {
    return AppStorage.get<number>('fontScale') || 1
  }

  // —— 颜色（浅色 / 深色双套）——Claude 风格：暖米白 + 珊瑚橙 / 墨黑 + 亮珊瑚
  static get BG(): string { return Theme.isDark() ? '#1F1E1D' : '#F7F5F0' }
  static get SURFACE(): string { return Theme.isDark() ? '#2A2928' : '#FFFFFF' }
  static get PRIMARY(): string { return Theme.isDark() ? '#E8967A' : '#D97757' }
  static get PRIMARY_DARK(): string { return Theme.isDark() ? '#D97757' : '#C15F3C' }
  static get PRIMARY_LIGHT(): string { return Theme.isDark() ? '#3A2E2A' : '#F9E8E2' }
  static get TEXT(): string { return Theme.isDark() ? '#ECEAE7' : '#2D2A26' }
  static get TEXT_SECONDARY(): string { return Theme.isDark() ? '#A6A09A' : '#6F6A63' }
  static get TEXT_TERTIARY(): string { return Theme.isDark() ? '#7A746E' : '#9C948C' }
  static get BORDER(): string { return Theme.isDark() ? '#373533' : '#EDE8E1' }
  static get SUCCESS(): string { return Theme.isDark() ? '#34D399' : '#10B981' }
  static get SUCCESS_BG(): string { return Theme.isDark() ? '#14352B' : '#D1FAE5' }
  static get DANGER(): string { return Theme.isDark() ? '#F87171' : '#EF4444' }
  static get WARNING(): string { return Theme.isDark() ? '#FBBF24' : '#F59E0B' }
  // 主色底上的文字颜色（深色模式下 Theme.SURFACE 是深灰，配浅紫主色会看不清）
  static get ON_PRIMARY(): string { return '#FFFFFF' }
  static get SHADOW_COLOR(): string { return Theme.isDark() ? '#33000000' : '#11000000' }
  static get SHADOW(): number { return 6 }

  // —— 圆角 ——
  static readonly RADIUS_SM: number = 10
  static readonly RADIUS_MD: number = 14
  static readonly RADIUS_LG: number = 18
  static readonly RADIUS_FULL: number = 999

  // —— 间距（8pt 网格）——
  static readonly SPACE_XS: number = 4
  static readonly SPACE_SM: number = 8
  static readonly SPACE_MD: number = 16
  static readonly SPACE_LG: number = 24
  static readonly SPACE_XL: number = 32

  // —— 字号（随缩放系数）——
  static get FONT_TITLE(): number { return Math.round(28 * Theme.scale()) }
  static get FONT_HEADING(): number { return Math.round(20 * Theme.scale()) }
  static get FONT_SUB(): number { return Math.round(16 * Theme.scale()) }
  static get FONT_BODY(): number { return Math.round(14 * Theme.scale()) }
  static get FONT_CAPTION(): number { return Math.round(12 * Theme.scale()) }
  static get FONT_MICRO(): number { return Math.round(10 * Theme.scale()) }
  static get FONT_NUM(): number { return Math.round(24 * Theme.scale()) }
  static get FONT_BRAND(): number { return Math.round(24 * Theme.scale()) }
}
