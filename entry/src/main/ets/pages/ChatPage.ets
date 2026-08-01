import { httpUtil } from '../utils/HttpUtil';
import { ChatResponse } from '../utils/DataModels';
import { Theme } from '../utils/Theme';

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
  @State messages: ChatMessage[] = [
    { role: 'assistant', content: '你好，我是你的 AI 营养师。告诉我你今天吃了什么，我可以帮你分析营养是否均衡，给出健康建议。' }
  ]
  @State inputText: string = ''
  @State isSending: boolean = false
  @State configured: boolean = true
  scrollController: Scroller = new Scroller()

  quickQuestions: string[] = [
    '我今天吃得健康吗？',
    '蛋白质够不够？',
    '怎么吃才能减脂？',
    '推荐一顿均衡晚餐'
  ]

  async sendMessage(text: string) {
    if (!text.trim() || this.isSending) return
    this.inputText = ''
    this.isSending = true
    this.messages.push({ role: 'user', content: text })
    this.scrollToBottom()

    try {
      let resp: ChatResponse = await httpUtil.chat(text, 'default')
      this.configured = resp.configured
      if (resp.success) {
        this.messages.push({ role: 'assistant', content: resp.reply })
      } else {
        this.messages.push({ role: 'assistant', content: resp.reply })
      }
    } catch (e) {
      this.messages.push({ role: 'assistant', content: '网络错误，请确认后端服务已启动' })
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
  Bubble(msg: ChatMessage) {
    if (msg.role === 'user') {
      // 用户消息：右对齐主色气泡
      Row() {
        Text(msg.content)
          .fontSize(Theme.FONT_BODY).fontColor(Theme.SURFACE).lineHeight(20)
          .padding({ left: 14, right: 14, top: 10, bottom: 10 })
          .backgroundColor(Theme.PRIMARY)
          .borderRadius({ topLeft: Theme.RADIUS_MD, topRight: Theme.RADIUS_MD, bottomLeft: Theme.RADIUS_MD, bottomRight: 4 })
      }
      .width('100%').justifyContent(FlexAlign.End)
      .margin({ top: 8, bottom: 8 })
    } else {
      // AI 消息：左对齐浅色气泡
      Row() {
        Text(msg.content)
          .fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT).lineHeight(20)
          .padding({ left: 14, right: 14, top: 10, bottom: 10 })
          .backgroundColor(Theme.SURFACE)
          .borderRadius({ topLeft: Theme.RADIUS_MD, topRight: Theme.RADIUS_MD, bottomLeft: 4, bottomRight: Theme.RADIUS_MD })
          .shadow({ radius: 2, color: '#08000000', offsetY: 1 })
      }
      .width('100%').justifyContent(FlexAlign.Start)
      .margin({ top: 8, bottom: 8 })
    }
  }

  build() {
    Column() {
      // 顶栏
      Row() {
        Text('AI 营养师').fontSize(Theme.FONT_HEADING).fontWeight(600).fontColor(Theme.TEXT)
        Text('DeepSeek').fontSize(Theme.FONT_MICRO).fontColor(Theme.PRIMARY)
          .padding({ left: 8, right: 8, top: 2, bottom: 2 })
          .backgroundColor(Theme.PRIMARY_LIGHT).borderRadius(Theme.RADIUS_FULL)
          .margin({ left: 8 })
      }
      .width('100%').padding({ top: 14, bottom: 8, left: Theme.SPACE_LG })

      Divider().strokeWidth(0.5).color(Theme.BORDER)

      // 快捷问题
      Scroll() {
        Row({ space: Theme.SPACE_SM }) {
          ForEach(this.quickQuestions, (q: string) => {
            Text(q).fontSize(Theme.FONT_CAPTION).fontColor(Theme.PRIMARY)
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
            this.Bubble(msg)
          })
          if (this.isSending) {
            Row() {
              LoadingProgress().width(16).height(16).color(Theme.PRIMARY)
              Text('思考中...').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY)
                .margin({ left: 8 })
            }
            .width('100%').justifyContent(FlexAlign.Start).margin({ top: 8, bottom: 8 })
          }
        }
        .width('100%').padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG, bottom: 10 })
      }
      .layoutWeight(1).width('100%').scrollBar(BarState.Off)
      .backgroundColor(Theme.BG)

      // 未配置提示
      if (!this.configured) {
        Text('提示：服务器未配置 DEEPSEEK_API_KEY，AI 暂时无法回答')
          .fontSize(Theme.FONT_MICRO).fontColor(Theme.WARNING)
          .width('100%').textAlign(TextAlign.Center).padding({ top: 6, bottom: 2 })
      }

      // 输入区
      Row({ space: Theme.SPACE_SM }) {
        TextInput({ placeholder: '问问营养师...', text: this.inputText })
          .fontSize(Theme.FONT_BODY)
          .height(42).layoutWeight(1)
          .backgroundColor(Theme.SURFACE)
          .borderRadius(Theme.RADIUS_FULL)
          .padding({ left: 16, right: 16 })
          .onChange((value: string) => { this.inputText = value })
          .onSubmit(() => this.sendMessage(this.inputText))

        Button() {
          if (this.isSending) {
            LoadingProgress().width(16).height(16).color(Theme.SURFACE)
          } else {
            Text('发送').fontSize(Theme.FONT_BODY).fontColor(Theme.SURFACE)
          }
        }
        .type(ButtonType.Circle).backgroundColor(Theme.PRIMARY).width(42).height(42)
        .enabled(!this.isSending)
        .onClick(() => this.sendMessage(this.inputText))
      }
      .width('100%').padding({ left: Theme.SPACE_LG, right: Theme.SPACE_LG, top: 8, bottom: 14 })
      .backgroundColor(Theme.SURFACE)
    }
    .width('100%').height('100%').backgroundColor(Theme.SURFACE)
  }
}
