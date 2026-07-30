import router from '@ohos.router';
import { cameraPicker, camera } from '@kit.CameraKit';
import { image } from '@kit.ImageKit';
import fs from '@ohos.file.fs';
import common from '@ohos.app.ability.common';
import { httpUtil } from '../utils/HttpUtil';
import { AppStorage, RecognizeResult } from '../utils/DataModels';

@Entry
@Component
struct Index {
  @State photoPath: string = ''
  @State isRecognizing: boolean = false
  @State result: RecognizeResult | null = null
  @State photoPixelMap: image.PixelMap | null = null
  @State statusText: string = '点击拍照识别食材'
  @State backendStatus: string = ''

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

      // 预览
      let imgSource = image.createImageSource(uri)
      let pixelMap = await imgSource.createPixelMap()
      this.photoPixelMap = pixelMap

      // 复制原图到 cacheDir 用于上传
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
      this.statusText = '拍照失败: ' + JSON.stringify(e)
    }
  }

  async recognizePhoto() {
    if (!this.photoPath) return
    this.isRecognizing = true
    this.statusText = '识别中...'
    try {
      let resp = await httpUtil.recognize(this.photoPath)
      if (resp.success) {
        this.result = resp.prediction
        AppStorage.lastRecognizeResult = resp.prediction
        this.statusText = '识别结果: ' + resp.prediction.name
      } else {
        this.statusText = '识别失败'
      }
    } catch (e) {
      this.statusText = '网络错误: ' + JSON.stringify(e)
    }
    this.isRecognizing = false
  }

  goToNutrition() {
    if (!this.result) return
    router.pushUrl({ url: 'pages/NutritionPage' })
  }

  goToRecipes() {
    router.pushUrl({ url: 'pages/RecipesPage' })
  }

  goToGuidelines() {
    router.pushUrl({ url: 'pages/GuidelinesPage' })
  }

  goToMembers() {
    router.pushUrl({ url: 'pages/MembersPage' })
  }

  goToFace() {
    router.pushUrl({ url: 'pages/FacePage' })
  }

  goToHistory() {
    router.pushUrl({ url: 'pages/HistoryPage' })
  }

  build() {
    Column() {
      // 顶部标题
      Row() {
        Text('SmartKitchen').fontSize(22).fontWeight(700).fontColor('#1a1a2e')
        Text('v1.0').fontSize(12).fontColor('#8a9aaa').margin({ left: 8 })
      }
      .width('100%').padding({ top: 16, bottom: 8, left: 20 })

      // 状态提示
      Text(this.statusText)
        .fontSize(14).fontColor('#5a6a7e').width('100%').padding({ left: 20, right: 20, bottom: 12 })

      // 图片预览区
      Stack() {
        if (this.photoPixelMap) {
          Image(this.photoPixelMap).width('100%').height(240).objectFit(ImageFit.Contain)
            .borderRadius(12)
        } else {
          Column() {
            Text('📷').fontSize(48).opacity(0.3)
            Text('点击下方按钮拍照').fontSize(14).fontColor('#b0b8c8').margin({ top: 8 })
          }
          .justifyContent(FlexAlign.Center).width('100%').height(240)
          .backgroundColor('#f4f6f9').borderRadius(12)
        }
      }
      .width('100%').padding({ left: 20, right: 20 })

      // 操作按钮
      Row() {
        Button() {
          Text('📸 拍照').fontSize(16).fontColor('#fff').fontWeight(600)
        }
        .type(ButtonType.Capsule).backgroundColor('#2a5f8f').width(150).height(48)
        .onClick(() => this.takePhoto())

        Button() {
          if (this.isRecognizing) {
            LoadingProgress().width(20).height(20).color('#fff')
          } else {
            Text('🔍 识别').fontSize(16).fontColor('#fff').fontWeight(600)
          }
        }
        .type(ButtonType.Capsule).backgroundColor('#2d8a4e').width(150).height(48)
        .enabled(!!this.photoPath && !this.isRecognizing)
        .onClick(() => this.recognizePhoto())
      }
      .justifyContent(FlexAlign.SpaceEvenly).width('100%').padding({ top: 16, bottom: 12 })

      // 识别结果
      if (this.result) {
        Column() {
          Row() {
            Text('识别结果').fontSize(13).fontColor('#7a8a9e')
          }.width('100%')
          Row() {
            Text(this.result.name).fontSize(24).fontWeight(700).fontColor('#1a1a2e')
            Text((this.result.confidence * 100).toFixed(1) + '%')
              .fontSize(14).fontColor('#2d8a4e').margin({ left: 8 })
          }.margin({ top: 4 })

          Row() {
            Button() { Text('📊 查看营养').fontSize(14).fontColor('#fff') }
              .type(ButtonType.Capsule).backgroundColor('#4a7cbf').height(40)
              .onClick(() => this.goToNutrition())
            Button() { Text('📋 历史记录').fontSize(14).fontColor('#2a3a5c') }
              .type(ButtonType.Capsule).backgroundColor('#e8edf5').height(40)
              .onClick(() => this.goToHistory())
          }
          .justifyContent(FlexAlign.SpaceEvenly).width('100%').margin({ top: 12 })
        }
        .width('100%').padding({ left: 20, right: 20, top: 12 })
        .backgroundColor('#f8faff').borderRadius(12).padding(16)
      }

      // 底部导航
      Column() {
        Row() {
          Button() { Text('🏠 首页').fontSize(12).fontColor('#2a5f8f') }
            .type(ButtonType.Capsule).backgroundColor('#e8edf5').height(36)
            .layoutWeight(1).margin(4).onClick(() => {})
          Button() { Text('📊 营养').fontSize(12).fontColor('#5a6a7e') }
            .type(ButtonType.Capsule).backgroundColor('#f0f2f5').height(36)
            .layoutWeight(1).margin(4).onClick(() => this.goToNutrition())
          Button() { Text('🍽 菜谱').fontSize(12).fontColor('#5a6a7e') }
            .type(ButtonType.Capsule).backgroundColor('#f0f2f5').height(36)
            .layoutWeight(1).margin(4).onClick(() => this.goToRecipes())
        }
        .width('100%').justifyContent(FlexAlign.SpaceEvenly)

        Row() {
          Button() { Text('📋 记录').fontSize(12).fontColor('#5a6a7e') }
            .type(ButtonType.Capsule).backgroundColor('#f0f2f5').height(36)
            .layoutWeight(1).margin(4).onClick(() => this.goToHistory())
          Button() { Text('📖 指南').fontSize(12).fontColor('#5a6a7e') }
            .type(ButtonType.Capsule).backgroundColor('#f0f2f5').height(36)
            .layoutWeight(1).margin(4).onClick(() => this.goToGuidelines())
          Button() { Text('👥 成员').fontSize(12).fontColor('#5a6a7e') }
            .type(ButtonType.Capsule).backgroundColor('#f0f2f5').height(36)
            .layoutWeight(1).margin(4).onClick(() => this.goToMembers())
        }
        .width('100%').justifyContent(FlexAlign.SpaceEvenly)

        Row() {
          Button() { Text('👤 人脸').fontSize(12).fontColor('#5a6a7e') }
            .type(ButtonType.Capsule).backgroundColor('#f0f2f5').height(36)
            .layoutWeight(1).margin(4).onClick(() => this.goToFace())
        }
        .width('100%').justifyContent(FlexAlign.SpaceEvenly)
      }
      .width('100%').padding({ top: 12, bottom: 8, left: 8, right: 8 })
      .backgroundColor('#fafbfc')
    }
    .width('100%').height('100%').backgroundColor('#ffffff')
  }
}
