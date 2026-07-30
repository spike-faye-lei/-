import router from '@ohos.router'
import { httpUtil } from '../utils/HttpUtil'
import { RecipeItem, RecipeIngredient } from '../utils/DataModels'

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
      case 'breakfast': return '#f0a040'
      case 'lunch': return '#2a5f8f'
      case 'dinner': return '#2d8a4e'
      default: return '#8a9aaa'
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
      // 顶部
      Row() {
        Button() { Text('← 返回').fontSize(15).fontColor('#2a5f8f') }
          .type(ButtonType.Capsule).backgroundColor('transparent')
          .onClick(() => this.goBack())

        Text('菜谱推荐').fontSize(20).fontWeight(700).fontColor('#1a1a2e')
          .layoutWeight(1).textAlign(TextAlign.Center)
      }
      .width('100%').padding({ top: 16, bottom: 8, left: 12, right: 12 })

      // 模式切换
      Row() {
        Button() {
          Text(this.isRecommend ? '🌟 智能推荐' : '📖 全部菜谱')
            .fontSize(14).fontColor('#fff').fontWeight(600)
        }
        .type(ButtonType.Capsule).backgroundColor(this.isRecommend ? '#2a5f8f' : '#5a6a7e')
        .height(36).onClick(() => this.toggleMode())

        if (this.isRecommend) {
          Button() {
            Text(this.activeGoal === 'maintain' ? '⚖ 保持' :
              this.activeGoal === 'lose' ? '🔥 减重' : '💪 增重')
              .fontSize(14).fontColor('#2a5f8f').fontWeight(600)
          }
          .type(ButtonType.Capsule).backgroundColor('#e8edf5').height(36)
          .margin({ left: 8 }).onClick(() => {
            let goals = ['maintain', 'lose', 'gain']
            let idx = goals.indexOf(this.activeGoal)
            this.setGoal(goals[(idx + 1) % 3])
          })
        }
      }
      .width('100%').padding({ left: 20, right: 20, top: 12 }).justifyContent(FlexAlign.Start)

      // 餐类筛选
      Row() {
        ForEach(['全部', '早餐', '午餐', '晚餐'], (label: string, idx: number) => {
          Button() { Text(label).fontSize(13).fontColor(this.mealKeys[idx] === this.activeMeal ? '#fff' : '#5a6a7e').fontWeight(this.mealKeys[idx] === this.activeMeal ? 600 : 400) }
            .type(ButtonType.Capsule)
            .backgroundColor(this.mealKeys[idx] === this.activeMeal ? '#2a5f8f' : '#f0f2f5')
            .height(34).margin({ right: 8 })
            .onClick(() => this.setMealFilter(this.mealKeys[idx]))
        })
      }
      .width('100%').padding({ left: 20, right: 20, top: 12 })

      // 内容区
      if (this.isLoading) {
        Column() {
          LoadingProgress().width(32).height(32)
          Text('加载菜谱...').fontSize(14).fontColor('#8a9aaa').margin({ top: 12 })
        }.justifyContent(FlexAlign.Center).width('100%').height(300)
      } else if (this.recipes.length > 0) {
        List() {
          ForEach(this.recipes, (item: RecipeItem) => {
            ListItem() {
              Column() {
                // 标题行
                Row() {
                  Text(item.name).fontSize(17).fontWeight(600).fontColor('#1a1a2e')
                    .layoutWeight(1)
                  Text(this.getMealLabel(item.meal_type))
                    .fontSize(11).fontColor('#fff')
                    .padding({ left: 8, right: 8, top: 2, bottom: 2 })
                    .backgroundColor(this.getMealColor(item.meal_type))
                    .borderRadius(8)
                }.width('100%')

                // 英文名 + 标签
                Row() {
                  Text(item.name_en).fontSize(12).fontColor('#8a9aaa')
                  Text(' · ' + item.cook_time + 'min').fontSize(12).fontColor('#8a9aaa')
                  Text(' · ' + this.getDifficultyLabel(item.difficulty))
                    .fontSize(12).fontColor('#8a9aaa')
                }.margin({ top: 4 })

                // 营养条
                Row() {
                  Text('🔥 ' + item.nutrition.calories.toFixed(0) + 'kcal')
                    .fontSize(14).fontWeight(600).fontColor('#c96f2e')
                  Text('P:' + item.nutrition.protein.toFixed(0) + 'g')
                    .fontSize(13).fontColor('#5a6a7e').margin({ left: 12 })
                  Text('F:' + item.nutrition.fat.toFixed(0) + 'g')
                    .fontSize(13).fontColor('#5a6a7e').margin({ left: 8 })
                  Text('C:' + item.nutrition.carbs.toFixed(0) + 'g')
                    .fontSize(13).fontColor('#5a6a7e').margin({ left: 8 })
                }.margin({ top: 8 })

                // 食材标签
                Row() {
                  ForEach(item.ingredients, (ing: RecipeIngredient) => {
                    Text(ing.food).fontSize(11).fontColor('#8a9aaa')
                      .padding({ left: 8, right: 8, top: 2, bottom: 2 })
                      .backgroundColor('#f0f2f5').borderRadius(6)
                      .margin({ right: 6 })
                  })
                }.margin({ top: 8 })

                // 推荐分数
                if (item.score !== undefined) {
                  Text('匹配度 ' + item.score.toFixed(0) + '%')
                    .fontSize(12).fontColor('#2d8a4e').margin({ top: 4 })
                }
              }
              .width('100%').padding(16).backgroundColor('#ffffff').borderRadius(12)
              .shadow({ radius: 4, color: '#10000000', offsetY: 2 })
            }
            .margin({ top: 8, left: 20, right: 20 })
          })
        }
        .width('100%').layoutWeight(1).margin({ top: 8 })
      } else {
        Text(this.statusMsg).fontSize(14).fontColor('#8a9aaa').margin({ top: 80 })
          .width('100%').textAlign(TextAlign.Center)
      }
    }
    .width('100%').height('100%').backgroundColor('#f4f6f9')
  }
}
