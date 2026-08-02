import { cameraPicker, camera } from '@kit.CameraKit';
import { image } from '@kit.ImageKit';
import fs from '@ohos.file.fs';
import common from '@ohos.app.ability.common';
import { httpUtil } from '../utils/HttpUtil';
import { AppStorage as DataStore, RecognizeResult, HealthScoreResponse, I18nDict, NutritionDetail } from '../utils/DataModels';
import { Theme } from '../utils/Theme';
import { SystemBar } from '../utils/SystemBar';
import { LocalData } from '../utils/LocalData';
import { TabNutrition } from '../components/TabNutrition';
import { TabRecipes } from '../components/TabRecipes';
import { TabChat } from '../components/TabChat';
import { TabMe } from '../components/TabMe';
import { zh } from '../utils/i18n/zh';
import { en } from '../utils/i18n/en';

// ============================================
// SmartKitchen 主框架 — 5 Tab 大厂架构
// Tab1 首页(拍照识别/整餐) / Tab2 营养(评分) / Tab3 菜谱 / Tab4 助手(AI) / Tab5 我的
// 视觉: Material 3 + HarmonyOS Design
// ============================================

@Entry
@Component
struct Index {
  @StorageLink('themeMode') themeMode: string = 'system'
  @StorageLink('fontScale') fontScale: number = 1
  @StorageLink('language') language: string = 'zh'
  // 页面每次显示时自增，强制整页/所有 @Builder 重绘（绕开页面冻结时通知丢失）
  @State themeTick: number = 0
  // 页面每次显示自增：ForEach key 变化 → 内容整块重建 → 字体/语言/主题立即生效
  @State uiVersion: number = 0
  @State currentTab: number = 0
  @State photoPath: string = ''
  @State isRecognizing: boolean = false
  @State result: RecognizeResult | null = null
  @State photoPixelMap: image.PixelMap | null = null
  @State statusText: string = '点击拍照识别食材'
  @State mealMode: boolean = false
  @State mealResult: string = ''
  @State todayCalories: string = '—'
  @State todayFoods: string = '—'
  @State healthScore: HealthScoreResponse | null = null

  aboutToAppear() {
    this.loadTodaySummary()
    this.loadHealth()
    SystemBar.apply()
  }

  onPageShow() {
    // 页面被压栈时收不到 AppStorage 通知，回到前台强制同步最新设置
    let mode = AppStorage.get<string>('themeMode') || 'system'
    let scale = AppStorage.get<number>('fontScale') || 1
    let lang = AppStorage.get<string>('language') || 'zh'
    if (mode !== this.themeMode) this.themeMode = mode
    if (scale !== this.fontScale) this.fontScale = scale
    if (lang !== this.language) this.language = lang
    this.themeTick++
    this.uiVersion++
  }

  async loadTodaySummary() {
    try {
      let resp = await httpUtil.getHistory()
      if (resp && resp.records && resp.records.length > 0) {
        let total = 0
        let names: string[] = []
        resp.records.forEach((item: object) => {
          let it = item as Record<string, Object>
          total += Number(it['calories'] || 0)
          names.push(String(it['food_name_cn'] || it['food_name'] || ''))
        })
        this.todayCalories = total.toFixed(0)
        this.todayFoods = names.slice(0, 3).join(' · ')
      }
    } catch (e) {
      // 后端未启动时静默
    }
  }

  async loadHealth() {
    try {
      let resp = await httpUtil.getHealthScore('default')
      if (resp.success) {
        this.healthScore = resp
      }
    } catch (e) {
      // 静默
    }
  }

  async takePhoto() {
    this.statusText = '拍照中...'
    try {
      let context = this.getUIContext().getHostContext() as common.UIAbilityContext
      let pickerResult = await cameraPicker.pick(
        context,
        [cameraPicker.PickerMediaType.PHOTO],
        { cameraPosition: camera.CameraPosition.CAMERA_POSITION_BACK }
      )
      let uri = pickerResult.resultUri
      let imgSource = image.createImageSource(uri)
      let pixelMap = await imgSource.createPixelMap()
      this.photoPixelMap = pixelMap

      let destPath = context.cacheDir + '/food_' + Date.now() + '.jpg'
      let srcFile = fs.openSync(uri, fs.OpenMode.READ_ONLY)
      let stat = fs.statSync(srcFile.fd)
      let buf = new ArrayBuffer(stat.size)
      fs.readSync(srcFile.fd, buf)
      await fs.close(srcFile)
      let destFile = fs.openSync(destPath, fs.OpenMode.CREATE | fs.OpenMode.WRITE_ONLY)
      fs.writeSync(destFile.fd, buf)
      await fs.close(destFile)

      this.photoPath = destPath
      this.statusText = '已拍照，点击识别'
    } catch (e) {
      this.statusText = '拍照失败'
    }
  }

  async recognizePhoto() {
    if (!this.photoPath) return
    this.isRecognizing = true
    this.statusText = '识别中...'
    try {
      if (this.mealMode) {
        // 整餐多食材分析
        let resp = await httpUtil.recognizeMeal(this.photoPath)
        if (resp.success) {
          if (resp.summary) {
            this.mealResult = resp.message + ' | 总热量 ' + resp.summary.calories + ' kcal'
            this.result = null
            this.statusText = resp.message
          } else {
            this.mealResult = resp.message
            this.statusText = resp.message
          }
        } else {
          this.statusText = '整餐识别失败'
        }
      } else {
        // 单食材识别
        let resp = await httpUtil.recognize(this.photoPath)
        if (resp.success) {
          this.result = resp.prediction
          DataStore.lastRecognizeResult = resp.prediction
          this.statusText = '识别结果: ' + resp.prediction.name
        } else {
          this.statusText = '识别失败'
        }
      }
    } catch (e) {
      this.statusText = '网络错误'
    }
    this.isRecognizing = false
  }

  // 一键记录识别结果到历史（按 100g 记录营养）
  async logToHistory(): Promise<void> {
    if (!this.result) return
    let d: NutritionDetail | null = LocalData.nutrition(this.result.name, 100)
    let cal = d ? d.calories : 0
    let p = d ? d.protein_g : 0
    let f = d ? d.fat_g : 0
    let c = d ? d.carbs_g : 0
    try {
      let ok = await httpUtil.logFood(this.result.name_cn, 100, cal, p, f, c,
        this.result.confidence, DataStore.currentMember)
      this.statusText = ok ? this.i18n().logSuccess : this.i18n().logFail
    } catch (e) {
      this.statusText = this.i18n().logFail
    }
  }

  // ===== 导航 =====
  goToNutrition() { this.getUIContext().getRouter().pushUrl({ url: 'pages/NutritionPage' }).catch(() => {}) }
  goToRecipes() { this.getUIContext().getRouter().pushUrl({ url: 'pages/RecipesPage' }).catch(() => {}) }
  goToGuidelines() { this.getUIContext().getRouter().pushUrl({ url: 'pages/GuidelinesPage' }).catch(() => {}) }
  goToMembers() { this.getUIContext().getRouter().pushUrl({ url: 'pages/MembersPage' }).catch(() => {}) }
  goToFace() { this.getUIContext().getRouter().pushUrl({ url: 'pages/FacePage' }).catch(() => {}) }
  goToHistory() { this.getUIContext().getRouter().pushUrl({ url: 'pages/HistoryPage' }).catch(() => {}) }
  goToChat() { this.getUIContext().getRouter().pushUrl({ url: 'pages/ChatPage' }).catch(() => {}) }
  goToSettings() { this.getUIContext().getRouter().pushUrl({ url: 'pages/SettingsPage' }).catch(() => {}) }

  i18n(): I18nDict {
    return this.language === 'zh' ? zh : en
  }

  // ===== Tab 线性图标（自绘，非 emoji）=====
  @Builder
  IconCamera(active: boolean) {
    Stack({ alignContent: Alignment.Center }) {
      Text('').width(22).height(15)
        .border({ width: 1.5, color: active ? Theme.PRIMARY : '#9CA3AF' })
        .borderRadius(4)
      Text('').width(7).height(7)
        .border({ width: 1.5, color: active ? Theme.PRIMARY : '#9CA3AF' })
        .borderRadius(4)
    }.width(28).height(24)
  }

  @Builder
  IconChart(active: boolean) {
    Row({ space: 3 }) {
      Text('').width(4).height(10)
        .backgroundColor(active ? Theme.PRIMARY : '#9CA3AF').borderRadius(1)
      Text('').width(4).height(16)
        .backgroundColor(active ? Theme.PRIMARY : '#9CA3AF').borderRadius(1)
      Text('').width(4).height(13)
        .backgroundColor(active ? Theme.PRIMARY : '#9CA3AF').borderRadius(1)
    }.width(28).height(24).justifyContent(FlexAlign.Center)
  }

  @Builder
  IconPlate(active: boolean) {
    Stack({ alignContent: Alignment.Center }) {
      Text('').width(22).height(22)
        .border({ width: 1.5, color: active ? Theme.PRIMARY : '#9CA3AF' })
        .borderRadius(11)
      Text('').width(8).height(8)
        .border({ width: 1.2, color: active ? Theme.PRIMARY : '#9CA3AF' })
        .borderRadius(4)
    }.width(28).height(24)
  }

  @Builder
  IconUser(active: boolean) {
    Stack({ alignContent: Alignment.Top }) {
      Text('').width(8).height(8)
        .border({ width: 1.5, color: active ? Theme.PRIMARY : '#9CA3AF' })
        .borderRadius(4)
        .margin({ top: 2 })
      Text('').width(18).height(11)
        .border({ width: 1.5, color: active ? Theme.PRIMARY : '#9CA3AF' })
        .borderRadius({ topLeft: 9, topRight: 9, bottomLeft: 0, bottomRight: 0 })
        .margin({ top: 11 })
    }.width(28).height(24).alignContent(Alignment.Center)
  }

  @Builder
  IconChat(active: boolean) {
    Stack({ alignContent: Alignment.Center }) {
      Text('').width(22).height(16)
        .border({ width: 1.5, color: active ? Theme.PRIMARY : '#9CA3AF' })
        .borderRadius(5)
      Text('').width(6).height(6)
        .backgroundColor(active ? Theme.PRIMARY : '#9CA3AF')
        .borderRadius(3)
        .margin({ left: -10, top: 8 })
    }.width(28).height(24).alignContent(Alignment.Center)
  }

  @Builder
  TabBarItem(index: number, label: string) {
    Column() {
      if (index === 0) {
        this.IconCamera(this.currentTab === 0)
      } else if (index === 1) {
        this.IconChart(this.currentTab === 1)
      } else if (index === 2) {
        this.IconPlate(this.currentTab === 2)
      } else if (index === 3) {
        this.IconChat(this.currentTab === 3)
      } else {
        this.IconUser(this.currentTab === 4)
      }
      Text(label)
        .fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
        .fontColor(this.currentTab === index ? Theme.PRIMARY : Theme.TEXT_SYS_TERTIARY)
        .margin({ top: 2 })
    }
    .justifyContent(FlexAlign.Center)
    .width('100%').height('100%')
  }

  // ===== Tab2 营养概览 =====
  // mode/scale 按值传参：参数变化时 @Builder 才会重新渲染（ArkUI 官方机制）

  // ===== Tab3 菜谱概览 =====

  // ===== Tab4 助手 =====

  // ===== Tab5 我的（iOS 设置风格）=====

  // ===== 主布局 =====
  build() {
    Column() {
      // 页面每次显示强制重建：uiVersion 变化 → ForEach key 变化 → 整块重建 → 字体/语言/主题立即生效
      // 内容区：Swiper 左右滑动切换（微信式）
      Swiper() {
        // Tab1 首页
Scroll() {
          Column() {
            Row() {
              Text(this.i18n().appName).fontFamily('Inter').fontSize(Theme.FONT_BRAND).fontWeight(600).fontColor(Theme.TEXT_SYS).letterSpacing(0.5)
                .maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
            }
            .padding({ top: 12, bottom: 4, left: Theme.SPACE_LG, right: Theme.SPACE_LG })

          Text(this.statusText)
            .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY)
            .padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG, top: 6, bottom: 10 })

          // 模式切换（单食材 / 整餐）
          Row({ space: Theme.SPACE_SM }) {
            Text(this.i18n().singleFood).fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
              .fontColor(this.mealMode ? Theme.TEXT_SYS_TERTIARY : Theme.ON_PRIMARY)
              .padding({ left: 14, right: 14, top: 6, bottom: 6 })
              .backgroundColor(this.mealMode ? Theme.GLASS_BG : Theme.PRIMARY)
              .borderRadius(Theme.RADIUS_FULL)
              .onClick(() => { this.mealMode = false; this.result = null; this.mealResult = '' })
            Text(this.i18n().mealAnalysis).fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
              .fontColor(this.mealMode ? Theme.ON_PRIMARY : Theme.TEXT_SYS_TERTIARY)
              .padding({ left: 14, right: 14, top: 6, bottom: 6 })
              .backgroundColor(this.mealMode ? Theme.PRIMARY : Theme.GLASS_BG)
              .borderRadius(Theme.RADIUS_FULL)
              .onClick(() => { this.mealMode = true; this.result = null; this.mealResult = '' })
          }
          .padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG, bottom: 10 })

          // 拍照区（卡片）
          Stack() {
            if (this.photoPixelMap) {
              Image(this.photoPixelMap).width('100%').height(250).objectFit(ImageFit.Contain)
            } else {
              Column() {
                this.IconCamera(false)
                Text(this.mealMode ? '拍摄整桌餐食，自动分析多种食材' : '点击下方按钮拍照识别食材')
                  .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_TERTIARY).margin({ top: 14 })
              }
              .justifyContent(FlexAlign.Center).width('100%').height(250)
            }
          }
          .width('100%')
          .backgroundColor(Theme.GLASS_BG).backdropBlur(Theme.GLASS_BLUR).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_LG)
          .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
          .padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG })

          // 操作按钮
          Row({ space: Theme.SPACE_MD }) {
            Button() {
              Text(this.i18n().takePhoto).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.PRIMARY)
            }
            .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY_LIGHT)
            .width(140).height(46).layoutWeight(1)
            .onClick(() => this.takePhoto())

            Button() {
              if (this.isRecognizing) {
                LoadingProgress().width(18).height(18).color(Theme.ON_PRIMARY)
              } else {
                Text(this.i18n().recognize).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.ON_PRIMARY)
              }
            }
            .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY).linearGradient({ angle: 135, colors: [['#E8967A', 0.0], ['#D97757', 1.0]] })
            .width(140).height(46).layoutWeight(1)
            .enabled(!!this.photoPath && !this.isRecognizing)
            .onClick(() => this.recognizePhoto())
          }
          .padding({ top: Theme.SPACE_MD })

          // 识别结果卡片（单食材）
          if (this.result && !this.mealMode) {
            Row() {
              Column() {
                Text(this.result.name).fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT_SYS)
                Text('置信度 ' + (this.result.confidence * 100).toFixed(1) + '%')
                  .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.PRIMARY).margin({ top: 4 })
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)

              Button() { Text('查看营养 ›').fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.ON_PRIMARY) }
                .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY).linearGradient({ angle: 135, colors: [['#E8967A', 0.0], ['#D97757', 1.0]] }).height(34)
                .onClick((): void => this.goToNutrition())
            }
            .padding(Theme.SPACE_MD)
            .backgroundColor(Theme.GLASS_BG).backdropBlur(Theme.GLASS_BLUR).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_MD)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            .margin({ top: Theme.SPACE_MD })
          }
          // 整餐分析结果
          if (this.mealResult.length > 0 && this.mealMode) {
            Row() {
              Column() {
                Text(this.i18n().mealAnalysis).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
                Text(this.mealResult).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS)
                  .margin({ top: 6 }).lineHeight(20)
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)

              Button() { Text('问问营养师 ›').fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.ON_PRIMARY) }
                .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY).linearGradient({ angle: 135, colors: [['#E8967A', 0.0], ['#D97757', 1.0]] }).height(34)
                .onClick((): void => this.goToChat())
            }
            .padding(Theme.SPACE_MD)
            .backgroundColor(Theme.GLASS_BG).backdropBlur(Theme.GLASS_BLUR).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_MD)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            .margin({ top: Theme.SPACE_MD })
          }
          }
          .padding({ top: Theme.SPACE_MD })
          .alignItems(HorizontalAlign.Start)
          .backgroundColor(Theme.bg(this.themeMode))
        .opacity(this.themeTick >= 0 && this.fontScale > 0 ? 1 : 1)
        }
        .width('100%').height('100%').scrollBar(BarState.Off)
        .backgroundColor(Theme.bg(this.themeMode))
        .opacity(this.themeTick >= 0 && this.fontScale > 0 ? 1 : 1)
        // Tab2 营养
TabNutrition({
            healthScore: this.healthScore,
            todayCalories: this.todayCalories,
            todayFoods: this.todayFoods,
            onHistory: (): void => this.goToHistory(),
            onNutrition: (): void => this.goToNutrition()
          })
        // Tab3 菜谱
TabRecipes({
            onRecipes: (): void => this.goToRecipes(),
            onGuidelines: (): void => this.goToGuidelines()
          })
        // Tab4 助手
TabChat({
            onChat: (): void => this.goToChat()
          })
        // Tab5 我的
TabMe({
            onBoard: (): void => { this.getUIContext().getRouter().pushUrl({ url: 'pages/BoardPage' }).catch(() => {}) },
            onHistory: (): void => this.goToHistory(),
            onGuidelines: (): void => this.goToGuidelines(),
            onMembers: (): void => this.goToMembers(),
            onFace: (): void => this.goToFace(),
            onSettings: (): void => this.goToSettings(),
            onBody: (): void => { this.getUIContext().getRouter().pushUrl({ url: 'pages/BodyPage' }).catch(() => {}) },
            onLeaderboard: (): void => { this.getUIContext().getRouter().pushUrl({ url: 'pages/LeaderboardPage' }).catch(() => {}) }
          })
      }
      .index(this.currentTab)
      .onChange((idx: number) => {
        this.currentTab = idx
      })
      .width('100%').layoutWeight(1)
      .indicator(false)
      .loop(false)

      // 底部导航栏（内联，图标/文字颜色直接读状态）
      Row() {
        // 首页
        Column() {
          Stack({ alignContent: Alignment.Center }) {
            Text('').width(22).height(15)
              .border({ width: 1.5, color: this.currentTab === 0 ? Theme.PRIMARY : '#9CA3AF' })
              .borderRadius(4)
            Text('').width(7).height(7)
              .border({ width: 1.5, color: this.currentTab === 0 ? Theme.PRIMARY : '#9CA3AF' })
              .borderRadius(4)
          }.width(28).height(24)
          Text(this.i18n().home).fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
            .fontColor(this.currentTab === 0 ? Theme.PRIMARY : Theme.TEXT_SYS_TERTIARY)
            .margin({ top: 2 })
        }
        .justifyContent(FlexAlign.Center).layoutWeight(1).height('100%')
        .onClick(() => {
                this.getUIContext().animateTo({ duration: 200, curve: Curve.EaseOut }, () => {
                  this.currentTab = 0
                })
              })

        // 营养
        Column() {
          Row({ space: 3 }) {
            Text('').width(4).height(10)
              .backgroundColor(this.currentTab === 1 ? Theme.PRIMARY : '#9CA3AF').borderRadius(1)
            Text('').width(4).height(16)
              .backgroundColor(this.currentTab === 1 ? Theme.PRIMARY : '#9CA3AF').borderRadius(1)
            Text('').width(4).height(13)
              .backgroundColor(this.currentTab === 1 ? Theme.PRIMARY : '#9CA3AF').borderRadius(1)
          }.width(28).height(24).justifyContent(FlexAlign.Center)
          Text(this.i18n().nutrition).fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
            .fontColor(this.currentTab === 1 ? Theme.PRIMARY : Theme.TEXT_SYS_TERTIARY)
            .margin({ top: 2 })
        }
        .justifyContent(FlexAlign.Center).layoutWeight(1).height('100%')
        .onClick(() => {
                this.getUIContext().animateTo({ duration: 200, curve: Curve.EaseOut }, () => {
                  this.currentTab = 1
                })
              })

        // 菜谱
        Column() {
          Stack({ alignContent: Alignment.Center }) {
            Text('').width(22).height(22)
              .border({ width: 1.5, color: this.currentTab === 2 ? Theme.PRIMARY : '#9CA3AF' })
              .borderRadius(11)
            Text('').width(8).height(8)
              .border({ width: 1.2, color: this.currentTab === 2 ? Theme.PRIMARY : '#9CA3AF' })
              .borderRadius(4)
          }.width(28).height(24)
          Text(this.i18n().recipes).fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
            .fontColor(this.currentTab === 2 ? Theme.PRIMARY : Theme.TEXT_SYS_TERTIARY)
            .margin({ top: 2 })
        }
        .justifyContent(FlexAlign.Center).layoutWeight(1).height('100%')
        .onClick(() => {
                this.getUIContext().animateTo({ duration: 200, curve: Curve.EaseOut }, () => {
                  this.currentTab = 2
                })
              })

        // 助手
        Column() {
          Stack({ alignContent: Alignment.Center }) {
            Text('').width(22).height(16)
              .border({ width: 1.5, color: this.currentTab === 3 ? Theme.PRIMARY : '#9CA3AF' })
              .borderRadius(5)
            Text('').width(6).height(6)
              .backgroundColor(this.currentTab === 3 ? Theme.PRIMARY : '#9CA3AF')
              .borderRadius(3)
              .margin({ left: -10, top: 8 })
          }.width(28).height(24).alignContent(Alignment.Center)
          Text(this.i18n().assistant).fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
            .fontColor(this.currentTab === 3 ? Theme.PRIMARY : Theme.TEXT_SYS_TERTIARY)
            .margin({ top: 2 })
        }
        .justifyContent(FlexAlign.Center).layoutWeight(1).height('100%')
        .onClick(() => {
                this.getUIContext().animateTo({ duration: 200, curve: Curve.EaseOut }, () => {
                  this.currentTab = 3
                })
              })

        // 我的
        Column() {
          Stack({ alignContent: Alignment.Top }) {
            Text('').width(8).height(8)
              .border({ width: 1.5, color: this.currentTab === 4 ? Theme.PRIMARY : '#9CA3AF' })
              .borderRadius(4)
              .margin({ top: 2 })
            Text('').width(18).height(11)
              .border({ width: 1.5, color: this.currentTab === 4 ? Theme.PRIMARY : '#9CA3AF' })
              .borderRadius({ topLeft: 9, topRight: 9, bottomLeft: 0, bottomRight: 0 })
              .margin({ top: 11 })
          }.width(28).height(24).alignContent(Alignment.Center)
          Text(this.i18n().me).fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
            .fontColor(this.currentTab === 4 ? Theme.PRIMARY : Theme.TEXT_SYS_TERTIARY)
            .margin({ top: 2 })
        }
        .justifyContent(FlexAlign.Center).layoutWeight(1).height('100%')
        .onClick(() => {
                this.getUIContext().animateTo({ duration: 200, curve: Curve.EaseOut }, () => {
                  this.currentTab = 4
                })
              })
      }
      .width('100%').height(64)
      .backgroundColor(Theme.GLASS_BG).backdropBlur(Theme.GLASS_BLUR).border({ width: 0.5, color: Theme.GLASS_BORDER })
      .border({ width: { top: 0.5 }, color: Theme.BORDER })
    }
    .width('100%').height('100%')
    .backgroundColor(Theme.bg(this.themeMode))
    .opacity(this.themeTick >= 0 && this.fontScale > 0 ? 1 : 1)
  }
}
