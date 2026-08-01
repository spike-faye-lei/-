// ============================================
// SmartKitchen Design System (Material 3 + HarmonyOS)
// 统一设计变量：颜色 / 圆角 / 间距 / 字体
// ============================================

export class Theme {
  // —— 颜色 ——
  static readonly BG: string = '#F7F8FA'          // 页面背景（浅灰，纸面感）
  static readonly SURFACE: string = '#FFFFFF'     // 卡片表面
  static readonly PRIMARY: string = '#6366F1'     // 强调色 Indigo
  static readonly PRIMARY_DARK: string = '#4F46E5'
  static readonly PRIMARY_LIGHT: string = '#EEF2FF' // 强调色浅底
  static readonly TEXT: string = '#111827'        // 主文字
  static readonly TEXT_SECONDARY: string = '#6B7280' // 次文字
  static readonly TEXT_TERTIARY: string = '#9CA3AF' // 弱文字
  static readonly BORDER: string = '#F0F1F3'      // 极浅描边
  static readonly SUCCESS: string = '#10B981'
  static readonly DANGER: string = '#EF4444'
  static readonly WARNING: string = '#F59E0B'
  static readonly SHADOW: number = 8              // 卡片阴影模糊半径

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

  // —— 字号 ——
  static readonly FONT_TITLE: number = 28          // 大标题
  static readonly FONT_HEADING: number = 20        // 页面标题
  static readonly FONT_SUB: number = 16            // 卡片标题
  static readonly FONT_BODY: number = 14           // 正文
  static readonly FONT_CAPTION: number = 12        // 辅助文字
  static readonly FONT_MICRO: number = 10          // 标签

  // —— 卡片样式快捷方法（返回 border 参数）——
  // 注意：ArkTS 中 border/shadow 需在组件上单独链式调用
}
