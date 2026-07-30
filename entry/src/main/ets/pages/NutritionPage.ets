import router from '@ohos.router';
import { httpUtil } from '../utils/HttpUtil';
import { FoodItem, NutritionDetail, FoodListResponse, I18nDict } from '../utils/DataModels';
import { Light, Dark, ThemeColors } from '../utils/Theme';
import { zh } from '../utils/i18n/zh';
import { en } from '../utils/i18n/en';

@Entry
@Component
struct NutritionPage {
  @StorageLink('isDark') isDark: boolean = false
  @StorageLink('language') language: string = 'zh'
  @State currentTheme: ThemeColors = Light
  @State i18n: I18nDict = zh
  @State foods: FoodItem[] = []
  @State allFoods: FoodItem[] = []
  @State selected: FoodItem | null = null
  @State detail: NutritionDetail | null = null
  @State loading: boolean = true
  @State weight: number = 100
  @State selectedIndex: number = -1
  @State searchQuery: string = ''

  goBack(): void { router.back() }

  aboutToAppear(): void {
    this.currentTheme = this.isDark ? Dark : Light
    this.i18n = this.language === 'zh' ? zh : en
    this.loadList()
  }

  loadList(): void {
    httpUtil.get('/api/nutrition/list').then((json: string): void => {
      let res: FoodListResponse = JSON.parse(json) as FoodListResponse
      this.allFoods = res.foods
      this.foods = res.foods
      this.loading = false
    }).catch((): void => { this.loading = false })
  }

  searchFoods(): void {
    if (!this.searchQuery) { this.foods = this.allFoods; return }
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
    if (this.selected) { this.loadDetail(this.selected.key) }
  }

  build() {
    Column() {
      Row() {
        Text('← ' + this.i18n.back).fontSize(15).fontColor(this.currentTheme.accent)
          .onClick(() => { this.goBack() })
        Text(this.i18n.nutritionDB).fontSize(18).fontWeight(600)
          .fontColor(this.currentTheme.text).layoutWeight(1).textAlign(TextAlign.Center)
        Row().width(60)
      }.width('100%').padding({ left: 16, right: 16, top: 16, bottom: 8 })

      if (this.loading) {
        Blank()
        Text(this.i18n.loading).fontSize(14).fontColor(this.currentTheme.textSecondary)
        Blank()
      } else {
        TextInput({ placeholder: this.i18n.searchFood })
          .onChange((value: string): void => { this.searchQuery = value; this.searchFoods() })
          .width('100%').height(40)
          .backgroundColor(this.currentTheme.card).borderRadius(8)
          .padding({ left: 12, right: 12 })
          .margin({ left: 16, right: 16, bottom: 8 })

        if (this.detail) { this.DetailView() }

        if (this.foods.length === 0) {
          Blank()
          Text(this.i18n.noResults).fontSize(14).fontColor(this.currentTheme.textSecondary)
          Blank()
        } else {
          List() {
            ForEach(this.foods, (food: FoodItem, i: number) => {
              ListItem() {
                Row() {
                  Column() {
                    Text(food.name_cn).fontSize(15).fontWeight(500).fontColor(this.currentTheme.text)
                    Text(food.category).fontSize(11).fontColor(this.currentTheme.textHint).margin({ top: 2 })
                  }.alignItems(HorizontalAlign.Start)
                  Blank()
                  Column() {
                    Text(food.calories_per_100g + '').fontSize(16).fontWeight(600).fontColor(this.currentTheme.accent)
                    Text(this.i18n.kcal + this.i18n.per100g).fontSize(10).fontColor(this.currentTheme.textSecondary)                  }.alignItems(HorizontalAlign.End)
                }
                .width('100%').padding({ left: 14, right: 14, top: 12, bottom: 12 })
                .backgroundColor(this.selectedIndex === i ? this.currentTheme.accent + '10' : this.currentTheme.card)
                .borderRadius(8).margin({ bottom: 4, left: 16, right: 16 })
                .onClick(() => { this.onSelect(i as number) })
              }
            })
          }
          .width('100%').layoutWeight(1)
        }
      }
    }.width('100%').height('100%').backgroundColor(this.currentTheme.bg)
  }

  @Builder
  DetailView() {
    Column() {
      Row() {
        Text(this.selected!.name_cn).fontSize(22).fontWeight(600).fontColor(this.currentTheme.text)
        Blank()
        Text('×').fontSize(18).fontWeight(200).fontColor(this.currentTheme.textSecondary)
          .onClick((): void => { this.detail = null; this.selectedIndex = -1 })
      }.width('100%')
      Text(this.selected!.category).fontSize(12).fontColor(this.currentTheme.textHint).margin({ top: 2 })

      Divider().margin({ top: 12, bottom: 12 }).color(this.currentTheme.border)

      Row() {
        Text(this.i18n.weight).fontSize(13).fontColor(this.currentTheme.textSecondary).width(48)
        Button('−').fontSize(16).fontColor(this.currentTheme.accent).width(36).height(36).backgroundColor('transparent')
          .onClick((): void => { if (this.weight > 10) { this.weight -= 10; this.onWeightChange() } })
        Slider({ value: this.weight, min: 10, max: 500, step: 10 })
          .blockColor(this.currentTheme.accent).trackColor(this.currentTheme.border).width('100%').layoutWeight(1)
        Button('+').fontSize(16).fontColor(this.currentTheme.accent).width(36).height(36).backgroundColor('transparent')
          .onClick((): void => { if (this.weight < 500) { this.weight += 10; this.onWeightChange() } })
      }.width('100%')
      Text(this.weight + 'g').fontSize(15).fontWeight(600).fontColor(this.currentTheme.text)
        .textAlign(TextAlign.Center).width('100%').margin({ top: 8 })

      Grid() {
        GridItem() { this.NutriCard(this.i18n.calories, this.detail!.calories + '', 'kcal', this.currentTheme.accent) }
        GridItem() { this.NutriCard(this.i18n.protein, this.detail!.protein_g + '', 'g', '#FF6B6B') }
        GridItem() { this.NutriCard(this.i18n.fat, this.detail!.fat_g + '', 'g', '#FFD93D') }
        GridItem() { this.NutriCard(this.i18n.carbs, this.detail!.carbs_g + '', 'g', '#6BCB77') }
        GridItem() { this.NutriCard(this.i18n.fiber, this.detail!.fiber_g + '', 'g', '#4D96FF') }
      }.columnsTemplate('1fr 1fr').rowsGap(8).columnsGap(8).width('100%').margin({ top: 12 })
    }
    .width('100%').padding(16)
    .backgroundColor(this.currentTheme.card).borderRadius(12).margin({ left: 12, right: 12, bottom: 8 })
  }

  @Builder
  NutriCard(label: string, value: string, unit: string, accent: string) {
    Column() {
      Text(label).fontSize(10).fontColor(this.currentTheme.textHint)
      Text(value).fontSize(24).fontWeight(300).fontColor(accent).margin({ top: 4 })
      Text(unit).fontSize(9).fontColor(this.currentTheme.textHint)
    }
    .width('100%').padding(14)
    .backgroundColor(this.currentTheme.bg).borderRadius(8)
  }
}
