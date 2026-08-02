import { httpUtil } from '../utils/HttpUtil';
import { Theme } from '../utils/Theme';
import webSocket from '@ohos.net.webSocket';
import { BoardSensorData, BoardStatusResponse, I18nDict } from '../utils/DataModels'
import { zh } from '../utils/i18n/zh'
import { en } from '../utils/i18n/en';

// ============================================
// 开发板状态页 — 显示 TX-SMART-R 传感器数据
// 数据流: 开发板 --MQTT--> 后端 --REST/WS--> 这里
// ============================================

interface WsBoardMessage {
  board: string
  lux: number
  temp: number
  hum: number
  weight_g: number
  received_at: string
  event: string
  cls: string
  conf: number
}

@Entry
@Component
struct BoardPage {
  @StorageLink('themeMode') themeMode: string = 'system'
  @StorageLink('styleMode') styleMode: string = 'glass'
  @StorageLink('fontScale') fontScale: number = 1
  @StorageLink('language') language: string = 'zh'
  // 页面每次显示时自增，强制整页重绘
  @State themeTick: number = 0
  @State online: boolean = false
  @State lux: string = '--'
  @State temp: string = '--'
  @State hum: string = '--'
  @State weight: string = '--'
  @State lastTime: string = '--'
  @State message: string = '正在连接开发板...'
  @State events: string[] = []
  ws: webSocket.WebSocket | null = null
  pollTimer: number = -1

  i18n(): I18nDict {
    return this.language === 'zh' ? zh : en
  }

  onPageShow() {
    // 页面被压栈时收不到 AppStorage 通知，回到前台强制同步最新设置
    let mode = AppStorage.get<string>('themeMode') || 'system'
    let scale = AppStorage.get<number>('fontScale') || 1
    if (mode !== this.themeMode) this.themeMode = mode
    if (scale !== this.fontScale) this.fontScale = scale
    this.themeTick++
  }

  aboutToAppear() {
    this.fetchStatus()
    this.connectWS()
    // 每 10 秒轮询兜底
    this.pollTimer = setInterval(() => {
      this.fetchStatus()
    }, 10000)
  }

  aboutToDisappear() {
    clearInterval(this.pollTimer)
    if (this.ws) {
      try {
        this.ws.close()
      } catch (e) {
        // 忽略
      }
      this.ws = null
    }
  }

  connectWS() {
    try {
      this.ws = webSocket.createWebSocket()
      this.ws.on('open', () => {
        this.pushEvent('WebSocket 已连接，等待开发板事件...')
      })
      this.ws.on('message', (err: Error, data: string | ArrayBuffer) => {
        if (data instanceof ArrayBuffer) return
        try {
          let msg = JSON.parse(data as string) as WsBoardMessage
          if (msg.board) {
            // 传感器数据实时刷新
            this.online = true
            this.lux = (msg.lux ? msg.lux.toFixed(0) : '--') + ' lux'
            this.temp = (msg.temp ? msg.temp.toFixed(1) : '--') + ' °C'
            this.hum = (msg.hum ? msg.hum.toFixed(0) : '--') + ' %'
            if (msg.weight_g !== undefined) {
              this.weight = msg.weight_g.toFixed(0) + ' g'
            }
            this.lastTime = msg.received_at ? msg.received_at.substring(11, 19) : '--'
            this.pushEvent('传感器上报: ' + this.lux + ' / ' + this.temp + ' / ' + this.hum + ' / ' + this.weight)
          }
          if (msg.event === 'classify') {
            const names: string[] = ['水果', '蔬菜', '蛋白质', '主食']
            let cls = names[Number(msg.cls) || 0]
            this.pushEvent('粗分类结果: ' + cls + ' (置信度 ' + (msg.conf * 100).toFixed(0) + '%)')
          }
        } catch (e) {
          // 非 JSON 消息忽略
        }
      })
      this.ws.on('close', () => {
        this.pushEvent('WebSocket 断开，使用轮询模式')
      })
      // 用后端地址推导 ws 地址
      let base = 'ws://' + (this.getBackendHost()) + '/ws/board'
      this.ws.connect(base)
    } catch (e) {
      this.pushEvent('实时连接失败，使用轮询模式')
    }
  }

  getBackendHost(): string {
    // 从后端 URL 推导主机（http://192.168.1.100:8686 → 192.168.1.100:8686）
    let url = httpUtil.getBaseUrl()
    return url.replace('http://', '').replace('https://', '')
  }

  pushEvent(text: string) {
    let time = new Date().toTimeString().substring(0, 8)
    this.events = [time + '  ' + text].concat(this.events).slice(0, 6)
  }

  async fetchStatus() {
    try {
      let resp = await httpUtil.getBoardStatus()
      if (resp.success && resp.online && resp.data) {
        this.online = true
        this.lux = resp.data.lux.toFixed(0) + ' lux'
        this.temp = resp.data.temp.toFixed(1) + ' °C'
        this.hum = resp.data.hum.toFixed(0) + ' %'
        if (resp.data.weight_g !== undefined) {
          this.weight = resp.data.weight_g.toFixed(0) + ' g'
        }
        this.lastTime = resp.data._time.substring(11, 19)
        this.message = '开发板在线'
      } else {
        this.online = false
        this.message = resp.message || '开发板离线'
      }
    } catch (e) {
      this.online = false
      this.message = '网络错误，请检查后端服务'
    }
  }

  @Builder
  SensorCard(label: string, value: string, unit: string, mode: string, scale: number, tick: number) {
    Column() {
      Text(value).fontFamily('Inter').fontSize(30).fontWeight(700).fontColor(Theme.TEXT_SYS)
      Text(label + ' ' + unit).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
        .margin({ top: 4 })
    }
    .justifyContent(FlexAlign.Center).layoutWeight(1)
    .padding(Theme.SPACE_MD)
    .backgroundColor(Theme.GLASS_BG).backdropBlur(Theme.GLASS_BLUR).border({ width: 0.5, color: Theme.GLASS_BORDER }).borderRadius(Theme.RADIUS_MD)
    .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
    .opacity(this.fontScale > 0 ? 1 : 1)
  }

  build() {
    Column() {
      // 标题
      Row() {
        Text(this.i18n().boardTitle).fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT_SYS)
        Text(this.online ? '● ' + this.i18n().online : '○ ' + this.i18n().offline)
          .fontFamily('Inter').fontSize(Theme.FONT_CAPTION)
          .fontColor(this.online ? Theme.SUCCESS : Theme.TEXT_SYS_TERTIARY)
          .padding({ left: 8, right: 8, top: 2, bottom: 2 })
          .backgroundColor(this.online ? Theme.SUCCESS_BG : Theme.BG)
          .borderRadius(Theme.RADIUS_FULL)
          .margin({ left: Theme.SPACE_SM })
      }
      .padding({ top: 16, bottom: 8, left: Theme.SPACE_LG, right: Theme.SPACE_LG })

      Text(this.message).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY)
        .padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG, bottom: 12 })

      // 传感器卡片
      Row({ space: Theme.SPACE_MD }) {
        this.SensorCard(this.i18n().light, this.lux, '', this.themeMode, this.fontScale, this.themeTick)
        this.SensorCard(this.i18n().temperature, this.temp, '', this.themeMode, this.fontScale, this.themeTick)
        this.SensorCard(this.i18n().humidity, this.hum, '', this.themeMode, this.fontScale, this.themeTick)
      }
      .padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG })

      // 称重卡片
      Row({ space: Theme.SPACE_MD }) {
        this.SensorCard(this.i18n().foodWeight, this.weight, '', this.themeMode, this.fontScale, this.themeTick)
        Column() {
          Text(this.i18n().weighFlow).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
          Text(this.i18n().weighFlowDesc).fontFamily('Inter').fontSize(Theme.FONT_MICRO)
            .fontColor(Theme.TEXT_SYS_SECONDARY).margin({ top: 6 }).lineHeight(16)
        }
        .justifyContent(FlexAlign.Center).layoutWeight(2)
        .padding(Theme.SPACE_MD)
        .backgroundColor(Theme.PRIMARY_LIGHT).borderRadius(Theme.RADIUS_MD)
      }
      .padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG, top: Theme.SPACE_MD })

      // 设备信息
      Column() {
        this.InfoRow(this.i18n().deviceModel, 'TX-SMART-R', this.themeMode, this.fontScale, this.themeTick)
        Divider().strokeWidth(0.5).color(Theme.BORDER)
        this.InfoRow(this.i18n().chip, 'RK2206', this.themeMode, this.fontScale, this.themeTick)
        Divider().strokeWidth(0.5).color(Theme.BORDER)
        this.InfoRow(this.i18n().os, 'OpenHarmony Lite', this.themeMode, this.fontScale, this.themeTick)
        Divider().strokeWidth(0.5).color(Theme.BORDER)
        this.InfoRow(this.i18n().comm, 'Wi-Fi + MQTT', this.themeMode, this.fontScale, this.themeTick)
        Divider().strokeWidth(0.5).color(Theme.BORDER)
        this.InfoRow(this.i18n().lastReport, this.lastTime, this.themeMode, this.fontScale, this.themeTick)
      }
      .padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG, top: Theme.SPACE_MD })

      // 刷新按钮
      Button() {
        Text(this.i18n().refresh).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.ON_PRIMARY)
      }
      .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY).linearGradient({ angle: 135, colors: [['#E8967A', 0.0], ['#D97757', 1.0]] }).width(140).height(42)
      .margin({ top: Theme.SPACE_LG })
      .onClick(() => this.fetchStatus())

      Blank()

      Text(this.i18n().boardAuto)
        .fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY).padding({ bottom: 20 })
    }
    .width('100%').height('100%').linearGradient(Theme.bgGradient(this.themeMode, this.styleMode))
    .opacity(this.themeTick >= 0 && this.fontScale > 0 ? 1 : 1)
    .alignItems(HorizontalAlign.Start)
  }
  // 设备信息行
  @Builder
  InfoRow(label: string, value: string, mode: string, scale: number, tick: number) {
    Row() {
      Text(label).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY)
      Blank()
      Text(value).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS)
    }
    .padding(Theme.SPACE_MD)
    .opacity(this.fontScale > 0 ? 1 : 1)
  }
}
