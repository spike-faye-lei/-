// ============================================
// 系统栏（状态栏/导航栏）颜色同步工具
// 让系统栏与页面背景同色 → 无白边、沉浸式效果
// 用法: EntryAbility 启动时 init(window)，主题切换时 apply()
// ============================================
import { window } from '@kit.ArkUI';
import { ConfigurationConstant } from '@kit.AbilityKit';
import common from '@ohos.app.ability.common';
import { Theme } from './Theme';

export class SystemBar {
  static win: window.Window | null = null

  static init(w: window.Window) {
    SystemBar.win = w
    SystemBar.apply()
  }

  static apply() {
    if (!SystemBar.win) return
    let dark = Theme.isDark()
    let style = AppStorage.get<string>('styleMode') || 'glass'
    // 与页面背景同色：glass 浅色取渐变顶部色（页面渐变 135° 从顶部暖米白开始）
    let bg = dark ? '#1F1E1D' : (style === 'minimal' ? '#F7F5F0' : '#EDE6D8')
    let contentColor = dark ? '#FFFFFFFF' : '#FF000000'
    try {
      SystemBar.win.setWindowSystemBarProperties({
        statusBarColor: bg,
        navigationBarColor: bg,
        statusBarContentColor: contentColor,
        navigationBarContentColor: contentColor,
      })
    } catch (e) {
      // 某些设备不支持时静默
    }
  }

  // 应用级颜色模式：让系统资源（sys.color 文字色等）跟随 App 主题解析，
  // 否则 sys.color 永远按系统颜色模式解析，App 内部切深色时文字仍是黑色
  static applyColorMode(ctx: common.UIAbilityContext, mode: string) {
    let cm = mode === 'dark' ? ConfigurationConstant.ColorMode.COLOR_MODE_DARK :
      mode === 'light' ? ConfigurationConstant.ColorMode.COLOR_MODE_LIGHT :
        ConfigurationConstant.ColorMode.COLOR_MODE_NOT_SET
    try {
      ctx.getApplicationContext().setColorMode(cm)
    } catch (e) {
      // 忽略
    }
  }
}
