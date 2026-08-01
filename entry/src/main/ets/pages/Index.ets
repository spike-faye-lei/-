import router from '@ohos.router';
import { cameraPicker, camera } from '@kit.CameraKit';
import { image } from '@kit.ImageKit';
import fs from '@ohos.file.fs';
import common from '@ohos.app.ability.common';
import { httpUtil } from '../utils/HttpUtil';
import { AppStorage, RecognizeResult, HealthScoreResponse } from '../utils/DataModels';
import { Theme } from '../utils/Theme';

// ============================================
// SmartKitchen 主框架 — 5 Tab 大厂架构
// Tab1 首页(拍照识别/整餐) / Tab2 营养(评分) / Tab3 菜谱 / Tab4 助手(AI) / Tab5 我的
// 视觉: Material 3 + HarmonyOS Design
// ============================================

@Entry
@Component
struct Index {
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
      let context = getContext(this) as common.UIAbilityContext
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
          AppStorage.lastRecognizeResult = resp.prediction
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

  // ===== 导航 =====
  goToNutrition() { router.pushUrl({ url: 'pages/NutritionPage' }) }
  goToRecipes() { router.pushUrl({ url: 'pages/RecipesPage' }) }
  goToGuidelines() { router.pushUrl({ url: 'pages/GuidelinesPage' }) }
  goToMembers() { router.pushUrl({ url: 'pages/MembersPage' }) }
  goToFace() { router.pushUrl({ url: 'pages/FacePage' }) }
  goToHistory() { router.pushUrl({ url: 'pages/HistoryPage' }) }
  goToChat() { router.pushUrl({ url: 'pages/ChatPage' }) }

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
    }.width(28).height(24).justifyContent(FlexAlign.Center)
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
    }.width(28).height(24)
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
        .fontSize(Theme.FONT_CAPTION)
        .fontColor(this.currentTab === index ? Theme.PRIMARY : Theme.TEXT_TERTIARY)
        .margin({ top: 2 })
    }
    .justifyContent(FlexAlign.Center)
    .width('100%').height('100%')
  }

  // ===== Tab2 营养概览 =====
  @Builder
  NutritionTab() {
    Column({ space: Theme.SPACE_MD }) {
      Text('今日营养').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT)
        .width('100%').textAlign(TextAlign.Start)

      // 健康评分卡
      if (this.healthScore && this.healthScore.score !== null) {
        Row() {
          Column() {
            Text(this.healthScore.score.toFixed(0)).fontSize(40).fontWeight(700).fontColor(Theme.PRIMARY)
            Text('健康评分').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_TERTIARY).margin({ top: 2 })
          }
          .alignItems(HorizontalAlign.Start).layoutWeight(1)

          Column() {
            Text(this.healthScore.level).fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT)
            Text(this.healthScore.message).fontSize(Theme.FONT_MICRO)
              .fontColor(Theme.TEXT_SECONDARY).margin({ top: 4 }).maxLines(2)
          }
          .alignItems(HorizontalAlign.End).layoutWeight(2)
        }
        .width('100%').padding(Theme.SPACE_LG)
        .backgroundColor(Theme.SURFACE).borderRadius(Theme.RADIUS_LG)
        .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
      }

      // 热量大卡片
      Column() {
        Text(this.todayCalories).fontSize(44).fontWeight(700).fontColor(Theme.TEXT)
        Text('今日摄入热量 (kcal)').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY)
          .margin({ top: 4 })
        Text(this.todayFoods.length > 0 ? this.todayFoods : '暂无记录，去首页拍照识别吧')
          .fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SECONDARY).margin({ top: 10 })
          .maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
      }
      .width('100%').padding(Theme.SPACE_LG)
      .backgroundColor(Theme.SURFACE).borderRadius(Theme.RADIUS_LG)
      .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })

      // 功能入口
      Row({ space: Theme.SPACE_MD }) {
        this.EntryCard('历史记录', '查看饮食历史与趋势', () => this.goToHistory())
        this.EntryCard('食材详情', '查看营养素构成', () => this.goToNutrition())
      }.width('100%')
    }
    .width('100%').height('100%').padding(Theme.SPACE_LG)
    .alignItems(HorizontalAlign.Start)
  }

  // ===== Tab3 菜谱概览 =====
  @Builder
  RecipesTab() {
    Column({ space: Theme.SPACE_MD }) {
      Text('今日推荐').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT)
        .width('100%').textAlign(TextAlign.Start)

      this.EntryCard('菜谱广场', '按早/午/晚餐分类浏览', () => this.goToRecipes())
      this.EntryCard('膳食指南', '中国居民膳食宝塔与建议', () => this.goToGuidelines())

      // 灵感占位
      Column() {
        Text('好好吃饭').fontSize(16).fontColor(Theme.TEXT_SECONDARY)
        Text('均衡饮食是健康的基础').fontSize(Theme.FONT_CAPTION)
          .fontColor(Theme.TEXT_TERTIARY).margin({ top: 6 })
      }
      .width('100%').padding(Theme.SPACE_XL)
      .backgroundColor(Theme.PRIMARY_LIGHT).borderRadius(Theme.RADIUS_LG)
    }
    .width('100%').height('100%').padding(Theme.SPACE_LG)
    .alignItems(HorizontalAlign.Start)
  }

  // ===== Tab4 助手 =====
  @Builder
  ChatTab() {
    Column({ space: Theme.SPACE_MD }) {
      Text('AI 营养师').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT)
        .width('100%').textAlign(TextAlign.Start)

      // 入口大卡片
      Column() {
        Text('问问你的营养师').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT)
        Text('基于 DeepSeek 大模型，结合你的饮食记录给出个性化建议')
          .fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SECONDARY).margin({ top: 6 }).lineHeight(20)

        Button() {
          Text('开始对话 ›').fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.SURFACE)
        }
        .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY).height(42)
        .margin({ top: Theme.SPACE_MD })
        .onClick(() => this.goToChat())
      }
      .width('100%').padding(Theme.SPACE_LG)
      .backgroundColor(Theme.SURFACE).borderRadius(Theme.RADIUS_LG)
      .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })

      // 示例问题
      Text('可以这样问').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY)
        .width('100%').textAlign(TextAlign.Start)

      ForEach(['我今天吃得健康吗？', '蛋白质摄入够不够？', '晚餐推荐吃什么？'], (q: string) => {
        Row() {
          Text(q).fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT)
          Text('›').fontSize(18).fontColor(Theme.TEXT_TERTIARY)
        }
        .width('100%').padding(Theme.SPACE_MD)
        .backgroundColor(Theme.SURFACE).borderRadius(Theme.RADIUS_MD)
        .shadow({ radius: 4, color: '#08000000', offsetY: 1 })
        .onClick(() => this.goToChat())
      })
    }
    .width('100%').height('100%').padding(Theme.SPACE_LG)
    .alignItems(HorizontalAlign.Start)
  }

  // ===== Tab5 我的（iOS 设置风格）=====
  @Builder
  MeTab() {
    Column({ space: Theme.SPACE_MD }) {
      Text('我的').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT)
        .width('100%').textAlign(TextAlign.Start)

      // 设置分组
      Column() {
        this.SettingRow('记录', '饮食记录与统计', () => this.goToHistory())
        Divider().strokeWidth(0.5).color(Theme.BORDER).margin({ left: Theme.SPACE_MD })
        this.SettingRow('膳食指南', '中国居民膳食指南', () => this.goToGuidelines())
        Divider().strokeWidth(0.5).color(Theme.BORDER).margin({ left: Theme.SPACE_MD })
        this.SettingRow('家庭成员', '管理家庭成员信息', () => this.goToMembers())
        Divider().strokeWidth(0.5).color(Theme.BORDER).margin({ left: Theme.SPACE_MD })
        this.SettingRow('人脸识别', '刷脸登录与身份确认', () => this.goToFace())
      }
      .width('100%')
      .backgroundColor(Theme.SURFACE).borderRadius(Theme.RADIUS_MD)
      .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })

      // 关于
      Column() {
        Text('SmartKitchen v1.0').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT)
        Text('基于 CLIP 多模态预训练的智能厨房助手')
          .fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY).margin({ top: 4 })
      }
      .width('100%').padding(Theme.SPACE_LG)
      .backgroundColor(Theme.SURFACE).borderRadius(Theme.RADIUS_MD)
      .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
    }
    .width('100%').height('100%').padding(Theme.SPACE_LG)
    .alignItems(HorizontalAlign.Start)
  }

  @Builder
  EntryCard(title: string, desc: string, action: () => void) {
    Column() {
      Text(title).fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT)
      Text(desc).fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY)
        .margin({ top: 4 }).maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
    }
    .alignItems(HorizontalAlign.Start).layoutWeight(1)
    .padding(Theme.SPACE_MD)
    .backgroundColor(Theme.SURFACE).borderRadius(Theme.RADIUS_MD)
    .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
    .onClick(() => action())
  }

  @Builder
  SettingRow(title: string, desc: string, action: () => void) {
    Row() {
      Column() {
        Text(title).fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.TEXT)
        Text(desc).fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_TERTIARY).margin({ top: 2 })
      }
      .alignItems(HorizontalAlign.Start).layoutWeight(1)

      Text('›').fontSize(20).fontColor(Theme.TEXT_TERTIARY)
    }
    .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: 14, bottom: 14 })
    .onClick(() => action())
  }

  // ===== 主布局 =====
  build() {
    Tabs({ barPosition: BarPosition.End }) {
      // —— Tab1 首页：拍照识别 ——
      TabContent() {
        Column() {
          Row() {
            Text('SmartKitchen').fontSize(24).fontWeight(600).fontColor(Theme.TEXT).letterSpacing(0.5)
          }
          .width('100%').padding({ top: 12, bottom: 4, left: Theme.SPACE_LG })

          Text(this.statusText)
            .fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SECONDARY)
            .width('100%').padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG, top: 6, bottom: 10 })

          // 模式切换（单食材 / 整餐）
          Row({ space: Theme.SPACE_SM }) {
            Text('单食材').fontSize(Theme.FONT_CAPTION)
              .fontColor(this.mealMode ? Theme.TEXT_TERTIARY : Theme.SURFACE)
              .padding({ left: 14, right: 14, top: 6, bottom: 6 })
              .backgroundColor(this.mealMode ? Theme.SURFACE : Theme.PRIMARY)
              .borderRadius(Theme.RADIUS_FULL)
              .onClick(() => { this.mealMode = false; this.result = null; this.mealResult = '' })
            Text('整餐分析').fontSize(Theme.FONT_CAPTION)
              .fontColor(this.mealMode ? Theme.SURFACE : Theme.TEXT_TERTIARY)
              .padding({ left: 14, right: 14, top: 6, bottom: 6 })
              .backgroundColor(this.mealMode ? Theme.PRIMARY : Theme.SURFACE)
              .borderRadius(Theme.RADIUS_FULL)
              .onClick(() => { this.mealMode = true; this.result = null; this.mealResult = '' })
          }
          .width('100%').padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG, bottom: 10 })

          // 拍照区（卡片）
          Stack() {
            if (this.photoPixelMap) {
              Image(this.photoPixelMap).width('100%').height(250).objectFit(ImageFit.Contain)
            } else {
              Column() {
                this.IconCamera(false)
                Text(this.mealMode ? '拍摄整桌餐食，自动分析多种食材' : '点击下方按钮拍照识别食材')
                  .fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_TERTIARY).margin({ top: 14 })
              }
              .justifyContent(FlexAlign.Center).width('100%').height(250)
            }
          }
          .width('100%')
          .backgroundColor(Theme.SURFACE).borderRadius(Theme.RADIUS_LG)
          .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
          .padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG })

          // 操作按钮
          Row({ space: Theme.SPACE_MD }) {
            Button() {
              Text('拍照').fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.PRIMARY)
            }
            .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY_LIGHT)
            .width(140).height(46).layoutWeight(1)
            .onClick(() => this.takePhoto())

            Button() {
              if (this.isRecognizing) {
                LoadingProgress().width(18).height(18).color(Theme.SURFACE)
              } else {
                Text('识别').fontSize(Theme.FONT_BODY).fontWeight(500).fontColor(Theme.SURFACE)
              }
            }
            .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY)
            .width(140).height(46).layoutWeight(1)
            .enabled(!!this.photoPath && !this.isRecognizing)
            .onClick(() => this.recognizePhoto())
          }
          .width('100%').padding({ top: Theme.SPACE_MD })

          // 识别结果卡片（单食材）
          if (this.result && !this.mealMode) {
            Row() {
              Column() {
                Text(this.result.name).fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT)
                Text('置信度 ' + (this.result.confidence * 100).toFixed(1) + '%')
                  .fontSize(Theme.FONT_CAPTION).fontColor(Theme.PRIMARY).margin({ top: 4 })
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)

              Button() { Text('查看营养 ›').fontSize(Theme.FONT_CAPTION).fontColor(Theme.SURFACE) }
                .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY).height(34)
                .onClick(() => this.goToNutrition())
            }
            .width('100%').padding(Theme.SPACE_MD)
            .backgroundColor(Theme.SURFACE).borderRadius(Theme.RADIUS_MD)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            .margin({ top: Theme.SPACE_MD })
          }
          // 整餐分析结果
          if (this.mealResult.length > 0 && this.mealMode) {
            Row() {
              Column() {
                Text('整餐分析').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY)
                Text(this.mealResult).fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT)
                  .margin({ top: 6 }).lineHeight(20)
              }
              .alignItems(HorizontalAlign.Start).layoutWeight(1)

              Button() { Text('问问营养师 ›').fontSize(Theme.FONT_CAPTION).fontColor(Theme.SURFACE) }
                .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY).height(34)
                .onClick(() => this.goToChat())
            }
            .width('100%').padding(Theme.SPACE_MD)
            .backgroundColor(Theme.SURFACE).borderRadius(Theme.RADIUS_MD)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            .margin({ top: Theme.SPACE_MD })
          }
        }
        .width('100%').height('100%').padding({ top: Theme.SPACE_MD })
        .alignItems(HorizontalAlign.Start)
        .backgroundColor(Theme.BG)
      }
      .tabBar(this.TabBarItem(0, '首页'))

      // —— Tab2 营养 ——
      TabContent() {
        Scroll() {
          this.NutritionTab()
        }
        .width('100%').height('100%').scrollBar(BarState.Off)
        .backgroundColor(Theme.BG)
      }
      .tabBar(this.TabBarItem(1, '营养'))

      // —— Tab3 菜谱 ——
      TabContent() {
        Scroll() {
          this.RecipesTab()
        }
        .width('100%').height('100%').scrollBar(BarState.Off)
        .backgroundColor(Theme.BG)
      }
      .tabBar(this.TabBarItem(2, '菜谱'))

      // —— Tab4 助手 ——
      TabContent() {
        Scroll() {
          this.ChatTab()
        }
        .width('100%').height('100%').scrollBar(BarState.Off)
        .backgroundColor(Theme.BG)
      }
      .tabBar(this.TabBarItem(3, '助手'))

      // —— Tab5 我的 ——
      TabContent() {
        Scroll() {
          this.MeTab()
        }
        .width('100%').height('100%').scrollBar(BarState.Off)
        .backgroundColor(Theme.BG)
      }
      .tabBar(this.TabBarItem(4, '我的'))
    }
    .width('100%').height('100%')
    .scrollable(false)
    .barHeight(64)
    .barBackgroundColor(Theme.SURFACE)
    .onChange((index: number) => {
      this.currentTab = index
    })
  }
}
