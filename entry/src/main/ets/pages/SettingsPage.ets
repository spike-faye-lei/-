import preferences from '@ohos.data.preferences';
import common from '@ohos.app.ability.common';
import { Theme } from '../utils/Theme';
import { I18nDict } from '../utils/DataModels';
import { zh } from '../utils/i18n/zh';
import { en } from '../utils/i18n/en';
import { SystemBar } from '../utils/SystemBar';

// ============================================
// 设置页 — 对标 iOS/鸿蒙系统设置
// 分组卡片列表：外观(Toggle) / 字体大小(点击循环切换) / 语言(点击切换)
// 所有设置点一下立即生效，自动保存
// ============================================

@Entry
@Component
struct SettingsPage {
  @StorageLink('themeMode') themeMode: string = 'system'
  @StorageLink('fontScale') fontScale: number = 1
  @StorageLink('language') language: string = 'zh'
  @StorageLink('styleMode') styleMode: string = 'glass'
  // 页面每次显示时自增，强制整页重绘
  @State themeTick: number = 0

  // 字体档位（点击循环切换）
  fontPickerValues: number[] = [0.85, 1, 1.15, 1.3]

  async aboutToAppear() {
    await this.loadSettings()
  }

  i18n(): I18nDict {
    return this.language === 'zh' ? zh : en
  }

  onPageShow() {
    // 从其它页面返回时同步最新设置
    let mode = AppStorage.get<string>('themeMode') || 'system'
    let scale = AppStorage.get<number>('fontScale') || 1
    let lang = AppStorage.get<string>('language') || 'zh'
    let style = AppStorage.get<string>('styleMode') || 'glass'
    if (mode !== this.themeMode) this.themeMode = mode
    if (scale !== this.fontScale) this.fontScale = scale
    if (lang !== this.language) this.language = lang
    if (style !== this.styleMode) this.styleMode = style
    this.themeTick++
  }

  async loadSettings() {
    try {
      let context = this.getUIContext().getHostContext() as common.UIAbilityContext
      let pref = await preferences.getPreferences(context, 'smartkitchen_settings')
      let mode = await pref.get('themeMode', 'system') as string
      let scale = await pref.get('fontScale', 1) as number
      let lang = await pref.get('language', 'zh') as string
      let style = await pref.get('styleMode', 'glass') as string
      this.themeMode = mode
      this.fontScale = scale
      this.language = lang
      this.styleMode = style
    } catch (e) {
      // 首次启动无设置文件
    }
  }

  async saveSetting(key: string, value: string | number) {
    AppStorage.setOrCreate(key, value)
    if (key === 'themeMode') {
      // 同步应用级颜色模式：sys.color 系统资源文字立即按新主题解析
      SystemBar.apply()
      try {
        let context = this.getUIContext().getHostContext() as common.UIAbilityContext
        SystemBar.applyColorMode(context, value as string)
      } catch (e) {
        // 忽略
      }
    }
    try {
      let context = this.getUIContext().getHostContext() as common.UIAbilityContext
      let pref = await preferences.getPreferences(context, 'smartkitchen_settings')
      await pref.put(key, value)
      await pref.flush()
    } catch (e) {
      // 持久化失败不影响本次会话
    }
  }

  // 点击立即循环切换字体大小（点一下换一档，即时生效）
  cycleFont() {
    let idx = this.fontPickerValues.indexOf(this.fontScale)
    if (idx < 0) idx = 1
    let next = this.fontPickerValues[(idx + 1) % this.fontPickerValues.length]
    this.fontScale = next
    this.saveSetting('fontScale', next)
  }

  // 当前主题描述
  themeDesc(): string {
    if (this.themeMode === 'dark') return '深色'
    if (this.themeMode === 'light') return '浅色'
    return '跟随系统'
  }

  // 当前字号描述
  fontDesc(): string {
    if (this.fontScale <= 0.9) return this.i18n().fontSmall
    if (this.fontScale >= 1.3) return this.i18n().fontXLarge
    if (this.fontScale >= 1.15) return this.i18n().fontLarge
    return this.i18n().fontStandard
  }

  // 当前语言描述
  langDesc(): string {
    return this.language === 'zh' ? '中文' : 'English'
  }

  // 当前界面风格描述（液态玻璃 / Claude 简约）
  styleDesc(): string {
    return this.styleMode === 'minimal' ? this.i18n().minimalStyle : this.i18n().glassStyle
  }

  // ===== 设置行（直接内联，不用 @Builder 传函数）=====

  @Builder
  SectionTitle(title: string, mode: string, scale: number, tick: number) {
    Text(title)
      .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY).letterSpacing(1)
      .width('100%').textAlign(TextAlign.Start)
      .padding({ top: Theme.SPACE_LG, bottom: Theme.SPACE_SM })
      .opacity(this.fontScale > 0 ? 1 : 1)
  }

  build() {
    Column() {
      // 顶栏（iOS 大标题风格）
      Row() {
        Text(this.i18n().settings).fontFamily('Inter').fontSize(Theme.FONT_TITLE).fontWeight(700).fontColor(Theme.TEXT_SYS)
      }
      .padding({ top: 16, bottom: 8, left: Theme.SPACE_LG, right: Theme.SPACE_LG })

      Divider().strokeWidth(0.5).color(Theme.BORDER)

      Scroll() {
        // 内容统一用左右 padding（不要用卡片 margin，否则 width('100%')+margin 会超出屏幕右侧）
        Column() {
          // ===== 外观分组 =====
          this.SectionTitle(this.i18n().appearance, this.themeMode, this.fontScale, this.themeTick)

          Column() {
            // 行1: 跟随系统开关
            Row() {
              Column() {
                Text(this.i18n().followSystem).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS)
                Text(this.i18n().followSystemDesc).fontFamily('Inter').fontSize(Theme.FONT_MICRO)
                  .fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 2 })
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)

              Toggle({ type: ToggleType.Switch, isOn: this.themeMode === 'system' })
                .selectedColor(Theme.PRIMARY)
                .onChange((isOn: boolean): void => {
                  if (isOn) {
                    this.themeMode = 'system'
                    this.saveSetting('themeMode', 'system')
                  } else if (this.themeMode === 'system') {
                    this.themeMode = 'light'
                    this.saveSetting('themeMode', 'light')
                  }
                })
            }
            .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: 10, bottom: 10 })

            Divider().strokeWidth(0.5).color(Theme.BORDER).margin({ left: Theme.SPACE_MD })

            // 行2: 深色模式开关
            Row() {
              Column() {
                Text(this.i18n().darkMode).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS)
                Text(this.i18n().darkModeDesc).fontFamily('Inter').fontSize(Theme.FONT_MICRO)
                  .fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 2 })
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)

              Toggle({ type: ToggleType.Switch, isOn: Theme.isDark() })
                .selectedColor(Theme.PRIMARY)
                .onChange((isOn: boolean): void => {
                  if (isOn) {
                    this.themeMode = 'dark'
                    this.saveSetting('themeMode', 'dark')
                  } else {
                    this.themeMode = 'light'
                    this.saveSetting('themeMode', 'light')
                  }
                })
            }
            .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: 10, bottom: 10 })

            Divider().strokeWidth(0.5).color(Theme.BORDER).margin({ left: Theme.SPACE_MD })

            // 行3: 界面风格（液态玻璃 / Claude 简约，点击切换，Theme.GLASS_* 全局生效）
            Row() {
              Column() {
                Text(this.i18n().styleMode).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS)
                Text(this.i18n().styleDesc).fontFamily('Inter').fontSize(Theme.FONT_MICRO)
                  .fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 2 })
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)

              Row() {
                Text(this.styleDesc()).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.PRIMARY)
                Text('›').fontFamily('Inter').fontSize(18).fontColor(Theme.TEXT_SYS_TERTIARY).margin({ left: 6 })
              }
              .margin({ left: Theme.SPACE_SM })
            }
            .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: 10, bottom: 10 })
            .onClick((): void => {
              // 先直写 AppStorage：@StorageLink 本地赋值在渲染期间可能被忽略
              //（切玻璃后立刻再点切回会失效），全局存储更新会通知所有 @StorageLink 刷新
              let next = AppStorage.get<string>('styleMode') === 'minimal' ? 'glass' : 'minimal'
              AppStorage.setOrCreate('styleMode', next)
              this.styleMode = next
              this.saveSetting('styleMode', next)
            })
          }
          .width('100%')
          .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_MD)
          .shadow({ radius: Theme.SHADOW, color: Theme.SHADOW_COLOR, offsetY: 2 })

          // ===== 字体大小分组 =====
          this.SectionTitle(this.i18n().fontSize, this.themeMode, this.fontScale, this.themeTick)

          Column() {
            // 行1: 字体大小（点击弹窗）
            Row() {
              Column() {
                Text(this.i18n().fontSize).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS)
                Text(this.i18n().fontSizeDesc).fontFamily('Inter').fontSize(Theme.FONT_MICRO)
                  .fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 2 })
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)

              Row() {
                Text(this.fontDesc()).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.PRIMARY)
                Text('›').fontFamily('Inter').fontSize(18).fontColor(Theme.TEXT_SYS_TERTIARY).margin({ left: 6 })
              }
              .margin({ left: Theme.SPACE_SM })
            }
            .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: 10, bottom: 10 })
            .onClick((): void => this.cycleFont())

            Divider().strokeWidth(0.5).color(Theme.BORDER).margin({ left: Theme.SPACE_MD })

            // 行2: 字体预览
            Column() {
              Text(this.i18n().fontPreview).fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT_SYS)
              Text(this.i18n().appName + ' · 今日营养 · 好好吃饭')
                .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY).margin({ top: 6 })
            }
            .width('100%').alignItems(HorizontalAlign.Start).padding(Theme.SPACE_MD)
          }
          .width('100%')
          .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_MD)
          .shadow({ radius: Theme.SHADOW, color: Theme.SHADOW_COLOR, offsetY: 2 })

          // ===== 语言分组 =====
          this.SectionTitle(this.i18n().language + ' Language', this.themeMode, this.fontScale, this.themeTick)

          Column() {
            Row() {
              Column() {
                Text(this.i18n().language).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS)
                Text(this.i18n().languageDesc).fontFamily('Inter').fontSize(Theme.FONT_MICRO)
                  .fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 2 })
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)

              Row() {
                Text(this.langDesc()).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.PRIMARY)
                Text('›').fontFamily('Inter').fontSize(18).fontColor(Theme.TEXT_SYS_TERTIARY).margin({ left: 6 })
              }
              .margin({ left: Theme.SPACE_SM })
            }
            .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: 10, bottom: 10 })
            .onClick((): void => {
              // 点击立即切换语言（不用弹窗确认）
              this.language = this.language === 'zh' ? 'en' : 'zh'
              this.saveSetting('language', this.language)
            })
          }
          .width('100%')
          .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_MD)
          .shadow({ radius: Theme.SHADOW, color: Theme.SHADOW_COLOR, offsetY: 2 })

          // ===== 关于分组 =====
          this.SectionTitle(this.i18n().about, this.themeMode, this.fontScale, this.themeTick)

          Column() {
            Row() {
              Text(this.i18n().appName).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS)
              Blank()
              Text('v1.4').fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
            }.width('100%')
            Divider().strokeWidth(0.5).color(Theme.BORDER).margin({ top: 10, bottom: 10 })
            Text('基于 CLIP 多模态预训练 · 知识蒸馏 · HarmonyOS')
              .fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
              .width('100%').textAlign(TextAlign.Start)
          }
          .padding(Theme.SPACE_MD)
          .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_MD)
          .shadow({ radius: Theme.SHADOW, color: Theme.SHADOW_COLOR, offsetY: 2 })

          Text(this.i18n().settingsAutoSave).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
            .padding({ top: Theme.SPACE_LG, bottom: 24 })
        }
        .padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG })
        .alignItems(HorizontalAlign.Start)
      }
      .width('100%').layoutWeight(1).scrollBar(BarState.Off)
    }
    .width('100%').height('100%').linearGradient(Theme.bgGradient(this.themeMode, this.styleMode))
    .opacity(this.themeTick >= 0 && this.fontScale > 0 ? 1 : 1)
  }
}
