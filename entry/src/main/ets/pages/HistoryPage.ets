import { httpUtil } from '../utils/HttpUtil';
import { HistoryRecord, HistoryResponse, I18nDict } from '../utils/DataModels';
import { Theme } from '../utils/Theme';
import { zh } from '../utils/i18n/zh';
import { en } from '../utils/i18n/en';

interface WeekBar {
  label: string
  calories: number
  height: number
}

@Entry
@Component
struct HistoryPage {
  @StorageLink('themeMode') themeMode: string = 'system'
  @StorageLink('styleMode') styleMode: string = 'glass'
  @StorageLink('fontScale') fontScale: number = 1
  @StorageLink('language') language: string = 'zh'
  // 页面每次显示时自增，强制整页重绘
  @State themeTick: number = 0
  @State i18n: I18nDict = zh
  @State records: HistoryRecord[] = []
  @State loading: boolean = true
  @State weekData: WeekBar[] = []
  @State refreshing: boolean = false

  goBack(): void {
    this.getUIContext().getRouter().back()
  }

  aboutToAppear(): void {
    this.i18n = this.language === 'zh' ? zh : en
    this.loadHistory()
  }

  onPageShow(): void {
    // 页面被压栈时收不到 AppStorage 通知，回到前台强制同步最新设置
    let mode = AppStorage.get<string>('themeMode') || 'system'
    let scale = AppStorage.get<number>('fontScale') || 1
    let lang = AppStorage.get<string>('language') || 'zh'
    if (mode !== this.themeMode) this.themeMode = mode
    if (scale !== this.fontScale) this.fontScale = scale
    if (lang !== this.language) this.language = lang
    let style = AppStorage.get<string>('styleMode') || 'glass'
    if (style !== this.styleMode) this.styleMode = style
    this.i18n = lang === 'zh' ? zh : en
    this.themeTick++
  }

  loadHistory(): void {
    httpUtil.get('/api/history?days=30').then((json: string): void => {
      let res: HistoryResponse = JSON.parse(json) as HistoryResponse
      this.records = res.records
      this.weekData = this.buildWeekData()
      this.loading = false
    }).catch((): void => {
      this.weekData = this.buildWeekData()
      this.loading = false
    })
    this.refreshing = false
  }

  // 近 7 天热量聚合（柱状图数据）
  buildWeekData(): WeekBar[] {
    let today = new Date()
    let days: WeekBar[] = []
    let keys: string[] = []
    for (let i = 6; i >= 0; i--) {
      let d = new Date(today.getTime() - i * 86400000)
      let key = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0')
      keys.push(key)
      days.push({ label: (d.getMonth() + 1) + '/' + d.getDate(), calories: 0, height: 0 })
    }
    let max = 0
    this.records.forEach((r: HistoryRecord) => {
      let date = r.created_at.substring(0, 10)
      for (let i = 0; i < 7; i++) {
        if (date === keys[i]) {
          days[i].calories += r.calories
          if (days[i].calories > max) max = days[i].calories
        }
      }
    })
    days.forEach((d: WeekBar) => {
      d.height = max > 0 ? Math.round(d.calories / max * 120) : 0
    })
    return days
  }

  build() {
    Column() {
      // 页面大标题
      Text(this.i18n.dietHistory)
        .fontFamily('Inter').fontSize(Theme.FONT_TITLE)
        .fontWeight(600)
        .fontColor(Theme.TEXT_SYS)
                .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, bottom: Theme.SPACE_SM })

      // 下拉刷新
      Refresh({ refreshing: $$this.refreshing }) {
        Column() {
      // 近 7 天热量趋势
      if (this.weekData.length > 0) {
        Column() {
          Text(this.i18n.weeklyTrend)
            .fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT_SYS)
            .width('100%').textAlign(TextAlign.Start)
            .padding({ left: Theme.SPACE_MD, top: Theme.SPACE_SM, bottom: Theme.SPACE_SM })

          Row() {
            ForEach(this.weekData, (d: WeekBar) => {
              Column() {
                Text(d.calories > 0 ? d.calories + '' : '')
                  .fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                Row().width(16).height(d.height)
                  .backgroundColor(d.calories > 0 ? Theme.PRIMARY : Theme.BORDER)
                  .borderRadius(4).margin({ top: 2 })
                Text(d.label)
                  .fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                  .margin({ top: 4 })
              }
              .layoutWeight(1).alignItems(HorizontalAlign.Center)
            })
          }
          .width('100%').height(160).alignItems(VerticalAlign.Bottom)
          .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, bottom: Theme.SPACE_SM })
        }
        .width('100%')
        .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_LG)
        .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
        .padding({ top: Theme.SPACE_SM })
        .margin({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, bottom: Theme.SPACE_MD })
      }

      if (this.loading) {
        Blank()
        Text(this.i18n.loading)
          .fontFamily('Inter').fontSize(Theme.FONT_BODY)
          .fontColor(Theme.TEXT_SYS_SECONDARY)
        Blank()
      } else if (this.records.length === 0) {
        Blank()
        Column() {
          Text(this.i18n.noRecords)
            .fontFamily('Inter').fontSize(Theme.FONT_SUB)
            .fontWeight(500)
            .fontColor(Theme.TEXT_SYS_SECONDARY)
          Text(this.i18n.noRecordsHint)
            .fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
            .fontColor(Theme.TEXT_SYS_TERTIARY)
            .margin({ top: Theme.SPACE_SM })
        }
        Blank()
      } else {
        List() {
          ForEach(this.records, (item: HistoryRecord) => {
            ListItem() {
              Column() {
                Row() {
                  Text((item.food_name_cn || item.food_name))
                    .fontFamily('Inter').fontSize(Theme.FONT_SUB)
                    .fontWeight(500)
                    .fontColor(Theme.TEXT_SYS)
                  Blank()
                  Text(item.calories + ' ' + this.i18n.kcal)
                    .fontFamily('Inter').fontSize(Theme.FONT_BODY)
                    .fontWeight(600)
                    .fontColor(Theme.PRIMARY)
                }
                .width('100%')

                Row() {
                  Text(item.weight_g + 'g')
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
                    .fontColor(Theme.TEXT_SYS_TERTIARY)
                  Text('|')
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
                    .fontColor(Theme.BORDER)
                    .margin({ left: Theme.SPACE_SM, right: Theme.SPACE_SM })
                  Text('P ' + item.protein_g + 'g')
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
                    .fontColor(Theme.TEXT_SYS_TERTIARY)
                  Text('|')
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
                    .fontColor(Theme.BORDER)
                    .margin({ left: Theme.SPACE_SM, right: Theme.SPACE_SM })
                  Text('F ' + item.fat_g + 'g')
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
                    .fontColor(Theme.TEXT_SYS_TERTIARY)
                  Text('|')
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
                    .fontColor(Theme.BORDER)
                    .margin({ left: Theme.SPACE_SM, right: Theme.SPACE_SM })
                  Text('C ' + item.carbs_g + 'g')
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
                    .fontColor(Theme.TEXT_SYS_TERTIARY)
                }
                .width('100%')
                .margin({ top: Theme.SPACE_SM })

                Text(item.created_at)
                  .fontFamily('Inter').fontSize(Theme.FONT_MICRO)
                  .fontColor(Theme.TEXT_SYS_TERTIARY)
                  .margin({ top: Theme.SPACE_SM })
              }
                            .padding(Theme.SPACE_MD)
              .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER })
              .borderRadius(Theme.RADIUS_MD)
              .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
              .opacity(this.fontScale > 0 ? 1 : 1)
              .margin({ bottom: Theme.SPACE_SM, left: Theme.SPACE_MD, right: Theme.SPACE_MD })
            }
          })
        }
        .width('100%')
        .layoutWeight(1)
      }
        }
      }
      .width('100%').layoutWeight(1)
      .onRefreshing(() => {
        this.refreshing = true
        this.loadHistory()
      })
    }
    .width('100%')
    .height('100%')
    .linearGradient(Theme.bgGradient(this.themeMode, this.styleMode))
    .opacity(this.themeTick >= 0 && this.fontScale > 0 ? 1 : 1)
  }
}
