// ============================================
// 身体数据分析：输入身高/体重/年龄/性别 → BMI + 体脂率估算 + 分级建议
// 体脂率估算公式（BMI 法）：男 1.2×BMI+0.23×年龄-5.4；女 1.2×BMI+0.23×年龄-16.2
// ============================================
import { I18nDict, AppStorage as DataStore } from '../utils/DataModels';
import { Theme } from '../utils/Theme';
import { zh } from '../utils/i18n/zh';
import { en } from '../utils/i18n/en';
import preferences from '@ohos.data.preferences';
import common from '@ohos.app.ability.common';

@Entry
@Component
struct BodyPage {
  @StorageLink('themeMode') themeMode: string = 'system'
  @StorageLink('styleMode') styleMode: string = 'glass'
  @StorageLink('fontScale') fontScale: number = 1
  @StorageLink('language') language: string = 'zh'
  @State themeTick: number = 0
  @State heightInput: string = ''
  @State weightInput: string = ''
  @State ageInput: string = ''
  @State gender: string = 'male'
  @State analyzed: boolean = false
  @State bmi: number = 0
  @State bodyFat: number = 0
  @State level: string = ''
  @State suggestion: string = ''
  @State memberName: string = 'default'
  @State calTarget: string = ''
  @State meals: string = ''
  @State foods: string = ''
  @State ex: string = ''
  @State goal: string = 'maintain'

  aboutToAppear(): void {
    this.memberName = DataStore.currentMember
  }

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
    let style = AppStorage.get<string>('styleMode') || 'glass'
    if (style !== this.styleMode) this.styleMode = style
    this.themeTick++
  }

  goBack(): void {
    this.getUIContext().getRouter().back()
  }

  analyze(): void {
    let h = Number(this.heightInput) / 100
    let w = Number(this.weightInput)
    if (h <= 0 || w <= 0) {
      return
    }
    let bmiVal = w / (h * h)
    this.bmi = Math.round(bmiVal * 10) / 10
    // BMI 分级（中国标准）
    let lv = ''
    if (bmiVal < 18.5) {
      lv = this.i18n().underweight
    } else if (bmiVal < 24) {
      lv = this.i18n().normal
    } else if (bmiVal < 28) {
      lv = this.i18n().overweight
    } else {
      lv = this.i18n().obese
    }
    this.level = lv
    // 体脂率估算
    let age = Number(this.ageInput) > 0 ? Number(this.ageInput) : 25
    let bf = this.gender === 'male' ? 1.2 * bmiVal + 0.23 * age - 5.4 : 1.2 * bmiVal + 0.23 * age - 16.2
    this.bodyFat = Math.round(Math.max(3, Math.min(60, bf)) * 10) / 10
    // 建议 + 定制膳食方案（按分级，联动成员健康目标）
    if (bmiVal < 18.5) {
      this.suggestion = this.i18n().sugUnder
      this.calTarget = this.i18n().calUnder
      this.meals = this.i18n().mealsUnder
      this.foods = this.i18n().foodsUnder
      this.ex = this.i18n().exUnder
      this.goal = 'gain'
    } else if (bmiVal < 24) {
      this.suggestion = this.i18n().sugNormal
      this.calTarget = this.i18n().calNormal
      this.meals = this.i18n().mealsNormal
      this.foods = this.i18n().foodsNormal
      this.ex = this.i18n().exNormal
      this.goal = 'maintain'
    } else if (bmiVal < 28) {
      this.suggestion = this.i18n().sugOver
      this.calTarget = this.i18n().calOver
      this.meals = this.i18n().mealsOver
      this.foods = this.i18n().foodsOver
      this.ex = this.i18n().exOver
      this.goal = 'lose'
    } else {
      this.suggestion = this.i18n().sugObese
      this.calTarget = this.i18n().calObese
      this.meals = this.i18n().mealsObese
      this.foods = this.i18n().foodsObese
      this.ex = this.i18n().exObese
      this.goal = 'lose'
    }
    this.analyzed = true
  }

  // 应用健康目标：保存完整身体档案到当前成员，膳食指南/菜谱按此定制
  async applyGoal(): Promise<void> {
    try {
      let ctx = this.getUIContext().getHostContext() as common.UIAbilityContext
      let pref = await preferences.getPreferences(ctx, 'smartkitchen_settings')
      let member = DataStore.currentMember
      await pref.put('body_goal_' + member, this.goal)
      await pref.put('body_bmi_' + member, this.bmi)
      await pref.put('body_bodyfat_' + member, this.bodyFat)
      await pref.put('body_level_' + member, this.level)
      await pref.put('body_cal_' + member, this.calTarget)
      await pref.put('body_meals_' + member, this.meals)
      await pref.put('body_foods_' + member, this.foods)
      await pref.flush()
    } catch (e) {
      // 忽略
    }
  }

  build() {
    Column() {
      // 顶栏
      Row() {
        Text(this.i18n().bodyTitle)
          .fontFamily('Inter').fontSize(Theme.FONT_TITLE).fontWeight(700).fontColor(Theme.TEXT_SYS)
      }
      .width('100%')
      .padding({ top: 16, bottom: 8, left: Theme.SPACE_LG, right: Theme.SPACE_LG })

      Divider().strokeWidth(0.5).color(Theme.BORDER)

      Scroll() {
        Column() {
          // 输入卡片
          Column() {
            // 身高
            Row() {
              Text(this.i18n().height).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS).width(72)
              TextInput({ text: this.heightInput })
                .width(120).height(38)
                .backgroundColor(Theme.GLASS_BG).borderRadius(Theme.RADIUS_SM)
                .textAlign(TextAlign.Center).fontFamily('Inter').fontSize(Theme.FONT_BODY)
                .onChange((v: string) => { this.heightInput = v })
              Text(this.i18n().cm).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY)
                .margin({ left: Theme.SPACE_SM })
            }
            .width('100%').margin({ top: Theme.SPACE_MD })

            // 体重
            Row() {
              Text(this.i18n().bodyWeight).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS).width(72)
              TextInput({ text: this.weightInput })
                .width(120).height(38)
                .backgroundColor(Theme.GLASS_BG).borderRadius(Theme.RADIUS_SM)
                .textAlign(TextAlign.Center).fontFamily('Inter').fontSize(Theme.FONT_BODY)
                .onChange((v: string) => { this.weightInput = v })
              Text(this.i18n().kg).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY)
                .margin({ left: Theme.SPACE_SM })
            }
            .width('100%').margin({ top: Theme.SPACE_MD })

            // 年龄
            Row() {
              Text(this.i18n().age).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS).width(72)
              TextInput({ text: this.ageInput })
                .width(120).height(38)
                .backgroundColor(Theme.GLASS_BG).borderRadius(Theme.RADIUS_SM)
                .textAlign(TextAlign.Center).fontFamily('Inter').fontSize(Theme.FONT_BODY)
                .onChange((v: string) => { this.ageInput = v })
            }
            .width('100%').margin({ top: Theme.SPACE_MD })

            // 性别
            Row() {
              Text(this.i18n().gender).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS).width(72)
              Text(this.i18n().male).fontFamily('Inter').fontSize(Theme.FONT_BODY)
                .fontColor(this.gender === 'male' ? Theme.ON_PRIMARY : Theme.TEXT_SYS_SECONDARY)
                .padding({ left: 16, right: 16, top: 6, bottom: 6 })
                .backgroundColor(this.gender === 'male' ? Theme.PRIMARY : Theme.GLASS_BG)
                .borderRadius(Theme.RADIUS_FULL)
                .onClick(() => { this.gender = 'male' })
              Text(this.i18n().female).fontFamily('Inter').fontSize(Theme.FONT_BODY)
                .fontColor(this.gender === 'female' ? Theme.ON_PRIMARY : Theme.TEXT_SYS_SECONDARY)
                .padding({ left: 16, right: 16, top: 6, bottom: 6 })
                .backgroundColor(this.gender === 'female' ? Theme.PRIMARY : Theme.GLASS_BG)
                .borderRadius(Theme.RADIUS_FULL)
                .margin({ left: Theme.SPACE_SM })
                .onClick(() => { this.gender = 'female' })
            }
            .width('100%').margin({ top: Theme.SPACE_MD, bottom: Theme.SPACE_MD })
          }
          .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD })
          .backgroundBlurStyle(BlurStyle.Thin, { colorMode: Theme.isDark() ? ThemeColorMode.DARK : ThemeColorMode.LIGHT }).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_LG)
          .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })

          // 分析按钮
          Button() {
            Text(this.i18n().analyze).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.ON_PRIMARY).fontWeight(600)
          }
          .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY).linearGradient({ angle: 135, colors: [['#E8967A', 0.0], ['#D97757', 1.0]] }).width(200).height(44)
          .margin({ top: Theme.SPACE_LG })
          .onClick(() => { this.analyze() })

          // 当前成员
          Text(this.i18n().currentMemberLabel + ': ' + this.memberName)
            .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_SECONDARY)
            .width('100%').textAlign(TextAlign.Center)
            .margin({ top: Theme.SPACE_LG })

          // 结果卡
          if (this.analyzed) {
            Column() {
              // BMI 大数字
              Row() {
                Column() {
                  Text(this.bmi + '').fontFamily('Inter').fontSize(44).fontWeight(700).fontColor(Theme.PRIMARY)
                  Text(this.i18n().bmi).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                    .margin({ top: 2 })
                }
                .alignItems(HorizontalAlign.Center).layoutWeight(1)

                Column() {
                  Text(this.bodyFat + '%').fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(700).fontColor(Theme.SUCCESS)
                  Text(this.i18n().bodyFatRate).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                    .margin({ top: 2 })
                }
                .alignItems(HorizontalAlign.Center).layoutWeight(1)

                Column() {
                  Text(this.level).fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(700).fontColor(Theme.WARNING)
                  Text(this.i18n().level).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                    .margin({ top: 2 })
                }
                .alignItems(HorizontalAlign.Center).layoutWeight(1)
              }
              .width('100%').padding(Theme.SPACE_MD)

              Divider().color(Theme.BORDER)

              // 建议
              Text(this.i18n().suggestion).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS)
                .width('100%').lineHeight(22).textAlign(TextAlign.Start)
                .padding(Theme.SPACE_MD)

              Divider().color(Theme.BORDER)

              // 定制膳食方案
              Text(this.i18n().dietPlan).fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT_SYS)
                .width('100%').textAlign(TextAlign.Start)
                .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_MD })

              Text(this.i18n().calorieTarget + ': ' + this.calTarget)
                .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_SECONDARY)
                .width('100%').textAlign(TextAlign.Start).lineHeight(20)
                .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM })

              Text(this.i18n().mealsPlan + ': ' + this.meals)
                .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_SECONDARY)
                .width('100%').textAlign(TextAlign.Start).lineHeight(20)
                .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM })

              Text(this.i18n().foodRec + ': ' + this.foods)
                .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_SECONDARY)
                .width('100%').textAlign(TextAlign.Start).lineHeight(20)
                .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM })

              Text(this.i18n().exerciseRec + ': ' + this.ex)
                .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_SECONDARY)
                .width('100%').textAlign(TextAlign.Start).lineHeight(20)
                .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM })

              // 应用健康目标
              Button() {
                Text(this.i18n().applyGoal).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.ON_PRIMARY).fontWeight(600)
              }
              .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY).linearGradient({ angle: 135, colors: [['#E8967A', 0.0], ['#D97757', 1.0]] }).width(200).height(40)
              .margin({ top: Theme.SPACE_MD, bottom: Theme.SPACE_MD })
              .onClick(() => { this.applyGoal() })
            }
            .width('100%').margin({ top: Theme.SPACE_SM })
            .backgroundBlurStyle(BlurStyle.Thin, { colorMode: Theme.isDark() ? ThemeColorMode.DARK : ThemeColorMode.LIGHT }).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_LG)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
          }
        }
        .width('100%')
        .padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG, top: Theme.SPACE_MD, bottom: 24 })
      }
      .width('100%').layoutWeight(1).scrollBar(BarState.Off)
    }
    .width('100%').height('100%').linearGradient(Theme.bgGradient(this.themeMode, this.styleMode))
    .opacity(this.themeTick >= 0 && this.fontScale > 0 ? 1 : 1)
  }
}
