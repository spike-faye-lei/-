// ============================================
// Tab2 营养概览（独立组件）
// @Prop 传入 fontScale/themeMode 等 → 变化时组件重绘，内部文字/颜色重新求值
// ============================================
import { HealthScoreResponse, I18nDict } from '../utils/DataModels';
import { Theme } from '../utils/Theme';
import { zh } from '../utils/i18n/zh';
import { en } from '../utils/i18n/en';

@Component
export struct TabNutrition {
  @StorageLink('fontScale') @Watch('onSettingsChange') fontScale: number = 1
  @StorageLink('themeMode') @Watch('onSettingsChange') themeMode: string = 'system'
  @StorageLink('styleMode') @Watch('onSettingsChange') styleMode: string = 'glass'
  @StorageLink('language') @Watch('onSettingsChange') language: string = 'zh'
  @State themeTick: number = 0

  // 语言/主题/字体变化 → 强制组件重绘（@Builder 内容不随组件重绘，用 tick 兜底）
  onSettingsChange() {
    this.themeTick++
  }
  @Prop healthScore: HealthScoreResponse | null = null
  @Prop todayCalories: string = '—'
  @Prop todayFoods: string = '—'
  // 事件回调
  onHistory: () => void = () => {}
  onNutrition: () => void = () => {}

  i18n(): I18nDict {
    return this.language === 'zh' ? zh : en
  }

  build() {
    Column({ space: Theme.SPACE_MD }) {
      Text(this.i18n().nutrition).fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT_SYS)
        .width('100%').textAlign(TextAlign.Start)

      // 健康评分卡
      if (this.healthScore && this.healthScore.score !== null) {
        Row() {
          Column() {
            Text(this.healthScore.score.toFixed(0)).fontFamily('Inter').fontSize(40).fontWeight(700).fontColor(Theme.PRIMARY)
            Text(this.i18n().healthScore).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 2 })
          }
          .alignItems(HorizontalAlign.Start).layoutWeight(1)

          Column() {
            Text(this.healthScore.level).fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT_SYS)
            Text(this.healthScore.message).fontFamily('Inter').fontSize(Theme.FONT_MICRO)
              .fontColor(Theme.TEXT_SYS_SECONDARY).margin({ top: 4 }).maxLines(2)
          }
          .alignItems(HorizontalAlign.End).layoutWeight(2)
        }
        .padding(Theme.SPACE_LG)
        .backgroundBlurStyle(BlurStyle.Thin, { colorMode: Theme.isDark() ? ThemeColorMode.DARK : ThemeColorMode.LIGHT }).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_LG)
        .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })

        // 评分维度明细
        ForEach(Object.keys(this.healthScore.dimensions), (k: string) => {
          Row() {
            Text(k).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_SECONDARY)
            Blank()
            Text(this.healthScore!.dimensions[k].score + '/' + this.healthScore!.dimensions[k].full)
              .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontWeight(600).fontColor(Theme.PRIMARY)
          }
          .width('100%').padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG, top: 6, bottom: 6 })
        })
      }

      // 热量大卡片
      Column() {
        Text(this.todayCalories).fontFamily('Inter').fontSize(44).fontWeight(700).fontColor(Theme.TEXT_SYS)
        Text(this.i18n().todayCalories + ' (kcal)').fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
          .margin({ top: 4 })
        Text(this.todayFoods.length > 0 ? this.todayFoods : this.i18n().emptyRecord)
          .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY).margin({ top: 10 })
          .maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
      }
      .padding(Theme.SPACE_LG)
      .backgroundBlurStyle(BlurStyle.Thin, { colorMode: Theme.isDark() ? ThemeColorMode.DARK : ThemeColorMode.LIGHT }).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_LG)
      .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })

      // 功能入口（内联卡片）
      Row({ space: Theme.SPACE_MD }) {
        Column() {
          Text(this.i18n().history).fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT_SYS)
          Text(this.i18n().historyDesc).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
            .margin({ top: 4 }).maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
        }
        .alignItems(HorizontalAlign.Start).layoutWeight(1)
        .padding(Theme.SPACE_MD)
        .backgroundBlurStyle(BlurStyle.Thin, { colorMode: Theme.isDark() ? ThemeColorMode.DARK : ThemeColorMode.LIGHT }).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_MD)
        .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
        .onClick(() => this.onHistory())

        Column() {
          Text(this.i18n().foodDetail).fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT_SYS)
          Text(this.i18n().nutritionDetail).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
            .margin({ top: 4 }).maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
        }
        .alignItems(HorizontalAlign.Start).layoutWeight(1)
        .padding(Theme.SPACE_MD)
        .backgroundBlurStyle(BlurStyle.Thin, { colorMode: Theme.isDark() ? ThemeColorMode.DARK : ThemeColorMode.LIGHT }).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_MD)
        .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
        .onClick(() => this.onNutrition())
      }.width('100%')
    }
    .width('100%').height('100%').padding(Theme.SPACE_LG)
    .opacity(this.themeTick >= 0 && this.fontScale > 0 && this.language !== '' && this.themeMode !== '' ? 1 : 1)
    .alignItems(HorizontalAlign.Start)
  }
}
