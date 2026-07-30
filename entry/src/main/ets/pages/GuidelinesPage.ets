import router from '@ohos.router'
import { httpUtil } from '../utils/HttpUtil'
import { GuidelineResponse, GuidelineTarget, PagodaItem } from '../utils/DataModels'

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

  getGoalIcon(goal: string): string {
    switch (goal) {
      case 'maintain': return '⚖'
      case 'lose': return '🔥'
      case 'gain': return '💪'
      default: return '📊'
    }
  }

  getMealIcon(meal: string): string {
    switch (meal) {
      case 'breakfast': return '🌅'
      case 'lunch': return '☀️'
      case 'dinner': return '🌙'
      default: return '🍽'
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
        Text(label).fontSize(13).fontColor('#5a6a7e').width(80)
        Text(value.toFixed(0) + ' ' + unit).fontSize(16).fontWeight(600)
          .fontColor(color).layoutWeight(1)
      }.width('100%')

      Row() {
        Row()
          .width((total > 0 ? value * 100 / total : 0).toFixed(0) + '%')
          .height(6).backgroundColor(color).borderRadius(3)
      }
      .width('100%').height(6).backgroundColor('#f0f2f5').borderRadius(3)
      .margin({ top: 4 })
    }
    .width('100%').padding({ top: 6, bottom: 6 })
  }

  build() {
    Column() {
      // 顶部
      Row() {
        Button() { Text('← 返回').fontSize(15).fontColor('#2a5f8f') }
          .type(ButtonType.Capsule).backgroundColor('transparent')
          .onClick(() => this.goBack())

        Text('膳食指南').fontSize(20).fontWeight(700).fontColor('#1a1a2e')
          .layoutWeight(1).textAlign(TextAlign.Center)
      }
      .width('100%').padding({ top: 16, bottom: 8, left: 12, right: 12 })

      // 目标切换
      Row() {
        ForEach(['maintain', 'lose', 'gain'], (goal: string) => {
          Button() {
            Text(this.getGoalIcon(goal) + ' ' + this.getGoalLabel(goal))
              .fontSize(13).fontColor(this.activeGoal === goal ? '#fff' : '#5a6a7e').fontWeight(this.activeGoal === goal ? 600 : 400)
          }
          .type(ButtonType.Capsule)
          .backgroundColor(this.activeGoal === goal ? '#2a5f8f' : '#f0f2f5')
          .height(36).margin({ right: 8 })
          .onClick(() => this.setGoal(goal))
        })
      }
      .width('100%').padding({ left: 20, right: 20, top: 12 })

      if (this.isLoading) {
        Column() {
          LoadingProgress().width(32).height(32)
          Text('加载膳食指南...').fontSize(14).fontColor('#8a9aaa').margin({ top: 12 })
        }.justifyContent(FlexAlign.Center).width('100%').layoutWeight(1)
      } else if (this.guidelines) {
        Scroll() {
          Column() {
            // 每日总目标
            Text('每日推荐摄入').fontSize(16).fontWeight(700).fontColor('#1a1a2e')
              .width('100%').padding({ left: 20, top: 16 })

            Column() {
              this.buildNutrientRow('热量', this.guidelines.daily.calories, 'kcal', '#c96f2e',
                this.guidelines.daily.calories)
              this.buildNutrientRow('蛋白质', this.guidelines.daily.protein_g, 'g', '#2a5f8f',
                this.guidelines.daily.calories)
              this.buildNutrientRow('脂肪', this.guidelines.daily.fat_g, 'g', '#f0a040',
                this.guidelines.daily.calories)
              this.buildNutrientRow('碳水', this.guidelines.daily.carbs_g, 'g', '#2d8a4e',
                this.guidelines.daily.calories)
              this.buildNutrientRow('膳食纤维', this.guidelines.daily.fiber_g, 'g', '#8a6dbf',
                this.guidelines.daily.calories)
            }
            .width('100%').padding(16).backgroundColor('#ffffff').borderRadius(12)
            .margin({ left: 20, right: 20, top: 8 })

            // 宏量营养素比例
            Text('三大营养素供能比').fontSize(16).fontWeight(700).fontColor('#1a1a2e')
              .width('100%').padding({ left: 20, top: 20 })

            Row() {
              Column() {
                Text('蛋白质').fontSize(12).fontColor('#8a9aaa')
                Text(this.guidelines.macro_ratio.protein_pct.toFixed(0) + '%')
                  .fontSize(20).fontWeight(700).fontColor('#2a5f8f')
              }
              .alignItems(HorizontalAlign.Center).layoutWeight(1)

              Column() {
                Text('脂肪').fontSize(12).fontColor('#8a9aaa')
                Text(this.guidelines.macro_ratio.fat_pct.toFixed(0) + '%')
                  .fontSize(20).fontWeight(700).fontColor('#f0a040')
              }
              .alignItems(HorizontalAlign.Center).layoutWeight(1)

              Column() {
                Text('碳水').fontSize(12).fontColor('#8a9aaa')
                Text(this.guidelines.macro_ratio.carbs_pct.toFixed(0) + '%')
                  .fontSize(20).fontWeight(700).fontColor('#2d8a4e')
              }
              .alignItems(HorizontalAlign.Center).layoutWeight(1)
            }
            .width('100%').padding(16).backgroundColor('#ffffff').borderRadius(12)
            .margin({ left: 20, right: 20, top: 8 })

            // 每餐分配
            Text('三餐热量分配').fontSize(16).fontWeight(700).fontColor('#1a1a2e')
              .width('100%').padding({ left: 20, top: 20 })

            Column() {
              ForEach(Object.keys(this.guidelines.meals), (meal: string) => {
                Row() {
                  Text(this.getMealIcon(meal)).fontSize(20)
                  Column() {
                    Text(this.getMealLabel(meal)).fontSize(14).fontWeight(600).fontColor('#1a1a2e')
                    Text((this.guidelines!.meals[meal] as GuidelineTarget).calories.toFixed(0) + ' kcal · P:' +
                      (this.guidelines!.meals[meal] as GuidelineTarget).protein_g.toFixed(0) +
                      'g F:' + (this.guidelines!.meals[meal] as GuidelineTarget).fat_g.toFixed(0) +
                      'g C:' + (this.guidelines!.meals[meal] as GuidelineTarget).carbs_g.toFixed(0) + 'g')
                      .fontSize(12).fontColor('#8a9aaa').margin({ top: 2 })
                  }
                  .alignItems(HorizontalAlign.Start).layoutWeight(1).margin({ left: 12 })
                }
                .width('100%').padding({ top: 10, bottom: 10 })
                if (meal !== 'dinner') {
                  Divider().width('100%')
                }
              })
            }
            .width('100%').padding(16).backgroundColor('#ffffff').borderRadius(12)
            .margin({ left: 20, right: 20, top: 8 })

            // 膳食宝塔
            Text('中国居民膳食宝塔').fontSize(16).fontWeight(700).fontColor('#1a1a2e')
              .width('100%').padding({ left: 20, top: 20 })

            Column() {
              ForEach(Object.keys(this.guidelines.pagoda), (cat: string) => {
                Row() {
                  Text(cat).fontSize(14).fontWeight(600).fontColor('#1a1a2e').width(80)
                  Text((this.guidelines!.pagoda[cat] as PagodaItem).min + '~' +
                    (this.guidelines!.pagoda[cat] as PagodaItem).max + ' ' +
                    (this.guidelines!.pagoda[cat] as PagodaItem).unit)
                    .fontSize(14).fontColor('#5a6a7e').layoutWeight(1)
                }
                .width('100%').padding({ top: 8, bottom: 8 })
              })
            }
            .width('100%').padding(16).backgroundColor('#ffffff').borderRadius(12)
            .margin({ left: 20, right: 20, top: 8 })

            // 数据来源
            Text('数据来源: ' + this.guidelines.source)
              .fontSize(11).fontColor('#b0b8c8')
              .width('100%').padding({ left: 20, right: 20, top: 12, bottom: 24 })
          }
          .width('100%')
        }
        .width('100%').layoutWeight(1)
      } else {
        Text(this.statusMsg).fontSize(14).fontColor('#8a9aaa').margin({ top: 100 })
      }
    }
    .width('100%').height('100%').backgroundColor('#f4f6f9')
  }
}
