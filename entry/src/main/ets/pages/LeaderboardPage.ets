// ============================================
// 健康排行榜：家庭成员健康评分排行
// ============================================
import { httpUtil } from '../utils/HttpUtil';
import { RankItem, I18nDict } from '../utils/DataModels';
import { Theme } from '../utils/Theme';
import { zh } from '../utils/i18n/zh';
import { en } from '../utils/i18n/en';

@Entry
@Component
struct LeaderboardPage {
  @StorageLink('themeMode') themeMode: string = 'system'
  @StorageLink('styleMode') styleMode: string = 'glass'
  @StorageLink('fontScale') fontScale: number = 1
  @StorageLink('language') language: string = 'zh'
  @State themeTick: number = 0
  @State ranking: RankItem[] = []
  @State loading: boolean = true
  @State statusMsg: string = ''
  @State refreshing: boolean = false

  i18n(): I18nDict {
    return this.language === 'zh' ? zh : en
  }

  onPageShow(): void {
    let mode = AppStorage.get<string>('themeMode') || 'system'
    let scale = AppStorage.get<number>('fontScale') || 1
    let lang = AppStorage.get<string>('language') || 'zh'
    if (mode !== this.themeMode) this.themeMode = mode
    if (scale !== this.fontScale) this.fontScale = scale
    if (lang !== this.language) this.language = lang
    this.themeTick++
  }

  aboutToAppear(): void {
    this.load()
  }

  async load(): Promise<void> {
    this.loading = true
    try {
      let resp = await httpUtil.getLeaderboard()
      this.ranking = resp.ranking
      this.statusMsg = ''
    } catch (e) {
      this.ranking = []
      this.statusMsg = '加载失败'
    }
    this.loading = false
    this.refreshing = false
  }

  goBack(): void {
    this.getUIContext().getRouter().back()
  }

  build() {
    Column() {
      // 顶栏
      Row() {
        Text(this.i18n().leaderboard)
          .fontFamily('Inter').fontSize(Theme.FONT_TITLE).fontWeight(700).fontColor(Theme.TEXT_SYS)
      }
      .width('100%')
      .padding({ top: 16, bottom: 8, left: Theme.SPACE_LG, right: Theme.SPACE_LG })

      Divider().strokeWidth(0.5).color(Theme.BORDER)

      Refresh({ refreshing: $$this.refreshing }) {
        Column() {
      if (this.loading) {
        Column() {
          LoadingProgress().width(32).height(32).color(Theme.PRIMARY)
          Text('加载排行榜...').fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_TERTIARY)
            .margin({ top: Theme.SPACE_SM })
        }.justifyContent(FlexAlign.Center).width('100%').layoutWeight(1)
      } else if (this.ranking.length > 0) {
        List() {
          ForEach(this.ranking, (item: RankItem, i: number) => {
            ListItem() {
              Row() {
                // 排名徽章（前三名彩色）
                Text('#' + item.rank)
                  .fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(700)
                  .fontColor(item.rank === 1 ? Theme.WARNING : item.rank === 2 ? Theme.PRIMARY : item.rank === 3 ? Theme.SUCCESS : Theme.TEXT_TERTIARY)
                  .width(44)

                // 成员名
                Text(item.member)
                  .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(600).fontColor(Theme.TEXT_SYS)
                  .layoutWeight(1).maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })

                // 分数 + 天数
                Column() {
                  Text(item.score.toFixed(0) + '')
                    .fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(700).fontColor(Theme.PRIMARY)
                  Text(item.days + ' ' + this.i18n().days)
                    .fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                    .margin({ top: 2 })
                }
                .alignItems(HorizontalAlign.End)
              }
              .width('100%').padding(Theme.SPACE_MD)
              .backgroundEffect(Theme.GLASS_EFFECT).border({ width: 0.5, color: Theme.GLASS_BORDER })
              .borderRadius(Theme.RADIUS_MD)
              .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
              .margin({ bottom: Theme.SPACE_SM, left: Theme.SPACE_MD, right: Theme.SPACE_MD })
              .opacity(this.fontScale > 0 ? 1 : 1)
            }
          })
        }
        .width('100%').layoutWeight(1).margin({ top: Theme.SPACE_SM })
      } else {
        Column() {
          Text(this.statusMsg.length > 0 ? this.statusMsg : '暂无排行数据')
            .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_TERTIARY)
        }
        .width('100%').layoutWeight(1).justifyContent(FlexAlign.Center)
      }
        }
      }
      .width('100%').layoutWeight(1)
      .onRefreshing(() => {
        this.refreshing = true
        this.load()
      })
    }
    .width('100%').height('100%').linearGradient(Theme.bgGradient(this.themeMode, this.styleMode))
    .opacity(this.themeTick >= 0 && this.fontScale > 0 ? 1 : 1)
  }
}
