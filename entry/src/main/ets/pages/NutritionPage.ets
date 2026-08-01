import router from '@ohos.router';
import { httpUtil } from '../utils/HttpUtil';
import { FoodItem, NutritionDetail, FoodListResponse, I18nDict } from '../utils/DataModels';
import { Theme } from '../utils/Theme';
import { zh } from '../utils/i18n/zh';
import { en } from '../utils/i18n/en';

@Entry
@Component
struct NutritionPage {
  @StorageLink('language') language: string = 'zh'
  @State i18n: I18nDict = zh
  @State foods: FoodItem[] = []
  @State allFoods: FoodItem[] = []
  @State selected: FoodItem | null = null
  @State detail: NutritionDetail | null = null
  @State loading: boolean = true
  @State weight: number = 100
  @State selectedIndex: number = -1
  @State searchQuery: string = ''

  goBack(): void {
    router.back()
  }

  aboutToAppear(): void {
    this.i18n = this.language === 'zh' ? zh : en
    this.loadList()
  }

  loadList(): void {
    httpUtil.get('/api/nutrition/list').then((json: string): void => {
      let res: FoodListResponse = JSON.parse(json) as FoodListResponse
      this.allFoods = res.foods
      this.foods = res.foods
      this.loading = false
    }).catch((): void => {
      this.loading = false
    })
  }

  searchFoods(): void {
    if (!this.searchQuery) {
      this.foods = this.allFoods
      return
    }
    let q: string = this.searchQuery.toLowerCase()
    this.foods = this.allFoods.filter((food: FoodItem): boolean => {
      return food.name_cn.indexOf(q) >= 0 || food.key.indexOf(q) >= 0
    })
  }

  onSelect(index: number): void {
    let food: FoodItem = this.foods[index]
    this.selected = food
    this.selectedIndex = index
    this.detail = null
    this.loadDetail(food.key)
  }

  loadDetail(key: string): void {
    httpUtil.get('/api/nutrition?name=' + key + '&weight=' + this.weight).then((json: string): void => {
      this.detail = JSON.parse(json) as NutritionDetail
    })
  }

  onWeightChange(): void {
    if (this.selected) {
      this.loadDetail(this.selected.key)
    }
  }

  build() {
    Column() {
      // 顶部导航：返回
      Row() {
        Text(this.i18n.back)
          .fontSize(Theme.FONT_BODY)
          .fontWeight(500)
          .fontColor(Theme.PRIMARY)
          .onClick((): void => {
            this.goBack()
          })
      }
      .width('100%')
      .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_MD, bottom: Theme.SPACE_XS })

      // 页面大标题
      Text(this.i18n.nutritionDB)
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
      } else {
        TextInput({ placeholder: this.i18n.searchFood })
          .onChange((value: string): void => {
            this.searchQuery = value
            this.searchFoods()
          })
          .width('100%')
          .height(40)
          .backgroundColor(Theme.SURFACE)
          .borderRadius(Theme.RADIUS_SM)
          .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
          .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD })
          .margin({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, bottom: Theme.SPACE_SM })

        if (this.detail) {
          this.DetailView()
        }

        if (this.foods.length === 0) {
          Blank()
          Text(this.i18n.noResults)
            .fontSize(Theme.FONT_BODY)
            .fontColor(Theme.TEXT_SECONDARY)
          Blank()
        } else {
          List() {
            ForEach(this.foods, (food: FoodItem, i: number) => {
              ListItem() {
                Row() {
                  Column() {
                    Text(food.name_cn)
                      .fontSize(Theme.FONT_SUB)
                      .fontWeight(500)
                      .fontColor(Theme.TEXT)
                    Text(food.category)
                      .fontSize(Theme.FONT_CAPTION)
                      .fontColor(Theme.TEXT_TERTIARY)
                      .margin({ top: Theme.SPACE_XS })
                  }
                  .alignItems(HorizontalAlign.Start)
                  Blank()
                  Column() {
                    Text(food.calories_per_100g + '')
                      .fontSize(Theme.FONT_SUB)
                      .fontWeight(600)
                      .fontColor(Theme.PRIMARY)
                    Text(this.i18n.kcal + this.i18n.per100g)
                      .fontSize(Theme.FONT_MICRO)
                      .fontColor(Theme.TEXT_SECONDARY)
                  }
                  .alignItems(HorizontalAlign.End)
                }
                .width('100%')
                .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_MD, bottom: Theme.SPACE_MD })
                .backgroundColor(this.selectedIndex === i ? Theme.PRIMARY_LIGHT : Theme.SURFACE)
                .borderRadius(Theme.RADIUS_MD)
                .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
                .margin({ bottom: Theme.SPACE_SM, left: Theme.SPACE_MD, right: Theme.SPACE_MD })
                .onClick((): void => {
                  this.onSelect(i)
                })
              }
            })
          }
          .width('100%')
          .layoutWeight(1)
        }
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG)
  }

  @Builder
  DetailView() {
    Column() {
      Row() {
        Text(this.selected!.name_cn)
          .fontSize(Theme.FONT_HEADING)
          .fontWeight(600)
          .fontColor(Theme.TEXT)
        Blank()
        Text('×')
          .fontSize(Theme.FONT_SUB)
          .fontWeight(300)
          .fontColor(Theme.TEXT_SECONDARY)
          .onClick((): void => {
            this.detail = null
            this.selectedIndex = -1
          })
      }
      .width('100%')
      Text(this.selected!.category)
        .fontSize(Theme.FONT_CAPTION)
        .fontColor(Theme.TEXT_TERTIARY)
        .margin({ top: Theme.SPACE_XS })

      Divider()
        .margin({ top: Theme.SPACE_MD, bottom: Theme.SPACE_MD })
        .color(Theme.BORDER)

      Row() {
        Text(this.i18n.weight)
          .fontSize(Theme.FONT_CAPTION)
          .fontColor(Theme.TEXT_SECONDARY)
          .width(48)
        Button('−')
          .fontSize(Theme.FONT_SUB)
          .fontColor(Theme.PRIMARY)
          .width(36)
          .height(36)
          .backgroundColor(Theme.PRIMARY_LIGHT)
          .borderRadius(Theme.RADIUS_SM)
          .onClick((): void => {
            if (this.weight > 10) {
              this.weight -= 10
              this.onWeightChange()
            }
          })
        Slider({ value: this.weight, min: 10, max: 500, step: 10 })
          .blockColor(Theme.PRIMARY)
          .trackColor(Theme.BORDER)
          .width('100%')
          .layoutWeight(1)
        Button('+')
          .fontSize(Theme.FONT_SUB)
          .fontColor(Theme.PRIMARY)
          .width(36)
          .height(36)
          .backgroundColor(Theme.PRIMARY_LIGHT)
          .borderRadius(Theme.RADIUS_SM)
          .onClick((): void => {
            if (this.weight < 500) {
              this.weight += 10
              this.onWeightChange()
            }
          })
      }
      .width('100%')
      Text(this.weight + 'g')
        .fontSize(Theme.FONT_BODY)
        .fontWeight(600)
        .fontColor(Theme.TEXT)
        .textAlign(TextAlign.Center)
        .width('100%')
        .margin({ top: Theme.SPACE_SM })

      Grid() {
        GridItem() {
          this.NutriCard(this.i18n.calories, this.detail!.calories + '', 'kcal', Theme.PRIMARY)
        }
        GridItem() {
          this.NutriCard(this.i18n.protein, this.detail!.protein_g + '', 'g', Theme.SUCCESS)
        }
        GridItem() {
          this.NutriCard(this.i18n.fat, this.detail!.fat_g + '', 'g', Theme.WARNING)
        }
        GridItem() {
          this.NutriCard(this.i18n.carbs, this.detail!.carbs_g + '', 'g', Theme.DANGER)
        }
        GridItem() {
          this.NutriCard(this.i18n.fiber, this.detail!.fiber_g + '', 'g', Theme.PRIMARY_DARK)
        }
      }
      .columnsTemplate('1fr 1fr')
      .rowsGap(Theme.SPACE_SM)
      .columnsGap(Theme.SPACE_SM)
      .width('100%')
      .margin({ top: Theme.SPACE_MD })
    }
    .width('100%')
    .padding(Theme.SPACE_MD)
    .backgroundColor(Theme.SURFACE)
    .borderRadius(Theme.RADIUS_LG)
    .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
    .margin({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, bottom: Theme.SPACE_SM })
  }

  @Builder
  NutriCard(label: string, value: string, unit: string, accent: string) {
    Column() {
      Text(label)
        .fontSize(Theme.FONT_MICRO)
        .fontColor(Theme.TEXT_TERTIARY)
      Text(value)
        .fontSize(24)
        .fontWeight(300)
        .fontColor(accent)
        .margin({ top: Theme.SPACE_XS })
      Text(unit)
        .fontSize(Theme.FONT_MICRO)
        .fontColor(Theme.TEXT_TERTIARY)
    }
    .width('100%')
    .padding(Theme.SPACE_MD)
    .backgroundColor(Theme.BG)
    .borderRadius(Theme.RADIUS_MD)
  }
}
