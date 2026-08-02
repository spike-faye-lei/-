// ============================================
// Tab5 我的（独立组件）
// ============================================
import { I18nDict } from '../utils/DataModels';
import { Theme } from '../utils/Theme';
import { zh } from '../utils/i18n/zh';
import { en } from '../utils/i18n/en';

@Component
export struct TabMe {
  @StorageLink('fontScale') @Watch('onSettingsChange') fontScale: number = 1
  @StorageLink('themeMode') @Watch('onSettingsChange') themeMode: string = 'system'
  @StorageLink('styleMode') @Watch('onSettingsChange') styleMode: string = 'glass'
  @StorageLink('language') @Watch('onSettingsChange') language: string = 'zh'
  @State themeTick: number = 0

  // 语言/主题/字体变化 → 强制组件重绘（@Builder 内容不随组件重绘，用 tick 兜底）
  onSettingsChange() {
    this.themeTick++
  }
  // 事件回调
  onBoard: () => void = () => {}
  onHistory: () => void = () => {}
  onGuidelines: () => void = () => {}
  onMembers: () => void = () => {}
  onFace: () => void = () => {}
  onSettings: () => void = () => {}
  onBody: () => void = () => {}
  onLeaderboard: () => void = () => {}

  i18n(): I18nDict {
    return this.language === 'zh' ? zh : en
  }

  @Builder
  SettingRow(title: string, desc: string, action: () => void) {
    Row() {
      Column() {
        Text(title).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.TEXT_SYS)
        Text(desc).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 2 })
      }
      .alignItems(HorizontalAlign.Start).layoutWeight(1)

      Text('›').fontFamily('Inter').fontSize(20).fontColor(Theme.TEXT_SYS_TERTIARY)
    }
    .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: 14, bottom: 14 })
    .onClick(() => action())
  }

  build() {
    Column({ space: Theme.SPACE_MD }) {
      Text(this.i18n().me).fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT_SYS)
        .width('100%').textAlign(TextAlign.Start)

      // 设置分组
      Column() {
                    Row() {
              Column() {
                Text(this.i18n().boardStatus).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.TEXT_SYS)
                Text(this.i18n().boardDesc).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 2 })
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)
              Text('›').fontFamily('Inter').fontSize(20).fontColor(Theme.TEXT_SYS_TERTIARY)
            }
            .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: 14, bottom: 14 })
            .onClick(() => this.onBoard())
        Divider().strokeWidth(0.5).color(Theme.BORDER).margin({ left: Theme.SPACE_MD })
                    Row() {
              Column() {
                Text(this.i18n().history).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.TEXT_SYS)
                Text(this.i18n().historyDesc).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 2 })
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)
              Text('›').fontFamily('Inter').fontSize(20).fontColor(Theme.TEXT_SYS_TERTIARY)
            }
            .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: 14, bottom: 14 })
            .onClick(() => this.onHistory())
        Divider().strokeWidth(0.5).color(Theme.BORDER).margin({ left: Theme.SPACE_MD })
                    Row() {
              Column() {
                Text(this.i18n().guidelines).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.TEXT_SYS)
                Text(this.i18n().guidelinesDesc).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 2 })
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)
              Text('›').fontFamily('Inter').fontSize(20).fontColor(Theme.TEXT_SYS_TERTIARY)
            }
            .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: 14, bottom: 14 })
            .onClick(() => this.onGuidelines())
        Divider().strokeWidth(0.5).color(Theme.BORDER).margin({ left: Theme.SPACE_MD })
                    Row() {
              Column() {
                Text(this.i18n().memberTitle).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.TEXT_SYS)
                Text(this.i18n().membersDesc).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 2 })
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)
              Text('›').fontFamily('Inter').fontSize(20).fontColor(Theme.TEXT_SYS_TERTIARY)
            }
            .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: 14, bottom: 14 })
            .onClick(() => this.onMembers())
        Divider().strokeWidth(0.5).color(Theme.BORDER).margin({ left: Theme.SPACE_MD })
                    Row() {
              Column() {
                Text(this.i18n().faceRecognition).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.TEXT_SYS)
                Text(this.i18n().faceDesc).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 2 })
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)
              Text('›').fontFamily('Inter').fontSize(20).fontColor(Theme.TEXT_SYS_TERTIARY)
            }
            .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: 14, bottom: 14 })
            .onClick(() => this.onFace())
        Divider().strokeWidth(0.5).color(Theme.BORDER).margin({ left: Theme.SPACE_MD })
                    Row() {
              Column() {
                Text(this.i18n().settings).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.TEXT_SYS)
                Text(this.i18n().settingsDesc).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 2 })
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)
              Text('›').fontFamily('Inter').fontSize(20).fontColor(Theme.TEXT_SYS_TERTIARY)
            }
            .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: 14, bottom: 14 })
            .onClick(() => this.onSettings())
        Divider().strokeWidth(0.5).color(Theme.BORDER).margin({ left: Theme.SPACE_MD })
                    Row() {
              Column() {
                Text(this.i18n().bodyData).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.TEXT_SYS)
                Text(this.i18n().bodyDataDesc).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 2 })
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)
              Text('›').fontFamily('Inter').fontSize(20).fontColor(Theme.TEXT_SYS_TERTIARY)
            }
            .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: 14, bottom: 14 })
            .onClick(() => this.onBody())
        Divider().strokeWidth(0.5).color(Theme.BORDER).margin({ left: Theme.SPACE_MD })
                    Row() {
              Column() {
                Text(this.i18n().leaderboard).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.TEXT_SYS)
                Text(this.i18n().rankLabel + ' / ' + this.i18n().days).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 2 })
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)
              Text('›').fontFamily('Inter').fontSize(20).fontColor(Theme.TEXT_SYS_TERTIARY)
            }
            .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: 14, bottom: 14 })
            .onClick(() => this.onLeaderboard())
      }
      .width('100%')
      .backgroundBlurStyle(BlurStyle.Thin, { colorMode: Theme.isDark() ? ThemeColorMode.DARK : ThemeColorMode.LIGHT }).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_MD)
      .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })

      // 关于
      Column() {
        Text(this.i18n().appName + ' v1.4').fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS)
        Text(this.i18n().aboutDesc)
          .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 4 })
      }
      .width('100%').padding(Theme.SPACE_LG)
      .backgroundBlurStyle(BlurStyle.Thin, { colorMode: Theme.isDark() ? ThemeColorMode.DARK : ThemeColorMode.LIGHT }).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_MD)
      .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
    }
    .width('100%').height('100%').padding(Theme.SPACE_LG)
    .opacity(this.themeTick >= 0 && this.fontScale > 0 && this.language !== '' && this.themeMode !== '' ? 1 : 1)
    .alignItems(HorizontalAlign.Start)
  }
}
