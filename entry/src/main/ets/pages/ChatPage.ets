import { httpUtil } from '../utils/HttpUtil';
import { ChatResponse, I18nDict } from '../utils/DataModels';
import { zh } from '../utils/i18n/zh';
import { en } from '../utils/i18n/en';
import { Theme } from '../utils/Theme';
import { LocalData } from '../utils/LocalData';

// ============================================
// AI 营养师对话页
// ============================================

interface ChatMessage {
  role: string   // 'user' | 'assistant'
  content: string
}

@Entry
@Component
struct ChatPage {
  @StorageLink('themeMode') themeMode: string = 'system'
  @StorageLink('styleMode') styleMode: string = 'glass'
  @StorageLink('fontScale') fontScale: number = 1
  @StorageLink('language') language: string = 'zh'
  // 页面每次显示时自增，强制整页重绘
  @State themeTick: number = 0
  @State messages: ChatMessage[] = [
    { role: 'assistant', content: this.i18n().welcomeMsg }
  ]
  @State inputText: string = ''
  @State isSending: boolean = false
  @State configured: boolean = true
  scrollController: Scroller = new Scroller()

  i18n(): I18nDict {
    return this.language === 'zh' ? zh : en
  }

  onPageShow() {
    // 页面被压栈时收不到 AppStorage 通知，回到前台强制同步最新设置
    let mode = AppStorage.get<string>('themeMode') || 'system'
    let scale = AppStorage.get<number>('fontScale') || 1
    let lang = AppStorage.get<string>('language') || 'zh'
    if (mode !== this.themeMode) this.themeMode = mode
    if (scale !== this.fontScale) this.fontScale = scale
    if (lang !== this.language) this.language = lang
    let style = AppStorage.get<string>('styleMode') || 'glass'
    if (style !== this.styleMode) this.styleMode = style
    this.themeTick++
  }

  quickQuestions(): string[] {
    return [this.i18n().q1, this.i18n().q2, this.i18n().loseWeight, this.i18n().dinnerIdea]
  }

  async sendMessage(text: string) {
    if (!text.trim() || this.isSending) return
    this.inputText = ''
    this.isSending = true
    this.messages.push({ role: 'user', content: text })
    this.scrollToBottom()

    try {
      let resp: ChatResponse = await httpUtil.chat(text, 'default')
      this.configured = resp.configured
      this.messages.push({ role: 'assistant', content: resp.reply })
    } catch (e) {
      // 后端未启动：使用离线营养知识库兜底
      this.messages.push({ role: 'assistant', content: LocalData.ask(text) })
    }
    this.isSending = false
    this.scrollToBottom()
  }

  scrollToBottom() {
    setTimeout(() => {
      this.scrollController.scrollEdge(Edge.Bottom)
    }, 100)
  }

  @Builder
  Bubble(msg: ChatMessage, mode: string, scale: number, tick: number) {
    if (msg.role === 'user') {
      // 用户消息：右对齐主色气泡
      Row() {
        Text(msg.content)
          .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.ON_PRIMARY).lineHeight(20)
          .padding({ left: 14, right: 14, top: 10, bottom: 10 })
          .backgroundColor(Theme.PRIMARY)
          .borderRadius({ topLeft: Theme.RADIUS_MD, topRight: Theme.RADIUS_MD, bottomLeft: Theme.RADIUS_MD, bottomRight: 4 })
      }
      .width('100%').justifyContent(FlexAlign.End)
      .opacity(this.fontScale > 0 ? 1 : 1)
      .margin({ top: 8, bottom: 8 })
    } else {
      // AI 消息：左对齐浅色气泡
      Row() {
        Text(msg.content)
          .fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS).lineHeight(20)
          .padding({ left: 14, right: 14, top: 10, bottom: 10 })
          .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER })
          .borderRadius({ topLeft: Theme.RADIUS_MD, topRight: Theme.RADIUS_MD, bottomLeft: 4, bottomRight: Theme.RADIUS_MD })
          .shadow({ radius: 2, color: '#08000000', offsetY: 1 })
      }
      .width('100%').justifyContent(FlexAlign.Start)
      .opacity(this.fontScale > 0 ? 1 : 1)
      .margin({ top: 8, bottom: 8 })
    }
  }

  build() {
    Column() {
      // 顶栏
      Row() {
        Text(this.i18n().aiNutritionist).fontFamily('Inter').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT_SYS)
        Text('DeepSeek').fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.PRIMARY)
          .padding({ left: 8, right: 8, top: 2, bottom: 2 })
          .backgroundColor(Theme.PRIMARY_LIGHT).borderRadius(Theme.RADIUS_FULL)
          .margin({ left: 8 })
      }
      .padding({ top: 14, bottom: 8, left: Theme.SPACE_LG, right: Theme.SPACE_LG })

      Divider().strokeWidth(0.5).color(Theme.BORDER)

      // 快捷问题
      Scroll() {
        Row({ space: Theme.SPACE_SM }) {
          ForEach(this.quickQuestions(), (q: string) => {
            Text(q).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.PRIMARY)
              .padding({ left: 12, right: 12, top: 6, bottom: 6 })
              .backgroundColor(Theme.PRIMARY_LIGHT).borderRadius(Theme.RADIUS_FULL)
              .onClick(() => this.sendMessage(q))
          })
        }
        .padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG, top: 10, bottom: 4 })
      }
      .scrollable(ScrollDirection.Horizontal).scrollBar(BarState.Off)
      .width('100%').height(44)

      // 消息列表
      Scroll(this.scrollController) {
        Column() {
          ForEach(this.messages, (msg: ChatMessage, idx: number) => {
            this.Bubble(msg, this.themeMode, this.fontScale, this.themeTick)
          })
          if (this.isSending) {
            Row() {
              LoadingProgress().width(16).height(16).color(Theme.PRIMARY)
              Text(this.i18n().thinking).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
                .margin({ left: 8 })
            }
            .width('100%').justifyContent(FlexAlign.Start).margin({ top: 8, bottom: 8 })
          }
        }
        .padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG, bottom: 10 })
      }
      .layoutWeight(1).width('100%').scrollBar(BarState.Off)
      .backgroundColor(Theme.BG)

      // 未配置提示
      if (!this.configured) {
        Text(this.i18n().noKeyHint)
          .fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.WARNING)
          .width('100%').textAlign(TextAlign.Center).padding({ top: 6, bottom: 2 })
      }

      // 输入区
      Row({ space: Theme.SPACE_SM }) {
        TextInput({ placeholder: this.i18n().chatPlaceholder, text: this.inputText })
          .fontFamily('Inter').fontSize(Theme.FONT_BODY)
          .height(42).layoutWeight(1)
          .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER })
          .borderRadius(Theme.RADIUS_FULL)
          .padding({ left: 16, right: 16 })
          .onChange((value: string) => { this.inputText = value })
          .onSubmit(() => this.sendMessage(this.inputText))

        Button() {
          if (this.isSending) {
            LoadingProgress().width(16).height(16).color(Theme.ON_PRIMARY)
          } else {
            Text(this.i18n().send).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.ON_PRIMARY)
          }
        }
        .type(ButtonType.Circle).backgroundColor(Theme.PRIMARY).linearGradient({ angle: 135, colors: [['#E8967A', 0.0], ['#D97757', 1.0]] }).width(42).height(42)
        .enabled(!this.isSending)
        .onClick(() => this.sendMessage(this.inputText))
      }
      .padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG, top: 8, bottom: 14 })
      .backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER })
    }
    .width('100%').height('100%').linearGradient(Theme.bgGradient(this.themeMode, this.styleMode))
    .opacity(this.themeTick >= 0 && this.fontScale > 0 ? 1 : 1)
  }
}
