import router from '@ohos.router'
import { cameraPicker, camera } from '@kit.CameraKit'
import { image } from '@kit.ImageKit'
import fs from '@ohos.file.fs'
import common from '@ohos.app.ability.common'
import { httpUtil } from '../utils/HttpUtil'
import { AppStorage } from '../utils/DataModels'
import { Theme } from '../utils/Theme'

@Entry
@Component
struct FacePage {
  @State photoPath: string = ''
  @State isProcessing: boolean = false
  @State statusText: string = '拍照进行人脸识别'
  @State identifiedUser: string = ''
  @State confidence: number = 0
  @State showResult: boolean = false
  @State photoPixelMap: image.PixelMap | null = null
  @State enrolledUsers: string[] = []

  aboutToAppear() {
    this.loadFaceStatus()
  }

  async loadFaceStatus() {
    try {
      let resp = await httpUtil.getFaceStatus()
      this.enrolledUsers = resp.enrolled_users || []
    } catch (e) {
      this.statusText = '人脸服务未启动'
    }
  }

  async takePhoto() {
    this.statusText = '拍照中...'
    try {
      let context = getContext(this) as common.UIAbilityContext
      let pickerResult = await cameraPicker.pick(
        context,
        [cameraPicker.PickerMediaType.PHOTO],
        { cameraPosition: camera.CameraPosition.CAMERA_POSITION_FRONT }
      )
      let uri = pickerResult.resultUri

      // 预览
      let imgSource = image.createImageSource(uri)
      let pixelMap = await imgSource.createPixelMap()
      this.photoPixelMap = pixelMap

      // 复制原图到 cacheDir 用于上传
      let destPath = context.cacheDir + '/face_' + Date.now() + '.jpg'
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

  async verifyFace() {
    if (!this.photoPath) return
    this.isProcessing = true
    this.statusText = '识别中...'
    this.showResult = false

    try {
      let resp = await httpUtil.verifyFace(this.photoPath)
      if (resp.success) {
        if (resp.identified) {
          this.identifiedUser = resp.username || ''
          this.confidence = resp.confidence ?? 0
          this.statusText = '识别成功: ' + this.identifiedUser
          this.showResult = true
          AppStorage.currentMember = this.identifiedUser
        } else {
          this.statusText = '未识别: ' + (resp.message || '请先注册人脸')
        }
      } else {
        this.statusText = resp.message || '识别失败'
      }
    } catch (e) {
      this.statusText = '网络错误: ' + JSON.stringify(e)
    }
    this.isProcessing = false
  }

  async enrollFace(username: string) {
    if (!this.photoPath) return
    this.isProcessing = true
    this.statusText = '注册中...'

    try {
      let resp = await httpUtil.enrollFace(username, this.photoPath)
      if (resp.success) {
        this.statusText = '注册成功: ' + username
        await this.loadFaceStatus()
      } else {
        this.statusText = resp.message || '注册失败'
      }
    } catch (e) {
      this.statusText = '注册失败: ' + JSON.stringify(e)
    }
    this.isProcessing = false
  }

  goBack() {
    router.back()
  }

  build() {
    Column() {
      // 大标题区
      Row() {
        Text('← 返回').fontSize(Theme.FONT_SUB).fontColor(Theme.PRIMARY)
          .onClick(() => this.goBack())
        Blank()
      }
      .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD })

      Text('人脸识别').fontSize(Theme.FONT_TITLE).fontWeight(700).fontColor(Theme.TEXT)
        .width('100%').margin({ top: Theme.SPACE_SM })
        .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD })

      // 状态
      Text(this.statusText)
        .fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SECONDARY)
        .width('100%').margin({ top: Theme.SPACE_MD, bottom: Theme.SPACE_MD })
        .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD })

      // 预览区
      Stack() {
        if (this.photoPixelMap) {
          Image(this.photoPixelMap).width('100%').height(240).objectFit(ImageFit.Contain)
            .borderRadius(Theme.RADIUS_LG)
        } else {
          Column() {
            SymbolGlyph($r('sys.symbol.camera')).fontSize(56).fontColor([Theme.TEXT_TERTIARY])
            Text('点击拍照进行人脸识别').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_TERTIARY)
              .margin({ top: Theme.SPACE_SM })
          }
          .justifyContent(FlexAlign.Center).width('100%').height(240)
          .backgroundColor(Theme.BG).borderRadius(Theme.RADIUS_LG)
        }
      }
      .width('100%').margin({ left: Theme.SPACE_MD, right: Theme.SPACE_MD })

      // 按钮区
      Row() {
        Button() {
          Row() {
            SymbolGlyph($r('sys.symbol.camera')).fontSize(20).fontColor([Theme.PRIMARY])
            Text('拍照').fontSize(Theme.FONT_SUB).fontColor(Theme.PRIMARY).fontWeight(600)
              .margin({ left: Theme.SPACE_XS })
          }
        }
        .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY_LIGHT).width(150).height(48)
        .onClick(() => this.takePhoto())

        Button() {
          if (this.isProcessing) {
            LoadingProgress().width(20).height(20).color(Theme.SURFACE)
          } else {
            Row() {
              SymbolGlyph($r('sys.symbol.magnifyingglass')).fontSize(20).fontColor([Theme.SURFACE])
              Text('识别').fontSize(Theme.FONT_SUB).fontColor(Theme.SURFACE).fontWeight(600)
                .margin({ left: Theme.SPACE_XS })
            }
          }
        }
        .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY).width(150).height(48)
        .enabled(!!this.photoPath && !this.isProcessing)
        .onClick(() => this.verifyFace())
      }
      .justifyContent(FlexAlign.SpaceEvenly).width('100%').padding({ top: Theme.SPACE_MD, bottom: Theme.SPACE_MD })

      // 识别结果
      if (this.showResult) {
        Column() {
          Row() {
            Text('识别结果').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY)
          }.width('100%')

          Row() {
            Text(this.identifiedUser).fontSize(Theme.FONT_HEADING).fontWeight(700).fontColor(Theme.TEXT)
            Text((this.confidence * 100).toFixed(1) + '%')
              .fontSize(Theme.FONT_SUB).fontColor(Theme.SUCCESS).margin({ left: Theme.SPACE_SM })
          }.margin({ top: Theme.SPACE_XS })

          Row() {
            Button() { Text('注册此人').fontSize(Theme.FONT_BODY).fontColor(Theme.PRIMARY) }
              .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY_LIGHT).height(40)
              .onClick(() => this.enrollFace(this.identifiedUser))
          }
          .margin({ top: Theme.SPACE_MD })
        }
        .width('100%').padding(Theme.SPACE_MD).backgroundColor(Theme.SURFACE)
        .borderRadius(Theme.RADIUS_LG)
        .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
        .margin({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_MD })
      }

      // 已注册用户
      if (this.enrolledUsers.length > 0) {
        Text('已注册成员').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT)
          .width('100%').padding({ left: Theme.SPACE_MD, top: Theme.SPACE_LG, bottom: Theme.SPACE_SM })

        Column() {
          ForEach(this.enrolledUsers, (user: string) => {
            Row() {
              Text(user.charAt(0)).fontSize(Theme.FONT_BODY).fontWeight(600).fontColor(Theme.PRIMARY)
                .width(36).height(36).textAlign(TextAlign.Center)
                .backgroundColor(Theme.PRIMARY_LIGHT).borderRadius(Theme.RADIUS_FULL)

              Text(user).fontSize(Theme.FONT_SUB).fontColor(Theme.TEXT).layoutWeight(1)
                .margin({ left: Theme.SPACE_MD })

              Text('已注册').fontSize(Theme.FONT_MICRO).fontColor(Theme.SURFACE)
                .padding({ left: Theme.SPACE_SM, right: Theme.SPACE_SM, top: Theme.SPACE_XS, bottom: Theme.SPACE_XS })
                .backgroundColor(Theme.SUCCESS).borderRadius(Theme.RADIUS_FULL)
            }
            .width('100%').padding(Theme.SPACE_MD).backgroundColor(Theme.SURFACE)
            .borderRadius(Theme.RADIUS_MD)
            .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
            .margin({ top: Theme.SPACE_XS })
          })
        }
        .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD })
      }
    }
    .width('100%').height('100%').backgroundColor(Theme.BG).padding({ top: Theme.SPACE_MD })
  }
}
