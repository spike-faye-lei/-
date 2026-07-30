import router from '@ohos.router'
import { cameraPicker, camera } from '@kit.CameraKit'
import { image } from '@kit.ImageKit'
import fs from '@ohos.file.fs'
import common from '@ohos.app.ability.common'
import { httpUtil } from '../utils/HttpUtil'
import { AppStorage } from '../utils/DataModels'

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
      // 顶部
      Row() {
        Button() { Text('← 返回').fontSize(15).fontColor('#2a5f8f') }
          .type(ButtonType.Capsule).backgroundColor('transparent')
          .onClick(() => this.goBack())

        Text('人脸识别').fontSize(20).fontWeight(700).fontColor('#1a1a2e')
          .layoutWeight(1).textAlign(TextAlign.Center)
      }
      .width('100%').padding({ top: 16, bottom: 8, left: 12, right: 12 })

      // 状态
      Text(this.statusText)
        .fontSize(14).fontColor('#5a6a7e').width('100%').padding({ left: 20, right: 20, bottom: 12 })

      // 预览区
      Stack() {
        if (this.photoPixelMap) {
          Image(this.photoPixelMap).width('100%').height(240).objectFit(ImageFit.Contain)
            .borderRadius(12)
        } else {
          Column() {
            Text('👤').fontSize(48).opacity(0.3)
            Text('点击拍照进行人脸识别').fontSize(14).fontColor('#b0b8c8').margin({ top: 8 })
          }
          .justifyContent(FlexAlign.Center).width('100%').height(240)
          .backgroundColor('#f4f6f9').borderRadius(12)
        }
      }
      .width('100%').padding({ left: 20, right: 20 })

      // 按钮区
      Row() {
        Button() { Text('📸 拍照').fontSize(16).fontColor('#fff').fontWeight(600) }
          .type(ButtonType.Capsule).backgroundColor('#2a5f8f').width(150).height(48)
          .onClick(() => this.takePhoto())

        Button() {
          if (this.isProcessing) {
            LoadingProgress().width(20).height(20).color('#fff')
          } else {
            Text('🔍 识别').fontSize(16).fontColor('#fff').fontWeight(600)
          }
        }
        .type(ButtonType.Capsule).backgroundColor('#2d8a4e').width(150).height(48)
        .enabled(!!this.photoPath && !this.isProcessing)
        .onClick(() => this.verifyFace())
      }
      .justifyContent(FlexAlign.SpaceEvenly).width('100%').padding({ top: 16, bottom: 12 })

      // 识别结果
      if (this.showResult) {
        Column() {
          Row() {
            Text('识别结果').fontSize(13).fontColor('#7a8a9e')
          }.width('100%')

          Row() {
            Text(this.identifiedUser).fontSize(24).fontWeight(700).fontColor('#1a1a2e')
            Text((this.confidence * 100).toFixed(1) + '%')
              .fontSize(14).fontColor('#2d8a4e').margin({ left: 8 })
          }.margin({ top: 4 })

          Row() {
            Button() { Text('📝 注册此人').fontSize(14).fontColor('#fff') }
              .type(ButtonType.Capsule).backgroundColor('#4a7cbf').height(40)
              .onClick(() => this.enrollFace(this.identifiedUser))
          }
          .margin({ top: 12 })
        }
        .width('100%').padding({ left: 20, right: 20, top: 12 })
        .backgroundColor('#f8faff').borderRadius(12).padding(16)
      }

      // 已注册用户
      if (this.enrolledUsers.length > 0) {
        Text('已注册成员').fontSize(14).fontWeight(600).fontColor('#1a1a2e')
          .width('100%').padding({ left: 20, top: 20, bottom: 8 })

        Column() {
          ForEach(this.enrolledUsers, (user: string) => {
            Row() {
              Text('👤').fontSize(20)
              Text(user).fontSize(16).fontColor('#1a1a2e').layoutWeight(1).margin({ left: 12 })
              Text('已注册').fontSize(12).fontColor('#2d8a4e')
                .padding({ left: 8, right: 8, top: 2, bottom: 2 })
                .backgroundColor('#e8f5e9').borderRadius(8)
            }
            .width('100%').padding(12).backgroundColor('#ffffff').borderRadius(8)
            .margin({ top: 4 })
          })
        }
        .width('100%').padding({ left: 20, right: 20 })
      }
    }
    .width('100%').height('100%').backgroundColor('#ffffff')
  }
}
