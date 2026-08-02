import { httpUtil } from '../utils/HttpUtil'
import { GuidelineResponse, GuidelineTarget, MacroRatio, PagodaItem, I18nDict, AppStorage as DataStore } from '../utils/DataModels'
import preferences from '@ohos.data.preferences'
import common from '@ohos.app.ability.common'
import { zh } from '../utils/i18n/zh'
import { en } from '../utils/i18n/en'
import { Theme } from '../utils/Theme'
import { LocalData } from '../utils/LocalData'

@Entry
@Component
struct GuidelinesPage {
  @StorageLink('themeMode') themeMode: string = 'system'
  @StorageLink('styleMode') styleMode: string = 'glass'
  @StorageLink('fontScale') fontScale: number = 1
  @StorageLink('language') language: string = 'zh'
  // 页面每次显示时自增，强制整页重绘
  @State themeTick: number = 0
  @State guidelines: GuidelineResponse | null = null
  @State activeGoal: string = 'maintain'
  @State age: number = 30
  @State memberName: string = 'default'
  @State statusBmi: number = 0
  @State statusLevel: string = ''
  @State statusCal: string = ''
  @State statusFoods: string = ''
  @State hasProfile: boolean = false
  @State isLoading: boolean = true
  @State statusMsg: string = '加载中...'

  aboutToAppear() {
    this.loadMemberGoal()
    this.loadMemberProfile()
    this.loadGuidelines()
  }

  // 按年龄段计算每日能量（中国居民膳食指南 2022 各年龄段能量推荐，取中值）
  ageEnergy(age: number): number {
    if (age < 6) return 1100
    if (age < 11) return 1300 + (age - 6) * 50
    if (age < 14) return 1550 + (age - 11) * 130
    if (age < 18) return 1950 + (age - 14) * 150
    if (age < 30) return 2100
    if (age < 50) return 2050
    if (age < 65) return 1950
    if (age < 80) return 1850
    return 1800
  }

  // 按年龄 + 健康目标计算每日营养目标
  calcDaily(age: number, goal: string): GuidelineTarget {
    let base = this.ageEnergy(age)
    if (goal === 'lose') base -= 500
    else if (goal === 'gain') base += 500
    base = Math.max(1200, base)
    return {
      calories: base,
      protein_g: Math.round(base * 0.15 / 4),
      fat_g: Math.round(base * 0.25 / 9),
      carbs_g: Math.round(base * 0.55 / 4),
      fiber_g: Math.round(base / 1000 * 14)
    }
  }

  // 宏量营养素供能比
  macroRatio(): MacroRatio {
    let d = this.calcDaily(this.age, this.activeGoal)
    return {
      protein_pct: Math.round(d.protein_g * 4 / d.calories * 1000) / 10,
      fat_pct: Math.round(d.fat_g * 9 / d.calories * 1000) / 10,
      carbs_pct: Math.round(d.carbs_g * 4 / d.calories * 1000) / 10
    }
  }

  // 三餐分配（早 30% 午 40% 晚 30%）
  mealTarget(meal: string): GuidelineTarget {
    let d = this.calcDaily(this.age, this.activeGoal)
    let ratio = meal === 'breakfast' ? 0.3 : meal === 'lunch' ? 0.4 : 0.3
    return {
      calories: Math.round(d.calories * ratio),
      protein_g: Math.round(d.protein_g * ratio * 10) / 10,
      fat_g: Math.round(d.fat_g * ratio * 10) / 10,
      carbs_g: Math.round(d.carbs_g * ratio * 10) / 10,
      fiber_g: Math.round(d.fiber_g * ratio * 10) / 10
    }
  }

  // 读取成员身体档案（身体数据分析保存的：BMI/分级/定制方案）
  async loadMemberProfile(): Promise<void> {
    this.memberName = DataStore.currentMember
    try {
      let ctx = this.getUIContext().getHostContext() as common.UIAbilityContext
      let pref = await preferences.getPreferences(ctx, 'smartkitchen_settings')
      let bmi = await pref.get('body_bmi_' + this.memberName, 0) as number
      let level = await pref.get('body_level_' + this.memberName, '') as string
      let cal = await pref.get('body_cal_' + this.memberName, '') as string
      let foods = await pref.get('body_foods_' + this.memberName, '') as string
      if (bmi > 0) {
        this.statusBmi = bmi
        this.statusLevel = level
        this.statusCal = cal
        this.statusFoods = foods
        this.hasProfile = true
      } else {
        this.hasProfile = false
      }
    } catch (e) {
      this.hasProfile = false
    }
  }

  // 读取成员健康目标（身体数据分析里应用的目标）
  async loadMemberGoal(): Promise<void> {
    try {
      let ctx = this.getUIContext().getHostContext() as common.UIAbilityContext
      let pref = await preferences.getPreferences(ctx, 'smartkitchen_settings')
      let goal = await pref.get('body_goal_' + DataStore.currentMember, 'maintain') as string
      this.activeGoal = goal
    } catch (e) {
      // 忽略
    }
  }

  i18n(): I18nDict {
    return this.language === 'zh' ? zh : en
  }

  onPageShow() {
    // 页面被压栈时收不到 AppStorage 通知，回到前台强制同步最新设置
    let mode = AppStorage.get<string>('themeMode') || 'system'
    let scale = AppStorage.get<number>('fontScale') || 1
    let lang = AppStorage.get<string>('language') || 'zh'
    if (mode !== this.themeMode) this.themeMode = mode
    if (scale !== this.fontScale) this.fontScale = scale
    if (lang !== this.language) this.language = lang
    let style = AppStorage.get<string>('styleMode') || 'glass'
    if (style !== this.styleMode) this.styleMode = style
    this.themeTick++
    this.loadMemberProfile()
  }

  async loadGuidelines() {
    this.isLoading = true
    try {
      this.guidelines = await httpUtil.getGuidelines(this.activeGoal)
      this.statusMsg = ''
    } catch (e) {
      // 后端未启动：使用离线预载膳食指南（中国居民膳食指南 2022）
      this.guidelines = LocalData.guidelines(this.activeGoal)
      this.statusMsg = ''
    }
    this.isLoading = false
  }

  setGoal(goal: string) {
    this.activeGoal = goal
    this.loadGuidelines()
  }

  goBack() {
    this.getUIContext().getRouter().back()
  }

  getGoalLabel(goal: string): string {
    switch (goal) {
      case 'maintain': return this.i18n().goalMaintain
      case 'lose': return this.i18n().goalLose
      case 'gain': return this.i18n().goalGain
      default: return goal
    }
  }

  getMealLabel(meal: string): string {
    switch (meal) {
      case 'breakfast': return this.i18n().mealBreakfast + ' (30%)'
      case 'lunch': return this.i18n().mealLunch + ' (40%)'
      case 'dinner': return this.i18n().mealDinner + ' (30%)'
      default: return meal
    }
  }

  @Builder
  buildNutrientRow(label: string, value: number, unit: string, color: string, total: number, mode: string, scale: number, tick: number) {
    Column() {
      Row() {
        Text(label).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY).width(80)
        Text(value.toFixed(0) + ' ' + unit).fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600)
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
    .padding({ top: Theme.SPACE_SM, bottom: Theme.SPACE_SM })
    .opacity(this.fontScale > 0 ? 1 : 1)
  }

  build() {
    Column() {
      // 顶部导航 + 大标题
      Column() {
        Row() {
          Button() { Text('←').fontFamily('Inter').fontSize(18).fontColor(Theme.TEXT_SYS).fontWeight(600) }
            .type(ButtonType.Circle)
            .width(40).height(40)
            .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER })
            .border({ width: 1, color: Theme.BORDER })
            .onClick(() => this.goBack())
          Blank()
        }.width('100%')

        Text(this.i18n().guidelinesTitle)
          .fontFamily('Inter').fontSize(Theme.FONT_TITLE).fontWeight(700).fontColor(Theme.TEXT_SYS)
          .margin({ top: Theme.SPACE_SM })
      }
      .width('100%')
      .padding({ top: Theme.SPACE_MD, bottom: Theme.SPACE_XS, left: Theme.SPACE_MD, right: Theme.SPACE_MD })

      // 目标切换
      Row() {
        ForEach(['maintain', 'lose', 'gain'], (goal: string) => {
          Button() {
            Text(this.getGoalLabel(goal))
              .fontFamily('Inter').fontSize(Theme.FONT_BODY)
              .fontColor(this.activeGoal === goal ? Theme.ON_PRIMARY : Theme.TEXT_SYS_SECONDARY)
              .fontWeight(this.activeGoal === goal ? 600 : 400)
          }
          .type(ButtonType.Capsule)
          .height(36)
          .backgroundColor(this.activeGoal === goal ? Theme.PRIMARY : Theme.GLASS_BG)
          .border({ width: 1, color: this.activeGoal === goal ? Theme.PRIMARY : Theme.BORDER })
          .margin({ right: Theme.SPACE_SM })
          .onClick(() => this.setGoal(goal))
        })
      }
      .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM })

      if (this.isLoading) {
        Column() {
          LoadingProgress().width(32).height(32).color(Theme.PRIMARY)
          Text(this.i18n().loadingGuidelines).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_TERTIARY)
            .margin({ top: Theme.SPACE_SM })
        }.justifyContent(FlexAlign.Center).width('100%').layoutWeight(1)
      } else if (this.guidelines) {
        Scroll() {
          // 内容统一用左右 padding（避免卡片 width('100%')+margin 超出屏幕）
          Column() {
            // 当前成员身体状况 + 今日建议
            Column() {
              Row() {
                Text(this.i18n().currentMemberLabel + ': ' + this.memberName)
                  .fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT_SYS)
                Blank()
                if (this.hasProfile) {
                  Text(this.i18n().bmi + ' ' + this.statusBmi + ' · ' + this.statusLevel)
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.PRIMARY)
                }
              }
              .width('100%')

              if (this.hasProfile) {
                Text(this.i18n().eatWhat + ': ' + this.statusFoods)
                  .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_SECONDARY)
                  .width('100%').textAlign(TextAlign.Start).lineHeight(20)
                  .margin({ top: Theme.SPACE_SM })
                Text(this.i18n().eatHowMuch + ': ' + this.statusCal)
                  .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_SECONDARY)
                  .width('100%').textAlign(TextAlign.Start).lineHeight(20)
                  .margin({ top: Theme.SPACE_XS })
              } else {
                Text(this.i18n().noProfile)
                  .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
                  .width('100%').textAlign(TextAlign.Start).lineHeight(20)
                  .margin({ top: Theme.SPACE_SM })
              }
            }
            .width('100%').padding(Theme.SPACE_MD)
            .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER })
            .borderRadius(Theme.RADIUS_MD)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            .margin({ top: Theme.SPACE_MD })

            // 年龄段选择（动态计算每日推荐摄入）
            Row() {
              Text(this.i18n().ageGroup + ': ' + this.age + this.i18n().ageUnit)
                .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(600).fontColor(Theme.PRIMARY)
              Slider({ value: this.age, min: 2, max: 80, step: 1 })
                .blockColor(Theme.PRIMARY).trackColor(Theme.BORDER)
                .layoutWeight(1)
                .margin({ left: Theme.SPACE_MD })
                .onChange((value: number) => {
                  this.age = value
                })
            }
            .width('100%').padding({ top: Theme.SPACE_LG, left: Theme.SPACE_MD, right: Theme.SPACE_MD })

            // 每日总目标
            Text(this.i18n().dailyIntake)
              .fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT_SYS)
              .padding({ top: Theme.SPACE_MD })

            Column() {
              // 热量（内联：与年龄绑定，重绘时按最新年龄重算）
              Column() {
                Row() {
                  Text(this.i18n().calories).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY).width(80)
                  Text(this.calcDaily(this.age, this.activeGoal).calories.toFixed(0) + ' kcal').fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600)
                    .fontColor(Theme.WARNING).layoutWeight(1)
                }.width('100%')
                Row() {
                  Row().width('100%').height(6).backgroundColor(Theme.WARNING).borderRadius(Theme.RADIUS_FULL)
                }
                .width('100%').height(6).backgroundColor(Theme.BORDER).borderRadius(Theme.RADIUS_FULL)
                .margin({ top: Theme.SPACE_XS })
              }
              .width('100%').padding({ top: Theme.SPACE_SM, bottom: Theme.SPACE_SM })

              // 蛋白质
              Column() {
                Row() {
                  Text(this.i18n().protein).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY).width(80)
                  Text(this.calcDaily(this.age, this.activeGoal).protein_g.toFixed(0) + ' g').fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600)
                    .fontColor(Theme.PRIMARY).layoutWeight(1)
                }.width('100%')
                Row() {
                  Row().width(this.macroRatio().protein_pct + '%').height(6).backgroundColor(Theme.PRIMARY).borderRadius(Theme.RADIUS_FULL)
                }
                .width('100%').height(6).backgroundColor(Theme.BORDER).borderRadius(Theme.RADIUS_FULL)
                .margin({ top: Theme.SPACE_XS })
              }
              .width('100%').padding({ top: Theme.SPACE_SM, bottom: Theme.SPACE_SM })

              // 脂肪
              Column() {
                Row() {
                  Text(this.i18n().fat).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY).width(80)
                  Text(this.calcDaily(this.age, this.activeGoal).fat_g.toFixed(0) + ' g').fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600)
                    .fontColor(Theme.PRIMARY_DARK).layoutWeight(1)
                }.width('100%')
                Row() {
                  Row().width(this.macroRatio().fat_pct + '%').height(6).backgroundColor(Theme.PRIMARY_DARK).borderRadius(Theme.RADIUS_FULL)
                }
                .width('100%').height(6).backgroundColor(Theme.BORDER).borderRadius(Theme.RADIUS_FULL)
                .margin({ top: Theme.SPACE_XS })
              }
              .width('100%').padding({ top: Theme.SPACE_SM, bottom: Theme.SPACE_SM })

              // 碳水
              Column() {
                Row() {
                  Text(this.i18n().carbs).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY).width(80)
                  Text(this.calcDaily(this.age, this.activeGoal).carbs_g.toFixed(0) + ' g').fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600)
                    .fontColor(Theme.SUCCESS).layoutWeight(1)
                }.width('100%')
                Row() {
                  Row().width(this.macroRatio().carbs_pct + '%').height(6).backgroundColor(Theme.SUCCESS).borderRadius(Theme.RADIUS_FULL)
                }
                .width('100%').height(6).backgroundColor(Theme.BORDER).borderRadius(Theme.RADIUS_FULL)
                .margin({ top: Theme.SPACE_XS })
              }
              .width('100%').padding({ top: Theme.SPACE_SM, bottom: Theme.SPACE_SM })

              // 膳食纤维
              Column() {
                Row() {
                  Text(this.i18n().fiber).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY).width(80)
                  Text(this.calcDaily(this.age, this.activeGoal).fiber_g.toFixed(0) + ' g').fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600)
                    .fontColor(Theme.TEXT_TERTIARY).layoutWeight(1)
                }.width('100%')
                Row() {
                  Row().width('14%').height(6).backgroundColor(Theme.TEXT_TERTIARY).borderRadius(Theme.RADIUS_FULL)
                }
                .width('100%').height(6).backgroundColor(Theme.BORDER).borderRadius(Theme.RADIUS_FULL)
                .margin({ top: Theme.SPACE_XS })
              }
              .width('100%').padding({ top: Theme.SPACE_SM, bottom: Theme.SPACE_SM })
            }
            .padding(Theme.SPACE_MD).backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER })
            .borderRadius(Theme.RADIUS_MD)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            .margin({ top: Theme.SPACE_SM })

            // 宏量营养素比例
            Text(this.i18n().macroRatio)
              .fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT_SYS)
              .padding({ top: Theme.SPACE_LG })

            Row() {
              Column() {
                Text(this.i18n().protein).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
                Text(this.macroRatio().protein_pct.toFixed(0) + '%')
                  .fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(700).fontColor(Theme.PRIMARY)
              }
              .alignItems(HorizontalAlign.Center).layoutWeight(1)

              Column() {
                Text(this.i18n().fat).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
                Text(this.macroRatio().fat_pct.toFixed(0) + '%')
                  .fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(700).fontColor(Theme.WARNING)
              }
              .alignItems(HorizontalAlign.Center).layoutWeight(1)

              Column() {
                Text(this.i18n().carbs).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
                Text(this.macroRatio().carbs_pct.toFixed(0) + '%')
                  .fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(700).fontColor(Theme.SUCCESS)
              }
              .alignItems(HorizontalAlign.Center).layoutWeight(1)
            }
            .padding(Theme.SPACE_MD).backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER })
            .borderRadius(Theme.RADIUS_MD)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            .margin({ top: Theme.SPACE_SM })

            // 每餐分配
            Text(this.i18n().mealDistribution)
              .fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT_SYS)
              .padding({ top: Theme.SPACE_LG })

            Column() {
              // 早餐（30%）
              Row() {
                Column() {
                  Text(this.i18n().mealBreakfast + ' (30%)')
                    .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(600).fontColor(Theme.TEXT_SYS)
                  Text(this.mealTarget('breakfast').calories.toFixed(0) + ' kcal · P:' +
                    this.mealTarget('breakfast').protein_g.toFixed(0) +
                    'g F:' + this.mealTarget('breakfast').fat_g.toFixed(0) +
                    'g C:' + this.mealTarget('breakfast').carbs_g.toFixed(0) + 'g')
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
                    .margin({ top: Theme.SPACE_XS })
                }
                .alignItems(HorizontalAlign.Start).layoutWeight(1)
              }
              .width('100%').padding({ top: Theme.SPACE_SM, bottom: Theme.SPACE_SM })
              Divider().color(Theme.BORDER)

              // 午餐（40%）
              Row() {
                Column() {
                  Text(this.i18n().mealLunch + ' (40%)')
                    .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(600).fontColor(Theme.TEXT_SYS)
                  Text(this.mealTarget('lunch').calories.toFixed(0) + ' kcal · P:' +
                    this.mealTarget('lunch').protein_g.toFixed(0) +
                    'g F:' + this.mealTarget('lunch').fat_g.toFixed(0) +
                    'g C:' + this.mealTarget('lunch').carbs_g.toFixed(0) + 'g')
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
                    .margin({ top: Theme.SPACE_XS })
                }
                .alignItems(HorizontalAlign.Start).layoutWeight(1)
              }
              .width('100%').padding({ top: Theme.SPACE_SM, bottom: Theme.SPACE_SM })
              Divider().color(Theme.BORDER)

              // 晚餐（30%）
              Row() {
                Column() {
                  Text(this.i18n().mealDinner + ' (30%)')
                    .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(600).fontColor(Theme.TEXT_SYS)
                  Text(this.mealTarget('dinner').calories.toFixed(0) + ' kcal · P:' +
                    this.mealTarget('dinner').protein_g.toFixed(0) +
                    'g F:' + this.mealTarget('dinner').fat_g.toFixed(0) +
                    'g C:' + this.mealTarget('dinner').carbs_g.toFixed(0) + 'g')
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
                    .margin({ top: Theme.SPACE_XS })
                }
                .alignItems(HorizontalAlign.Start).layoutWeight(1)
              }
              .width('100%').padding({ top: Theme.SPACE_SM, bottom: Theme.SPACE_SM })
            }
            .padding(Theme.SPACE_MD).backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER })
            .borderRadius(Theme.RADIUS_MD)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            .margin({ top: Theme.SPACE_SM })

            // 膳食宝塔
            Text(this.i18n().pagodaTitle)
              .fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT_SYS)
              .padding({ top: Theme.SPACE_LG })

            Column() {
              ForEach(Object.keys(this.guidelines.pagoda), (cat: string) => {
                Row() {
                  Text(cat).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(600).fontColor(Theme.TEXT_SYS).width(80)
                  Text((this.guidelines!.pagoda[cat] as PagodaItem).min + '~' +
                    (this.guidelines!.pagoda[cat] as PagodaItem).max + ' ' +
                    (this.guidelines!.pagoda[cat] as PagodaItem).unit)
                    .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY).layoutWeight(1)
                }
                .padding({ top: Theme.SPACE_SM, bottom: Theme.SPACE_SM })
              })
            }
            .padding(Theme.SPACE_MD).backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER })
            .borderRadius(Theme.RADIUS_MD)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            .margin({ top: Theme.SPACE_SM })

            // 数据来源
            Text(this.i18n().dataSource + ': ' + this.guidelines.source)
              .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
              .width('100%')
              .padding({ top: Theme.SPACE_SM, bottom: Theme.SPACE_LG })
          }
          .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD })
        }
        .width('100%').layoutWeight(1)
      } else {
        Column() {
          Text(this.statusMsg).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_TERTIARY)
            .width('100%').textAlign(TextAlign.Center)
        }
        .width('100%').layoutWeight(1).justifyContent(FlexAlign.Center)
      }
    }
    .width('100%').height('100%').linearGradient(Theme.bgGradient(this.themeMode, this.styleMode))
    .opacity(this.themeTick >= 0 && this.fontScale > 0 ? 1 : 1)
  }
}
