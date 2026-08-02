import { httpUtil } from '../utils/HttpUtil'
import { RecipeItem, RecipeIngredient, I18nDict, AppStorage as DataStore } from '../utils/DataModels'
import { Want } from '@kit.AbilityKit'
import preferences from '@ohos.data.preferences'
import common from '@ohos.app.ability.common'
import { zh } from '../utils/i18n/zh'
import { en } from '../utils/i18n/en'
import { Theme } from '../utils/Theme'
import { LocalData } from '../utils/LocalData'

@Entry
@Component
struct RecipesPage {
  @StorageLink('themeMode') themeMode: string = 'system'
  @StorageLink('styleMode') styleMode: string = 'glass'
  @StorageLink('fontScale') fontScale: number = 1
  @StorageLink('language') language: string = 'zh'
  // 页面每次显示时自增，强制整页重绘
  @State themeTick: number = 0
  @State recipes: RecipeItem[] = []
  @State activeMeal: string = ''
  @State activeGoal: string = 'maintain'
  @State isLoading: boolean = true
  @State statusMsg: string = '加载中...'
  @State isRecommend: boolean = true
  @State selectedRecipe: RecipeItem | null = null

  aboutToAppear() {
    this.loadMemberGoal()
    this.loadRecipes()
  }

  // 读取成员健康目标（身体数据分析里应用的目标，用于定制菜谱推荐）
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
  }

  async loadRecipes() {
    this.isLoading = true
    try {
      let resp = this.isRecommend
        ? await httpUtil.recommendRecipes(this.activeGoal, this.activeMeal || undefined)
        : await httpUtil.getRecipes(this.activeMeal || undefined)
      this.recipes = resp.recipes
      this.statusMsg = resp.recipes.length > 0 ? '' : this.i18n().noRecipes
    } catch (e) {
      // 后端未启动：使用离线预载菜谱
      this.recipes = this.isRecommend
        ? LocalData.recommendRecipes(this.activeGoal, this.activeMeal)
        : LocalData.recipes(this.activeMeal)
      this.statusMsg = this.recipes.length > 0 ? '' : this.i18n().noRecipes
    }
    this.isLoading = false
  }

  // 食材清单文本
  ingredientList(r: RecipeItem): string {
    let names: string[] = []
    r.ingredients.forEach((ing: RecipeIngredient) => {
      names.push(LocalData.foodName(ing.food) + ' ' + ing.grams + 'g')
    })
    return names.join('、')
  }

  // 打开 B 站视频教程（跳转系统浏览器）
  openBilibili(url: string): void {
    let ctx = this.getUIContext().getHostContext() as common.UIAbilityContext
    let want: Want = {
      action: 'ohos.want.action.viewData',
      uri: url
    }
    ctx.startAbility(want).catch(() => {})
  }

  setMealFilter(meal: string) {
    this.activeMeal = this.activeMeal === meal ? '' : meal
    this.loadRecipes()
  }

  setGoal(goal: string) {
    this.activeGoal = goal
    this.loadRecipes()
  }

  toggleMode() {
    this.isRecommend = !this.isRecommend
    this.loadRecipes()
  }

  goBack() {
    this.getUIContext().getRouter().back()
  }

  getMealLabel(mealType: string): string {
    switch (mealType) {
      case 'breakfast': return this.i18n().mealBreakfast
      case 'lunch': return this.i18n().mealLunch
      case 'dinner': return this.i18n().mealDinner
      default: return mealType
    }
  }

  getMealColor(mealType: string): string {
    switch (mealType) {
      case 'breakfast': return Theme.WARNING
      case 'lunch': return Theme.PRIMARY
      case 'dinner': return Theme.SUCCESS
      default: return Theme.TEXT_TERTIARY
    }
  }

  getDifficultyLabel(difficulty: string): string {
    switch (difficulty) {
      case 'easy': return this.i18n().diffEasy
      case 'medium': return this.i18n().diffMedium
      case 'hard': return this.i18n().diffHard
      default: return difficulty
    }
  }

  private mealKeys: string[] = ['', 'breakfast', 'lunch', 'dinner']

  build() {
    Column() {
      // 顶部导航 + 大标题
      Column() {
        Text(this.i18n().recipeTitle)
          .fontFamily('Inter').fontSize(Theme.FONT_TITLE).fontWeight(700).fontColor(Theme.TEXT_SYS)
          .margin({ top: Theme.SPACE_SM })
      }
      .width('100%')
      .padding({ top: Theme.SPACE_MD, bottom: Theme.SPACE_XS, left: Theme.SPACE_MD, right: Theme.SPACE_MD })

      // 模式切换
      Row() {
        Button() {
          Text(this.isRecommend ? this.i18n().smartRecommend : this.i18n().allRecipes)
            .fontFamily('Inter').fontSize(Theme.FONT_BODY)
            .fontColor(this.isRecommend ? Theme.ON_PRIMARY : Theme.TEXT_SYS_SECONDARY)
            .fontWeight(600)
        }
        .type(ButtonType.Capsule)
        .height(36)
        .backgroundColor(this.isRecommend ? Theme.PRIMARY : Theme.GLASS_BG)
        .border({ width: 1, color: this.isRecommend ? Theme.PRIMARY : Theme.BORDER })
        .onClick(() => this.toggleMode())

        if (this.isRecommend) {
          Button() {
            Text(this.activeGoal === 'maintain' ? this.i18n().goalMaintain :
              this.activeGoal === 'lose' ? this.i18n().goalLose : this.i18n().goalGain)
              .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.PRIMARY).fontWeight(600)
          }
          .type(ButtonType.Capsule)
          .backgroundColor(Theme.PRIMARY_LIGHT)
          .height(36)
          .margin({ left: Theme.SPACE_SM })
          .onClick(() => {
            let goals: string[] = ['maintain', 'lose', 'gain']
            let idx: number = goals.indexOf(this.activeGoal)
            this.setGoal(goals[(idx + 1) % 3])
          })
        }
      }
            .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM })
      .justifyContent(FlexAlign.Start)

      // 餐类筛选
      Row() {
        ForEach([this.i18n().all, this.i18n().mealBreakfast, this.i18n().mealLunch, this.i18n().mealDinner], (label: string, idx: number) => {
          Button() {
            Text(label)
              .fontFamily('Inter').fontSize(Theme.FONT_BODY)
              .fontColor(this.mealKeys[idx] === this.activeMeal ? Theme.ON_PRIMARY : Theme.TEXT_SYS_SECONDARY)
              .fontWeight(this.mealKeys[idx] === this.activeMeal ? 600 : 400)
          }
          .type(ButtonType.Capsule)
          .height(34)
          .backgroundColor(this.mealKeys[idx] === this.activeMeal ? Theme.PRIMARY : Theme.GLASS_BG)
          .border({ width: 1, color: this.mealKeys[idx] === this.activeMeal ? Theme.PRIMARY : Theme.BORDER })
          .margin({ right: Theme.SPACE_SM })
          .onClick(() => this.setMealFilter(this.mealKeys[idx]))
        })
      }
      .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM })

      // 内容区
      if (this.isLoading) {
        Column() {
          LoadingProgress().width(32).height(32).color(Theme.PRIMARY)
          Text(this.i18n().loadingRecipes).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_TERTIARY)
            .margin({ top: Theme.SPACE_SM })
        }.justifyContent(FlexAlign.Center).width('100%').height(300)
      } else if (this.recipes.length > 0) {
        List() {
          ForEach(this.recipes, (item: RecipeItem) => {
            ListItem() {
              Column() {
                // 标题行
                Row() {
                  Text(item.name)
                    .fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT_SYS)
                    .layoutWeight(1)
                  Text(this.getMealLabel(item.meal_type))
                    .fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.ON_PRIMARY)
                    .padding({ left: Theme.SPACE_SM, right: Theme.SPACE_SM, top: Theme.SPACE_XS, bottom: Theme.SPACE_XS })
                    .backgroundColor(this.getMealColor(item.meal_type))
                    .borderRadius(Theme.RADIUS_SM)
                }.width('100%')

                // 英文名 + 标签
                Row() {
                  Text(item.name_en).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
                  Text(' · ' + item.cook_time + 'min').fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
                  Text(' · ' + this.getDifficultyLabel(item.difficulty))
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
                }.margin({ top: Theme.SPACE_XS })

                // 营养条
                Row() {
                  Text(item.nutrition.calories.toFixed(0) + 'kcal')
                    .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(600).fontColor(Theme.WARNING)
                  Text('P:' + item.nutrition.protein.toFixed(0) + 'g')
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_SECONDARY).margin({ left: Theme.SPACE_MD })
                  Text('F:' + item.nutrition.fat.toFixed(0) + 'g')
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_SECONDARY).margin({ left: Theme.SPACE_SM })
                  Text('C:' + item.nutrition.carbs.toFixed(0) + 'g')
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_SECONDARY).margin({ left: Theme.SPACE_SM })
                }.margin({ top: Theme.SPACE_SM })

                // 食材标签（显示中文名）
                Row() {
                  ForEach(item.ingredients, (ing: RecipeIngredient) => {
                    Text(LocalData.foodName(ing.food))
                      .fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_SECONDARY)
                      .padding({ left: Theme.SPACE_SM, right: Theme.SPACE_SM, top: Theme.SPACE_XS, bottom: Theme.SPACE_XS })
                      .backgroundColor(Theme.BORDER).borderRadius(Theme.RADIUS_SM)
                      .margin({ right: Theme.SPACE_XS })
                  })
                }.margin({ top: Theme.SPACE_SM })

                // 推荐分数
                if (item.score !== undefined) {
                  Text(this.i18n().matchScore + ' ' + item.score.toFixed(0) + '%')
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.SUCCESS)
                    .margin({ top: Theme.SPACE_XS })
                }
              }
                            .padding(Theme.SPACE_MD)
              .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER })
              .borderRadius(Theme.RADIUS_MD)
              .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
              .opacity(this.fontScale > 0 ? 1 : 1)
              .onClick(() => {
                // 点击展开/收起菜谱详情
                this.selectedRecipe = this.selectedRecipe && this.selectedRecipe.key === item.key ? null : item
              })
            }
            .margin({ top: Theme.SPACE_SM, left: Theme.SPACE_MD, right: Theme.SPACE_MD })
          })
        }
        .width('100%').layoutWeight(1).margin({ top: Theme.SPACE_SM })

        // 菜谱详情（点击卡片展开）
        if (this.selectedRecipe) {
          Column() {
            Row() {
              Text(this.selectedRecipe.name)
                .fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT_SYS)
                .layoutWeight(1).maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
              Text(this.getMealLabel(this.selectedRecipe.meal_type))
                .fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.ON_PRIMARY)
                .padding({ left: 8, right: 8, top: 3, bottom: 3 })
                .backgroundColor(this.getMealColor(this.selectedRecipe.meal_type))
                .borderRadius(Theme.RADIUS_SM)
            }.width('100%')

            Text(this.selectedRecipe.name_en + ' · ' + this.selectedRecipe.cook_time + 'min · ' +
              this.getDifficultyLabel(this.selectedRecipe.difficulty))
              .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
              .width('100%').textAlign(TextAlign.Start)
              .margin({ top: Theme.SPACE_XS })

            Divider().color(Theme.BORDER).margin({ top: Theme.SPACE_MD, bottom: Theme.SPACE_MD })

            // 食材清单
            Text(this.i18n().ingredients).fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT_SYS)
              .width('100%').textAlign(TextAlign.Start)
            Text(this.ingredientList(this.selectedRecipe))
              .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY)
              .width('100%').textAlign(TextAlign.Start).lineHeight(22)
              .margin({ top: Theme.SPACE_SM })

            // 营养
            Text(this.i18n().nutritionDetail + ': ' +
              this.selectedRecipe.nutrition.calories + ' kcal · P ' +
              this.selectedRecipe.nutrition.protein + 'g · F ' +
              this.selectedRecipe.nutrition.fat + 'g · C ' +
              this.selectedRecipe.nutrition.carbs + 'g')
              .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.PRIMARY)
              .width('100%').textAlign(TextAlign.Start)
              .margin({ top: Theme.SPACE_MD })

            // 做法步骤
            Text(this.i18n().steps).fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT_SYS)
              .width('100%').textAlign(TextAlign.Start)
              .margin({ top: Theme.SPACE_MD })
            if (this.selectedRecipe.steps) {
              ForEach(this.selectedRecipe.steps, (s: string, i: number) => {
                Text((i + 1) + '. ' + s)
                  .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS)
                  .width('100%').textAlign(TextAlign.Start).lineHeight(22)
                  .margin({ top: Theme.SPACE_XS })
              })
            }

            // B 站视频教程（跳转）
            if (this.selectedRecipe.bvideo) {
              Button() {
                Row() {
                  Text('B站')
                    .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.ON_PRIMARY).fontWeight(600)
                    .padding({ left: 10, right: 10, top: 3, bottom: 3 })
                    .backgroundColor('#FB7299').borderRadius(Theme.RADIUS_SM)
                  Text(this.i18n().watchTutorial)
                    .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.ON_PRIMARY).fontWeight(500)
                    .margin({ left: 8 })
                }
              }
              .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY).linearGradient({ angle: 135, colors: [['#E8967A', 0.0], ['#D97757', 1.0]] }).height(40)
              .margin({ top: Theme.SPACE_LG })
              .onClick(() => {
                this.openBilibili(this.selectedRecipe!.bvideo!)
              })
            }
          }
          .width('100%').padding(Theme.SPACE_MD)
          .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_LG)
          .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
          .margin({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM })
        }
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
