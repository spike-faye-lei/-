import router from '@ohos.router';
import { httpUtil } from '../utils/HttpUtil';
import { HistoryRecord, HistoryResponse, I18nDict } from '../utils/DataModels';
import { Light, Dark, ThemeColors } from '../utils/Theme';
import { zh } from '../utils/i18n/zh';
import { en } from '../utils/i18n/en';

@Entry
@Component
struct HistoryPage {
  @StorageLink('isDark') isDark: boolean = false
  @StorageLink('language') language: string = 'zh'
  @State currentTheme: ThemeColors = Light
  @State i18n: I18nDict = zh
  @State records: HistoryRecord[] = []
  @State loading: boolean = true

  goBack(): void { router.back() }

  aboutToAppear(): void {
    this.currentTheme = this.isDark ? Dark : Light
    this.i18n = this.language === 'zh' ? zh : en
    this.loadHistory()
  }

  loadHistory(): void {
    httpUtil.get('/api/history?days=30').then((json: string): void => {
      let res: HistoryResponse = JSON.parse(json) as HistoryResponse
      this.records = res.records
      this.loading = false
    }).catch((): void => { this.loading = false })
  }

  build() {
    Column() {
      Row() {
        Text('← ' + this.i18n.back).fontSize(15).fontColor(this.currentTheme.accent)
          .onClick(() => { this.goBack() })
        Text(this.i18n.dietHistory).fontSize(18).fontWeight(600)
          .fontColor(this.currentTheme.text).layoutWeight(1).textAlign(TextAlign.Center)
        Text(this.i18n.reload).fontSize(13).fontColor(this.currentTheme.accent)
          .onClick(() => { this.loading = true; this.loadHistory() })
      }.width('100%').padding({ left: 16, right: 16, top: 16, bottom: 8 })

      if (this.loading) {
        Blank()
        Text(this.i18n.loading).fontSize(14).fontColor(this.currentTheme.textSecondary)
        Blank()
      } else if (this.records.length === 0) {
        Blank()
        Column() {
          Text(this.i18n.noRecords).fontSize(16).fontWeight(500).fontColor(this.currentTheme.textSecondary)
          Text(this.i18n.noRecordsHint).fontSize(12).fontColor(this.currentTheme.textHint).margin({ top: 6 })
        }
        Blank()
      } else {
        List() {
          ForEach(this.records, (item: HistoryRecord) => {
            ListItem() {
              Column() {
                Row() {
                  Text((item.food_name_cn || item.food_name))
                    .fontSize(15).fontWeight(500).fontColor(this.currentTheme.text)
                  Blank()
                  Text(item.calories + ' ' + this.i18n.kcal)
                    .fontSize(14).fontWeight(600).fontColor(this.currentTheme.accent)
                }.width('100%')

                Row() {
                  Text(item.weight_g + 'g').fontSize(11).fontColor(this.currentTheme.textHint)
                  Text('|').fontSize(11).fontColor(this.currentTheme.border).margin({ left: 8, right: 8 })
                  Text('P ' + item.protein_g + 'g').fontSize(11).fontColor(this.currentTheme.textHint)
                  Text('|').fontSize(11).fontColor(this.currentTheme.border).margin({ left: 8, right: 8 })
                  Text('F ' + item.fat_g + 'g').fontSize(11).fontColor(this.currentTheme.textHint)
                  Text('|').fontSize(11).fontColor(this.currentTheme.border).margin({ left: 8, right: 8 })
                  Text('C ' + item.carbs_g + 'g').fontSize(11).fontColor(this.currentTheme.textHint)
                }.width('100%').margin({ top: 6 })

                Text(item.created_at).fontSize(10).fontColor(this.currentTheme.textHint).margin({ top: 6 })
              }
              .width('100%').padding(14)
              .backgroundColor(this.currentTheme.card).borderRadius(8)
              .margin({ bottom: 4, left: 16, right: 16 })
            }
          })
        }
        .width('100%').layoutWeight(1)
      }
    }.width('100%').height('100%').backgroundColor(this.currentTheme.bg)
  }
}
