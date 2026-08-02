// ============================================
// Tab3 菜谱概览（独立组件）
// ============================================
import { I18nDict } from '../utils/DataModels';
import { Theme } from '../utils/Theme';
import { zh } from '../utils/i18n/zh';
import { en } from '../utils/i18n/en';

@Component
export struct TabRecipes {
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
  onRecipes: () => void = () => {}
  onGuidelines: () => void = () => {}

  i18n(): I18nDict {
    return this.language === 'zh' ? zh : en
  }

  build() {
    Column({ space: Theme.SPACE_MD }) {
      Text(this.i18n().recipes).fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT_SYS)
        .width('100%').textAlign(TextAlign.Start)

      // 菜谱广场（内联卡片）
      Column() {
        Text(this.i18n().recipeSquare).fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT_SYS)
        Text(this.i18n().browseByMeal).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
          .margin({ top: 4 }).maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
      }
      .alignItems(HorizontalAlign.Start).layoutWeight(1)
      .padding(Theme.SPACE_MD)
      .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_MD)
      .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
      .onClick(() => this.onRecipes())

      // 膳食指南（内联卡片）
      Column() {
        Text(this.i18n().guidelines).fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT_SYS)
        Text(this.i18n().pagodaDesc).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
          .margin({ top: 4 }).maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
      }
      .alignItems(HorizontalAlign.Start).layoutWeight(1)
      .padding(Theme.SPACE_MD)
      .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_MD)
      .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
      .onClick(() => this.onGuidelines())

      // 灵感占位
      Column() {
        Text(this.i18n().eatWell).fontFamily('Inter').fontSize(16).fontColor(Theme.TEXT_SYS_SECONDARY)
        Text(this.i18n().eatWellDesc).fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
          .fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 6 })
      }
      .width('100%').padding(Theme.SPACE_XL)
      .backgroundColor(Theme.PRIMARY_LIGHT).borderRadius(Theme.RADIUS_LG)
    }
    .width('100%').height('100%').padding(Theme.SPACE_LG)
    .opacity(this.themeTick >= 0 && this.fontScale > 0 && this.language !== '' && this.themeMode !== '' ? 1 : 1)
    .alignItems(HorizontalAlign.Start)
  }
}
