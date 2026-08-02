import { httpUtil } from '../utils/HttpUtil';
import { FoodItem, NutritionDetail, FoodListResponse, I18nDict } from '../utils/DataModels';
import { Theme } from '../utils/Theme';
import { LocalData } from '../utils/LocalData';
import { zh } from '../utils/i18n/zh';
import { en } from '../utils/i18n/en';

@Entry
@Component
struct NutritionPage {
  @StorageLink('themeMode') themeMode: string = 'system'
  @StorageLink('styleMode') styleMode: string = 'glass'
  @StorageLink('fontScale') fontScale: number = 1
  @StorageLink('language') language: string = 'zh'
  // 页面每次显示时自增，强制整页重绘
  @State themeTick: number = 0
  @State i18n: I18nDict = zh
  @State foods: FoodItem[] = []
  @State allFoods: FoodItem[] = []
  @State selected: FoodItem | null = null
  @State detail: NutritionDetail | null = null
  @State loading: boolean = true
  @State weight: number = 100
  @State weightInput: string = ''
  @State editingWeight: boolean = false
  @State selectedIndex: number = -1
  @State searchQuery: string = ''
  // 开发板传感器称重（实时）
  @State sensorWeight: number = -1
  @State sensorOnline: boolean = false

  goBack(): void {
    // 详情卡展开时：先收起详情卡（回到列表），再按返回才退出页面
    if (this.selected) {
      this.selected = null
      this.selectedIndex = -1
      this.detail = null
    } else {
      this.getUIContext().getRouter().back()
    }
  }

  // 系统返回键：同样先收起详情卡
  onBackPress(): boolean {
    if (this.selected) {
      this.selected = null
      this.selectedIndex = -1
      this.detail = null
      return true
    }
    return false
  }

  aboutToAppear(): void {
    this.i18n = this.language === 'zh' ? zh : en
    this.loadList()
  }

  onPageShow(): void {
    // 页面被压栈时收不到 AppStorage 通知，回到前台强制同步最新设置
    let mode = AppStorage.get<string>('themeMode') || 'system'
    let scale = AppStorage.get<number>('fontScale') || 1
    let lang = AppStorage.get<string>('language') || 'zh'
    if (mode !== this.themeMode) this.themeMode = mode
    if (scale !== this.fontScale) this.fontScale = scale
    if (lang !== this.language) this.language = lang
    let style = AppStorage.get<string>('styleMode') || 'glass'
    if (style !== this.styleMode) this.styleMode = style
    this.i18n = lang === 'zh' ? zh : en
    this.themeTick++
  }

  loadList(): void {
    httpUtil.get('/api/nutrition/list').then((json: string): void => {
      let res: FoodListResponse = JSON.parse(json) as FoodListResponse
      this.allFoods = res.foods
      this.foods = res.foods
      this.loading = false
    }).catch((): void => {
      // 后端未启动：使用离线预载数据（中国食物成分表）
      this.allFoods = LocalData.foodList()
      this.foods = this.allFoods
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
    this.weightInput = this.weight + ''
    this.loadSensorWeight()
  }

  // 拉取开发板传感器称重数据
  async loadSensorWeight(): Promise<void> {
    try {
      let resp = await httpUtil.getBoardStatus()
      if (resp.success && resp.online && resp.data && resp.data.weight_g !== undefined) {
        this.sensorWeight = resp.data.weight_g
        this.sensorOnline = true
      } else {
        this.sensorOnline = false
      }
    } catch (e) {
      this.sensorOnline = false
    }
  }

  // build 中调用：每次渲染按最新 weight 实时计算营养（读 this.weight → 建立依赖 → 变化即重绘）
  curDetail(): NutritionDetail | null {
    if (!this.selected) return null
    return LocalData.nutrition(this.selected.key, this.weight)
  }

  // 输入框提交：回车或失焦时应用输入的数字并恢复大字显示
  applyWeightInput(): void {
    let w = Number(this.weightInput)
    if (!isNaN(w) && w >= 10 && w <= 500) {
      this.weight = w
      this.weightInput = this.weight + ''
    } else {
      this.weightInput = this.weight + ''
    }
    this.editingWeight = false
  }


  build() {
    Column() {
      // 页面大标题
      Text(this.i18n.nutritionDB)
        .fontFamily('Inter').fontSize(Theme.FONT_TITLE)
        .fontWeight(600)
        .fontColor(Theme.TEXT_SYS)
                .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, bottom: Theme.SPACE_SM })

      if (this.loading) {
        Blank()
        Text(this.i18n.loading)
          .fontFamily('Inter').fontSize(Theme.FONT_BODY)
          .fontColor(Theme.TEXT_SYS_SECONDARY)
        Blank()
      } else {
        Column() {
          TextInput({ placeholder: this.i18n.searchFood })
            .onChange((value: string): void => {
              this.searchQuery = value
              this.searchFoods()
            })
            .width('100%')
            .height(40)
            .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER })
            .borderRadius(Theme.RADIUS_SM)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD })
        }
        .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, bottom: Theme.SPACE_SM })

        // ===== 食材详情卡（直接内联在页面 build：@State weight 变化 → 页面重绘 → 全部实时重算）=====
        if (this.selected) {
          Column() {
            // 标题行
            Row() {
              Text(this.selected.name_cn)
                .fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT_SYS)
                .layoutWeight(1).maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
              Text('×')
                .fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(300)
                .fontColor(Theme.TEXT_SYS_SECONDARY)
                .onClick((): void => {
                  this.selected = null
                  this.selectedIndex = -1
                  this.detail = null
                })
            }
            .width('100%')

            Text(this.selected.category)
              .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
              .margin({ top: Theme.SPACE_XS })

            Divider()
              .margin({ top: Theme.SPACE_MD, bottom: Theme.SPACE_MD })
              .color(Theme.BORDER)

            // 滑块行：− / 滑块 / +（左右对称）
            Row() {
              Button('−')
                .fontFamily('Inter').fontSize(Theme.FONT_SUB).fontColor(Theme.PRIMARY)
                .width(36).height(36)
                .backgroundColor(Theme.PRIMARY_LIGHT).borderRadius(Theme.RADIUS_SM)
                .onClick((): void => {
                  if (this.weight > 10) {
                    this.weight = this.weight - 10
                    this.weightInput = this.weight + ''
                  }
                })
              Slider({ value: this.weight, min: 10, max: 500, step: 10 })
                .blockColor(Theme.PRIMARY).trackColor(Theme.BORDER)
                .layoutWeight(1)
                .onChange((value: number): void => {
                  this.weight = value
                  this.weightInput = this.weight + ''
                })
              Button('+')
                .fontFamily('Inter').fontSize(Theme.FONT_SUB).fontColor(Theme.PRIMARY)
                .width(36).height(36)
                .backgroundColor(Theme.PRIMARY_LIGHT).borderRadius(Theme.RADIUS_SM)
                .onClick((): void => {
                  if (this.weight < 500) {
                    this.weight = this.weight + 10
                    this.weightInput = this.weight + ''
                  }
                })
            }
            .width('100%')

            // 当前克数（大号显示，点击可直接输入修改）
            if (!this.editingWeight) {
              Text(this.weight + 'g')
                .fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(700).fontColor(Theme.PRIMARY)
                .textAlign(TextAlign.Center).width('100%')
                .margin({ top: Theme.SPACE_MD })
                .onClick((): void => {
                  this.weightInput = this.weight + ''
                  this.editingWeight = true
                })
            } else {
              Row() {
                TextInput({ text: this.weightInput })
                  .width(120).height(42)
                  .backgroundColor(Theme.GLASS_BG).borderRadius(Theme.RADIUS_SM)
                  .textAlign(TextAlign.Center).fontFamily('Inter').fontSize(Theme.FONT_HEADING)
                  .onChange((v: string): void => { this.weightInput = v })
                  .onSubmit((): void => { this.applyWeightInput() })
                  .onBlur((): void => { this.applyWeightInput() })
                Text('g')
                  .fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(700).fontColor(Theme.PRIMARY)
                  .margin({ left: Theme.SPACE_XS })
              }
              .justifyContent(FlexAlign.Center).width('100%')
              .margin({ top: Theme.SPACE_MD })
            }

            // 开发板传感器称重：点击"使用"即按传感器重量实时计算营养
            if (this.sensorOnline && this.sensorWeight > 0) {
              Row() {
                Text('开发板称重: ' + this.sensorWeight + 'g')
                  .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS)
                Button() {
                  Text('使用').fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.ON_PRIMARY)
                }
                .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY).linearGradient({ angle: 135, colors: [['#E8967A', 0.0], ['#D97757', 1.0]] }).height(28)
                .margin({ left: Theme.SPACE_SM })
                .onClick((): void => {
                  this.weight = this.sensorWeight
                  this.weightInput = this.weight + ''
                })
              }
              .justifyContent(FlexAlign.Center).width('100%')
              .margin({ top: Theme.SPACE_MD })
            }


            // 营养网格（完全内联，与克数大字同层级：页面重绘时数值必然重新求值）
            if (this.curDetail()) {
              Grid() {
                GridItem() {
                  Column() {
                    Text(this.i18n.calories).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                    Text(LocalData.nutrition(this.selected.key, this.weight)!.calories + '').fontFamily('Inter').fontSize(Theme.FONT_NUM).fontWeight(300)
                      .fontColor(Theme.PRIMARY).margin({ top: Theme.SPACE_XS })
                    Text('kcal').fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                  }
                  .width('100%').padding(Theme.SPACE_MD).backgroundColor(Theme.BG).borderRadius(Theme.RADIUS_MD)
                }
                GridItem() {
                  Column() {
                    Text(this.i18n.protein).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                    Text(LocalData.nutrition(this.selected.key, this.weight)!.protein_g + '').fontFamily('Inter').fontSize(Theme.FONT_NUM).fontWeight(300)
                      .fontColor(Theme.SUCCESS).margin({ top: Theme.SPACE_XS })
                    Text('g').fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                  }
                  .width('100%').padding(Theme.SPACE_MD).backgroundColor(Theme.BG).borderRadius(Theme.RADIUS_MD)
                }
                GridItem() {
                  Column() {
                    Text(this.i18n.fat).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                    Text(LocalData.nutrition(this.selected.key, this.weight)!.fat_g + '').fontFamily('Inter').fontSize(Theme.FONT_NUM).fontWeight(300)
                      .fontColor(Theme.WARNING).margin({ top: Theme.SPACE_XS })
                    Text('g').fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                  }
                  .width('100%').padding(Theme.SPACE_MD).backgroundColor(Theme.BG).borderRadius(Theme.RADIUS_MD)
                }
                GridItem() {
                  Column() {
                    Text(this.i18n.carbs).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                    Text(LocalData.nutrition(this.selected.key, this.weight)!.carbs_g + '').fontFamily('Inter').fontSize(Theme.FONT_NUM).fontWeight(300)
                      .fontColor(Theme.DANGER).margin({ top: Theme.SPACE_XS })
                    Text('g').fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                  }
                  .width('100%').padding(Theme.SPACE_MD).backgroundColor(Theme.BG).borderRadius(Theme.RADIUS_MD)
                }
                GridItem() {
                  Column() {
                    Text(this.i18n.fiber).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                    Text(LocalData.nutrition(this.selected.key, this.weight)!.fiber_g + '').fontFamily('Inter').fontSize(Theme.FONT_NUM).fontWeight(300)
                      .fontColor(Theme.PRIMARY_DARK).margin({ top: Theme.SPACE_XS })
                    Text('g').fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                  }
                  .width('100%').padding(Theme.SPACE_MD).backgroundColor(Theme.BG).borderRadius(Theme.RADIUS_MD)
                }
              }
              .columnsTemplate('1fr 1fr')
              .rowsGap(Theme.SPACE_SM).columnsGap(Theme.SPACE_SM)
              .width('100%')
              .margin({ top: Theme.SPACE_MD })
            }
          }
          .padding(Theme.SPACE_MD)
          .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER })
          .borderRadius(Theme.RADIUS_LG)
          .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
          .margin({ bottom: Theme.SPACE_MD })
        }

        if (this.foods.length === 0) {
          Blank()
          Text(this.i18n.noResults)
            .fontFamily('Inter').fontSize(Theme.FONT_BODY)
            .fontColor(Theme.TEXT_SYS_SECONDARY)
          Blank()
        } else {
          List() {
            ForEach(this.foods, (food: FoodItem, i: number) => {
              ListItem() {
                Row() {
                  Column() {
                    Text(food.name_cn)
                      .fontFamily('Inter').fontSize(Theme.FONT_SUB)
                      .fontWeight(500)
                      .fontColor(Theme.TEXT_SYS)
                      .maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
                    Text(food.category)
                      .fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
                      .fontColor(Theme.TEXT_SYS_TERTIARY)
                      .margin({ top: Theme.SPACE_XS })
                  }
                  .alignItems(HorizontalAlign.Start).layoutWeight(1)

                  Column() {
                    Text(food.calories_per_100g + '')
                      .fontFamily('Inter').fontSize(Theme.FONT_SUB)
                      .fontWeight(600)
                      .fontColor(Theme.PRIMARY)
                    Text(this.i18n.kcal + this.i18n.per100g)
                      .fontFamily('Inter').fontSize(Theme.FONT_MICRO)
                      .fontColor(Theme.TEXT_SYS_SECONDARY)
                      .margin({ top: Theme.SPACE_XS })
                  }
                  .alignItems(HorizontalAlign.End)
                  .margin({ left: Theme.SPACE_SM })
                }
                                .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_MD, bottom: Theme.SPACE_MD })
                .backgroundColor(this.selectedIndex === i ? Theme.PRIMARY_LIGHT : Theme.GLASS_BG)
                .borderRadius(Theme.RADIUS_MD)
                .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
                .margin({ bottom: Theme.SPACE_SM, left: Theme.SPACE_MD, right: Theme.SPACE_MD })
                .onClick((): void => {
                  this.onSelect(i)
                })
                .opacity(this.fontScale > 0 ? 1 : 1)
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
    .linearGradient(Theme.bgGradient(this.themeMode, this.styleMode))
    .opacity(this.themeTick >= 0 && this.fontScale > 0 ? 1 : 1)
  }
}
