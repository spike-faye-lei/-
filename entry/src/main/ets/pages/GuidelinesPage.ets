import router from '@ohos.router'
import { httpUtil } from '../utils/HttpUtil'
import { GuidelineResponse, GuidelineTarget, PagodaItem } from '../utils/DataModels'
import { Theme } from '../utils/Theme'

@Entry
@Component
struct GuidelinesPage {
  @State guidelines: GuidelineResponse | null = null
  @State activeGoal: string = 'maintain'
  @State isLoading: boolean = true
  @State statusMsg: string = '加载中...'

  aboutToAppear() {
    this.loadGuidelines()
  }

  async loadGuidelines() {
    this.isLoading = true
    try {
      this.guidelines = await httpUtil.getGuidelines(this.activeGoal)
      this.statusMsg = ''
    } catch (e) {
      this.statusMsg = '加载失败: ' + JSON.stringify(e)
    }
    this.isLoading = false
  }

  setGoal(goal: string) {
    this.activeGoal = goal
    this.loadGuidelines()
  }

  goBack() {
    router.back()
  }

  getGoalLabel(goal: string): string {
    switch (goal) {
      case 'maintain': return '保持体重'
      case 'lose': return '减重'
      case 'gain': return '增重'
      default: return goal
    }
  }

  getMealLabel(meal: string): string {
    switch (meal) {
      case 'breakfast': return '早餐 (30%)'
      case 'lunch': return '午餐 (40%)'
      case 'dinner': return '晚餐 (30%)'
      default: return meal
    }
  }

  @Builder
  buildNutrientRow(label: string, value: number, unit: string, color: string, total: number) {
    Column() {
      Row() {
        Text(label).fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SECONDARY).width(80)
        Text(value.toFixed(0) + ' ' + unit).fontSize(Theme.FONT_SUB).fontWeight(600)
          .fontColor(color).layoutWeight(1)
      }.width('100%')

      Row() {
        Row()
          .width((total > 0 ? value * 100 / total : 0).toFixed(0) + '%')
          .height(6).backgroundColor(color).borderRadius(Theme.RADIUS_FULL)
      }
      .width('100%').height(6).backgroundColor(Theme.BORDER).borderRadius(Theme.RADIUS_FULL)
      .margin({ top: Theme.SPACE_XS })
    }
    .width('100%').padding({ top: Theme.SPACE_SM, bottom: Theme.SPACE_SM })
  }

  build() {
    Column() {
      // 顶部导航 + 大标题
      Column() {
        Row() {
          Button() { Text('←').fontSize(18).fontColor(Theme.TEXT).fontWeight(600) }
            .type(ButtonType.Circle)
            .width(40).height(40)
            .backgroundColor(Theme.SURFACE)
            .border({ width: 1, color: Theme.BORDER })
            .onClick(() => this.goBack())
          Blank()
        }.width('100%')

        Text('膳食指南')
          .fontSize(Theme.FONT_TITLE).fontWeight(700).fontColor(Theme.TEXT)
          .margin({ top: Theme.SPACE_SM })
      }
      .width('100%')
      .padding({ top: Theme.SPACE_MD, bottom: Theme.SPACE_XS, left: Theme.SPACE_MD, right: Theme.SPACE_MD })

      // 目标切换
      Row() {
        ForEach(['maintain', 'lose', 'gain'], (goal: string) => {
          Button() {
            Text(this.getGoalLabel(goal))
              .fontSize(Theme.FONT_BODY)
              .fontColor(this.activeGoal === goal ? Theme.SURFACE : Theme.TEXT_SECONDARY)
              .fontWeight(this.activeGoal === goal ? 600 : 400)
          }
          .type(ButtonType.Capsule)
          .height(36)
          .backgroundColor(this.activeGoal === goal ? Theme.PRIMARY : Theme.SURFACE)
          .border({ width: 1, color: this.activeGoal === goal ? Theme.PRIMARY : Theme.BORDER })
          .margin({ right: Theme.SPACE_SM })
          .onClick(() => this.setGoal(goal))
        })
      }
      .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM })

      if (this.isLoading) {
        Column() {
          LoadingProgress().width(32).height(32).color(Theme.PRIMARY)
          Text('加载膳食指南...').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_TERTIARY)
            .margin({ top: Theme.SPACE_SM })
        }.justifyContent(FlexAlign.Center).width('100%').layoutWeight(1)
      } else if (this.guidelines) {
        Scroll() {
          Column() {
            // 每日总目标
            Text('每日推荐摄入')
              .fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT)
              .width('100%').padding({ left: Theme.SPACE_MD, top: Theme.SPACE_LG })

            Column() {
              this.buildNutrientRow('热量', this.guidelines.daily.calories, 'kcal', Theme.WARNING,
                this.guidelines.daily.calories)
              this.buildNutrientRow('蛋白质', this.guidelines.daily.protein_g, 'g', Theme.PRIMARY,
                this.guidelines.daily.calories)
              this.buildNutrientRow('脂肪', this.guidelines.daily.fat_g, 'g', Theme.PRIMARY_DARK,
                this.guidelines.daily.calories)
              this.buildNutrientRow('碳水', this.guidelines.daily.carbs_g, 'g', Theme.SUCCESS,
                this.guidelines.daily.calories)
              this.buildNutrientRow('膳食纤维', this.guidelines.daily.fiber_g, 'g', Theme.TEXT_TERTIARY,
                this.guidelines.daily.calories)
            }
            .width('100%').padding(Theme.SPACE_MD).backgroundColor(Theme.SURFACE)
            .borderRadius(Theme.RADIUS_MD)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            .margin({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM })

            // 宏量营养素比例
            Text('三大营养素供能比')
              .fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT)
              .width('100%').padding({ left: Theme.SPACE_MD, top: Theme.SPACE_LG })

            Row() {
              Column() {
                Text('蛋白质').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY)
                Text(this.guidelines.macro_ratio.protein_pct.toFixed(0) + '%')
                  .fontSize(Theme.FONT_HEADING).fontWeight(700).fontColor(Theme.PRIMARY)
              }
              .alignItems(HorizontalAlign.Center).layoutWeight(1)

              Column() {
                Text('脂肪').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY)
                Text(this.guidelines.macro_ratio.fat_pct.toFixed(0) + '%')
                  .fontSize(Theme.FONT_HEADING).fontWeight(700).fontColor(Theme.WARNING)
              }
              .alignItems(HorizontalAlign.Center).layoutWeight(1)

              Column() {
                Text('碳水').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY)
                Text(this.guidelines.macro_ratio.carbs_pct.toFixed(0) + '%')
                  .fontSize(Theme.FONT_HEADING).fontWeight(700).fontColor(Theme.SUCCESS)
              }
              .alignItems(HorizontalAlign.Center).layoutWeight(1)
            }
            .width('100%').padding(Theme.SPACE_MD).backgroundColor(Theme.SURFACE)
            .borderRadius(Theme.RADIUS_MD)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            .margin({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM })

            // 每餐分配
            Text('三餐热量分配')
              .fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT)
              .width('100%').padding({ left: Theme.SPACE_MD, top: Theme.SPACE_LG })

            Column() {
              ForEach(Object.keys(this.guidelines.meals), (meal: string) => {
                Row() {
                  Column() {
                    Text(this.getMealLabel(meal))
                      .fontSize(Theme.FONT_BODY).fontWeight(600).fontColor(Theme.TEXT)
                    Text((this.guidelines!.meals[meal] as GuidelineTarget).calories.toFixed(0) + ' kcal · P:' +
                      (this.guidelines!.meals[meal] as GuidelineTarget).protein_g.toFixed(0) +
                      'g F:' + (this.guidelines!.meals[meal] as GuidelineTarget).fat_g.toFixed(0) +
                      'g C:' + (this.guidelines!.meals[meal] as GuidelineTarget).carbs_g.toFixed(0) + 'g')
                      .fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY)
                      .margin({ top: Theme.SPACE_XS })
                  }
                  .alignItems(HorizontalAlign.Start).layoutWeight(1)
                }
                .width('100%').padding({ top: Theme.SPACE_SM, bottom: Theme.SPACE_SM })
                if (meal !== 'dinner') {
                  Divider().color(Theme.BORDER)
                }
              })
            }
            .width('100%').padding(Theme.SPACE_MD).backgroundColor(Theme.SURFACE)
            .borderRadius(Theme.RADIUS_MD)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            .margin({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM })

            // 膳食宝塔
            Text('中国居民膳食宝塔')
              .fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT)
              .width('100%').padding({ left: Theme.SPACE_MD, top: Theme.SPACE_LG })

            Column() {
              ForEach(Object.keys(this.guidelines.pagoda), (cat: string) => {
                Row() {
                  Text(cat).fontSize(Theme.FONT_BODY).fontWeight(600).fontColor(Theme.TEXT).width(80)
                  Text((this.guidelines!.pagoda[cat] as PagodaItem).min + '~' +
                    (this.guidelines!.pagoda[cat] as PagodaItem).max + ' ' +
                    (this.guidelines!.pagoda[cat] as PagodaItem).unit)
                    .fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SECONDARY).layoutWeight(1)
                }
                .width('100%').padding({ top: Theme.SPACE_SM, bottom: Theme.SPACE_SM })
              })
            }
            .width('100%').padding(Theme.SPACE_MD).backgroundColor(Theme.SURFACE)
            .borderRadius(Theme.RADIUS_MD)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            .margin({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM })

            // 数据来源
            Text('数据来源: ' + this.guidelines.source)
              .fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY)
              .width('100%')
              .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM, bottom: Theme.SPACE_LG })
          }
          .width('100%')
        }
        .width('100%').layoutWeight(1)
      } else {
        Column() {
          Text(this.statusMsg).fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_TERTIARY)
            .width('100%').textAlign(TextAlign.Center)
        }
        .width('100%').layoutWeight(1).justifyContent(FlexAlign.Center)
      }
    }
    .width('100%').height('100%').backgroundColor(Theme.BG)
  }
}
