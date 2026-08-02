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

  // —— 页面背景（传 themeMode + styleMode，让 build() 建立响应式依赖：切主题/切风格 → 组件重绘）——
  static bg(mode: string, style: string): string {
    if (mode === 'dark') return '#1F1E1D'
    // minimal = Claude 简约：暖米白
    if (style === 'minimal') return '#F7F5F0'
    // glass = 液态玻璃：更深的暖底，让半透明白卡片透出层次（玻璃感）
    return '#E7E1D5'
  }

  // —— 页面背景渐变（glass 模式：暖色渐变层次，半透明白卡片背后才有内容可透/可模糊，
  //    纯色背景上 backdropBlur 看不出玻璃感 —— 社区共识）——
  static bgGradient(mode: string, style: string): LinearGradientOptions {
    if (mode === 'dark') {
      return { angle: 135, colors: [['#1F1E1D', 0.0], ['#272420', 1.0]] }
    }
    if (style === 'minimal') {
      // 简约：两端同色 = 纯色暖米白
      return { angle: 135, colors: [['#F7F5F0', 0.0], ['#F7F5F0', 1.0]] }
    }
    // 玻璃：暖米白 → 暖沙色渐变，给玻璃卡片提供可透出的层次
    return { angle: 135, colors: [['#EDE6D8', 0.0], ['#DACFBE', 1.0]] }
  }

  // —— 字体缩放依赖哨兵：值恒为 1，仅用于让 build() 依赖 fontScale（缩放变化 → 强制重绘）——
  static scaleDep(scale: number): number {
    return scale > 0 ? 1 : 1
  }

  // —— 当前是否为 Claude 简约风格（minimal）——
  static isMinimal(): boolean {
    return (AppStorage.get<string>('styleMode') || 'glass') === 'minimal'
  }

  // —— 液态玻璃卡片（半透明白 + 背景模糊）—— 参考 Claude 设计双风格：
  //    glass   液态玻璃（Apple Liquid Glass 风）：半透明白 + 模糊 + 高光白边
  //    minimal Claude 简约风：纯白卡片 + 无模糊 + 细灰边
  // 风格：glass 液态玻璃（半透明+模糊）/ minimal Claude 简约（纯色无模糊）
  static get GLASS_BG(): string {
    if (Theme.isMinimal()) {
      // 简约卡片可见（学浅色简约：白卡片 / 暗色：深灰卡片），扁平无阴影
      return Theme.isDark() ? '#2A2928' : '#FFFFFF'
    }
    // 玻璃：低透明度让背景渐变透出（暗色 0.16 通透效果好，浅色对齐到 0.42）
    return Theme.isDark() ? 'rgba(255,255,255,0.16)' : 'rgba(255,255,255,0.42)'
  }
  static get GLASS_BLUR(): number {
    return Theme.isMinimal() ? 0 : 24
  }
  // 玻璃卡片描边：glass 高光白边 / minimal 细边框（学浅色简约：白卡配细边，暗色配细白边）
  static get GLASS_BORDER(): string {
    if (Theme.isMinimal()) {
      return Theme.isDark() ? 'rgba(255,255,255,0.10)' : 'rgba(0,0,0,0.06)'
    }
    return Theme.isDark() ? 'rgba(255,255,255,0.30)' : 'rgba(255,255,255,0.80)'
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
  // 卡片阴影：glass 柔影（深浅色都可见）/ minimal 无阴影（Claude 简约扁平）
  // 深色背景上黑色投影必须明显加深+加大半径，否则看不见
  static get SHADOW_COLOR(): string {
    if (Theme.isMinimal()) return 'rgba(0,0,0,0)'
    return Theme.isDark() ? '#66000000' : '#40000000'
  }
  static get SHADOW(): number { return Theme.isMinimal() ? 0 : (Theme.isDark() ? 10 : 8) }

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
