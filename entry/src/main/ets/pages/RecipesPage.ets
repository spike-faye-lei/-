import router from '@ohos.router'
import { httpUtil } from '../utils/HttpUtil'
import { RecipeItem, RecipeIngredient } from '../utils/DataModels'
import { Theme } from '../utils/Theme'

@Entry
@Component
struct RecipesPage {
  @State recipes: RecipeItem[] = []
  @State activeMeal: string = ''
  @State activeGoal: string = 'maintain'
  @State isLoading: boolean = true
  @State statusMsg: string = '加载中...'
  @State isRecommend: boolean = true

  aboutToAppear() {
    this.loadRecipes()
  }

  async loadRecipes() {
    this.isLoading = true
    try {
      let resp = this.isRecommend
        ? await httpUtil.recommendRecipes(this.activeGoal, this.activeMeal || undefined)
        : await httpUtil.getRecipes(this.activeMeal || undefined)
      this.recipes = resp.recipes
      this.statusMsg = resp.recipes.length > 0 ? '' : '暂无菜谱'
    } catch (e) {
      this.statusMsg = '加载失败: ' + JSON.stringify(e)
    }
    this.isLoading = false
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
    router.back()
  }

  getMealLabel(mealType: string): string {
    switch (mealType) {
      case 'breakfast': return '早餐'
      case 'lunch': return '午餐'
      case 'dinner': return '晚餐'
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
      case 'easy': return '简单'
      case 'medium': return '中等'
      case 'hard': return '困难'
      default: return difficulty
    }
  }

  private mealKeys: string[] = ['', 'breakfast', 'lunch', 'dinner']

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

        Text('菜谱推荐')
          .fontSize(Theme.FONT_TITLE).fontWeight(700).fontColor(Theme.TEXT)
          .margin({ top: Theme.SPACE_SM })
      }
      .width('100%')
      .padding({ top: Theme.SPACE_MD, bottom: Theme.SPACE_XS, left: Theme.SPACE_MD, right: Theme.SPACE_MD })

      // 模式切换
      Row() {
        Button() {
          Text(this.isRecommend ? '智能推荐' : '全部菜谱')
            .fontSize(Theme.FONT_BODY)
            .fontColor(this.isRecommend ? Theme.SURFACE : Theme.TEXT_SECONDARY)
            .fontWeight(600)
        }
        .type(ButtonType.Capsule)
        .height(36)
        .backgroundColor(this.isRecommend ? Theme.PRIMARY : Theme.SURFACE)
        .border({ width: 1, color: this.isRecommend ? Theme.PRIMARY : Theme.BORDER })
        .onClick(() => this.toggleMode())

        if (this.isRecommend) {
          Button() {
            Text(this.activeGoal === 'maintain' ? '保持' :
              this.activeGoal === 'lose' ? '减重' : '增重')
              .fontSize(Theme.FONT_BODY).fontColor(Theme.PRIMARY).fontWeight(600)
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
      .width('100%')
      .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM })
      .justifyContent(FlexAlign.Start)

      // 餐类筛选
      Row() {
        ForEach(['全部', '早餐', '午餐', '晚餐'], (label: string, idx: number) => {
          Button() {
            Text(label)
              .fontSize(Theme.FONT_BODY)
              .fontColor(this.mealKeys[idx] === this.activeMeal ? Theme.SURFACE : Theme.TEXT_SECONDARY)
              .fontWeight(this.mealKeys[idx] === this.activeMeal ? 600 : 400)
          }
          .type(ButtonType.Capsule)
          .height(34)
          .backgroundColor(this.mealKeys[idx] === this.activeMeal ? Theme.PRIMARY : Theme.SURFACE)
          .border({ width: 1, color: this.mealKeys[idx] === this.activeMeal ? Theme.PRIMARY : Theme.BORDER })
          .margin({ right: Theme.SPACE_SM })
          .onClick(() => this.setMealFilter(this.mealKeys[idx]))
        })
      }
      .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_SM })

      // 内容区
      if (this.isLoading) {
        Column() {
          LoadingProgress().width(32).height(32).color(Theme.PRIMARY)
          Text('加载菜谱...').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_TERTIARY)
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
                    .fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT)
                    .layoutWeight(1)
                  Text(this.getMealLabel(item.meal_type))
                    .fontSize(Theme.FONT_MICRO).fontColor(Theme.SURFACE)
                    .padding({ left: Theme.SPACE_SM, right: Theme.SPACE_SM, top: Theme.SPACE_XS, bottom: Theme.SPACE_XS })
                    .backgroundColor(this.getMealColor(item.meal_type))
                    .borderRadius(Theme.RADIUS_SM)
                }.width('100%')

                // 英文名 + 标签
                Row() {
                  Text(item.name_en).fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY)
                  Text(' · ' + item.cook_time + 'min').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY)
                  Text(' · ' + this.getDifficultyLabel(item.difficulty))
                    .fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY)
                }.margin({ top: Theme.SPACE_XS })

                // 营养条
                Row() {
                  Text(item.nutrition.calories.toFixed(0) + 'kcal')
                    .fontSize(Theme.FONT_BODY).fontWeight(600).fontColor(Theme.WARNING)
                  Text('P:' + item.nutrition.protein.toFixed(0) + 'g')
                    .fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SECONDARY).margin({ left: Theme.SPACE_MD })
                  Text('F:' + item.nutrition.fat.toFixed(0) + 'g')
                    .fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SECONDARY).margin({ left: Theme.SPACE_SM })
                  Text('C:' + item.nutrition.carbs.toFixed(0) + 'g')
                    .fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SECONDARY).margin({ left: Theme.SPACE_SM })
                }.margin({ top: Theme.SPACE_SM })

                // 食材标签
                Row() {
                  ForEach(item.ingredients, (ing: RecipeIngredient) => {
                    Text(ing.food)
                      .fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SECONDARY)
                      .padding({ left: Theme.SPACE_SM, right: Theme.SPACE_SM, top: Theme.SPACE_XS, bottom: Theme.SPACE_XS })
                      .backgroundColor(Theme.BORDER).borderRadius(Theme.RADIUS_SM)
                      .margin({ right: Theme.SPACE_XS })
                  })
                }.margin({ top: Theme.SPACE_SM })

                // 推荐分数
                if (item.score !== undefined) {
                  Text('匹配度 ' + item.score.toFixed(0) + '%')
                    .fontSize(Theme.FONT_CAPTION).fontColor(Theme.SUCCESS)
                    .margin({ top: Theme.SPACE_XS })
                }
              }
              .width('100%')
              .padding(Theme.SPACE_MD)
              .backgroundColor(Theme.SURFACE)
              .borderRadius(Theme.RADIUS_MD)
              .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            }
            .margin({ top: Theme.SPACE_SM, left: Theme.SPACE_MD, right: Theme.SPACE_MD })
          })
        }
        .width('100%').layoutWeight(1).margin({ top: Theme.SPACE_SM })
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
