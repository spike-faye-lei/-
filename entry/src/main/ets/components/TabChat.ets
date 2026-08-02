// ============================================
// Tab4 助手（独立组件）
// ============================================
import { I18nDict } from '../utils/DataModels';
import { Theme } from '../utils/Theme';
import { zh } from '../utils/i18n/zh';
import { en } from '../utils/i18n/en';

@Component
export struct TabChat {
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
  onChat: () => void = () => {}

  i18n(): I18nDict {
    return this.language === 'zh' ? zh : en
  }

  build() {
    Column({ space: Theme.SPACE_MD }) {
      Text('AI ' + this.i18n().assistant).fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT_SYS)
        .width('100%').textAlign(TextAlign.Start)

      // 入口大卡片
      Column() {
        Text(this.i18n().askNutritionist).fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT_SYS)
        Text(this.i18n().chatDesc)
          .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY).margin({ top: 6 }).lineHeight(20)

        Button() {
          Text(this.i18n().startChat + ' ›').fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.ON_PRIMARY)
        }
        .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY).linearGradient({ angle: 135, colors: [['#E8967A', 0.0], ['#D97757', 1.0]] }).height(42)
        .margin({ top: Theme.SPACE_MD })
        .onClick(() => this.onChat())
      }
      .width('100%').padding(Theme.SPACE_LG)
      .backgroundEffect(Theme.GLASS_EFFECT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_LG)
      .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })

      // 示例问题
      Text(this.i18n().tryAsking).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
        .width('100%').textAlign(TextAlign.Start)

      ForEach([this.i18n().q1, this.i18n().q2, this.i18n().q3], (q: string) => {
        Row() {
          Text(q).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS)
          Text('›').fontFamily('Inter').fontSize(18).fontColor(Theme.TEXT_SYS_TERTIARY)
        }
        .width('100%').padding(Theme.SPACE_MD)
        .backgroundEffect(Theme.GLASS_EFFECT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_MD)
        .shadow({ radius: 4, color: '#08000000', offsetY: 1 })
        .onClick(() => this.onChat())
      })
    }
    .width('100%').height('100%').padding(Theme.SPACE_LG)
    .opacity(this.themeTick >= 0 && this.fontScale > 0 && this.language !== '' && this.themeMode !== '' ? 1 : 1)
    .alignItems(HorizontalAlign.Start)
  }
}
