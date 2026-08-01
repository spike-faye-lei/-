import router from '@ohos.router';
import { httpUtil } from '../utils/HttpUtil';
import { HistoryRecord, HistoryResponse, I18nDict } from '../utils/DataModels';
import { Theme } from '../utils/Theme';
import { zh } from '../utils/i18n/zh';
import { en } from '../utils/i18n/en';

@Entry
@Component
struct HistoryPage {
  @StorageLink('language') language: string = 'zh'
  @State i18n: I18nDict = zh
  @State records: HistoryRecord[] = []
  @State loading: boolean = true

  goBack(): void {
    router.back()
  }

  aboutToAppear(): void {
    this.i18n = this.language === 'zh' ? zh : en
    this.loadHistory()
  }

  loadHistory(): void {
    httpUtil.get('/api/history?days=30').then((json: string): void => {
      let res: HistoryResponse = JSON.parse(json) as HistoryResponse
      this.records = res.records
      this.loading = false
    }).catch((): void => {
      this.loading = false
    })
  }

  build() {
    Column() {
      // 顶部导航：返回 + 刷新
      Row() {
        Text(this.i18n.back)
          .fontSize(Theme.FONT_BODY)
          .fontWeight(500)
          .fontColor(Theme.PRIMARY)
          .onClick((): void => {
            this.goBack()
          })
        Blank()
        Button(this.i18n.reload)
          .fontSize(Theme.FONT_CAPTION)
          .fontWeight(500)
          .fontColor(Theme.PRIMARY)
          .backgroundColor(Theme.PRIMARY_LIGHT)
          .borderRadius(Theme.RADIUS_FULL)
          .height(32)
          .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD })
          .onClick((): void => {
            this.loading = true
            this.loadHistory()
          })
      }
      .width('100%')
      .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_MD, bottom: Theme.SPACE_XS })

      // 页面大标题
      Text(this.i18n.dietHistory)
        .fontSize(Theme.FONT_TITLE)
        .fontWeight(600)
        .fontColor(Theme.TEXT)
        .width('100%')
        .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, bottom: Theme.SPACE_SM })

      if (this.loading) {
        Blank()
        Text(this.i18n.loading)
          .fontSize(Theme.FONT_BODY)
          .fontColor(Theme.TEXT_SECONDARY)
        Blank()
      } else if (this.records.length === 0) {
        Blank()
        Column() {
          Text(this.i18n.noRecords)
            .fontSize(Theme.FONT_SUB)
            .fontWeight(500)
            .fontColor(Theme.TEXT_SECONDARY)
          Text(this.i18n.noRecordsHint)
            .fontSize(Theme.FONT_CAPTION)
            .fontColor(Theme.TEXT_TERTIARY)
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
                    .fontSize(Theme.FONT_SUB)
                    .fontWeight(500)
                    .fontColor(Theme.TEXT)
                  Blank()
                  Text(item.calories + ' ' + this.i18n.kcal)
                    .fontSize(Theme.FONT_BODY)
                    .fontWeight(600)
                    .fontColor(Theme.PRIMARY)
                }
                .width('100%')

                Row() {
                  Text(item.weight_g + 'g')
                    .fontSize(Theme.FONT_CAPTION)
                    .fontColor(Theme.TEXT_TERTIARY)
                  Text('|')
                    .fontSize(Theme.FONT_CAPTION)
                    .fontColor(Theme.BORDER)
                    .margin({ left: Theme.SPACE_SM, right: Theme.SPACE_SM })
                  Text('P ' + item.protein_g + 'g')
                    .fontSize(Theme.FONT_CAPTION)
                    .fontColor(Theme.TEXT_TERTIARY)
                  Text('|')
                    .fontSize(Theme.FONT_CAPTION)
                    .fontColor(Theme.BORDER)
                    .margin({ left: Theme.SPACE_SM, right: Theme.SPACE_SM })
                  Text('F ' + item.fat_g + 'g')
                    .fontSize(Theme.FONT_CAPTION)
                    .fontColor(Theme.TEXT_TERTIARY)
                  Text('|')
                    .fontSize(Theme.FONT_CAPTION)
                    .fontColor(Theme.BORDER)
                    .margin({ left: Theme.SPACE_SM, right: Theme.SPACE_SM })
                  Text('C ' + item.carbs_g + 'g')
                    .fontSize(Theme.FONT_CAPTION)
                    .fontColor(Theme.TEXT_TERTIARY)
                }
                .width('100%')
                .margin({ top: Theme.SPACE_SM })

                Text(item.created_at)
                  .fontSize(Theme.FONT_MICRO)
                  .fontColor(Theme.TEXT_TERTIARY)
                  .margin({ top: Theme.SPACE_SM })
              }
              .width('100%')
              .padding(Theme.SPACE_MD)
              .backgroundColor(Theme.SURFACE)
              .borderRadius(Theme.RADIUS_MD)
              .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
              .margin({ bottom: Theme.SPACE_SM, left: Theme.SPACE_MD, right: Theme.SPACE_MD })
            }
          })
        }
        .width('100%')
        .layoutWeight(1)
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG)
  }
}
