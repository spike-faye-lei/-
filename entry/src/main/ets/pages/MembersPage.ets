import { httpUtil } from '../utils/HttpUtil'
import { AppStorage as DataStore, MemberItem, I18nDict } from '../utils/DataModels'
import { zh } from '../utils/i18n/zh'
import { en } from '../utils/i18n/en'
import { Theme } from '../utils/Theme'

@Entry
@Component
struct MembersPage {
  @StorageLink('themeMode') themeMode: string = 'system'
  @StorageLink('styleMode') styleMode: string = 'glass'
  @StorageLink('fontScale') fontScale: number = 1
  @StorageLink('language') language: string = 'zh'
  // 页面每次显示时自增，强制整页重绘
  @State themeTick: number = 0
  @State members: MemberItem[] = []
  @State isLoading: boolean = true
  @State statusMsg: string = '加载中...'
  @State newName: string = ''
  @State newGoal: string = 'maintain'
  @State showAdd: boolean = false
  @State selectedMember: string = DataStore.currentMember

  aboutToAppear() {
    this.loadMembers()
  }

  i18n(): I18nDict {
    return this.language === 'zh' ? zh : en
  }

  onPageShow() {
    // 页面被压栈时收不到 AppStorage 通知，回到前台强制同步最新设置
    let mode = AppStorage.get<string>('themeMode') || 'system'
    let scale = AppStorage.get<number>('fontScale') || 1
    if (mode !== this.themeMode) this.themeMode = mode
    if (scale !== this.fontScale) this.fontScale = scale
    let style = AppStorage.get<string>('styleMode') || 'glass'
    if (style !== this.styleMode) this.styleMode = style
    this.themeTick++
  }

  async loadMembers() {
    this.isLoading = true
    try {
      let resp = await httpUtil.getMembers()
      this.members = resp.members
      this.statusMsg = resp.members.length > 0 ? '' : this.i18n().noMembers
      // 同步当前选中
      let current = this.members.find(m => m.name === this.selectedMember)
      if (!current && this.members.length > 0) {
        this.selectedMember = this.members[0].name
        DataStore.currentMember = this.selectedMember
      }
    } catch (e) {
      this.statusMsg = '加载失败: ' + JSON.stringify(e)
    }
    this.isLoading = false
  }

  async addMember() {
    let name = this.newName.trim()
    if (!name) {
      this.getUIContext().getPromptAction().showToast({ message: this.i18n().enterMemberName, duration: 2000 })
      return
    }
    try {
      await httpUtil.addMember(name, this.newGoal)
      this.getUIContext().getPromptAction().showToast({ message: this.i18n().addSuccess + ' ' + name, duration: 1500 })
      this.newName = ''
      this.showAdd = false
      await this.loadMembers()
    } catch (e) {
      this.getUIContext().getPromptAction().showToast({ message: this.i18n().addFailed, duration: 2000 })
    }
  }

  async deleteMember(item: MemberItem) {
    if (item.name === 'default') {
      this.getUIContext().getPromptAction().showToast({ message: this.i18n().defaultNotDeletable, duration: 1500 })
      return
    }
    try {
      await httpUtil.deleteMember(item.id)
      this.getUIContext().getPromptAction().showToast({ message: this.i18n().deleteSuccess + ' ' + item.name, duration: 1500 })
      if (this.selectedMember === item.name) {
        this.selectedMember = 'default'
        DataStore.currentMember = 'default'
      }
      await this.loadMembers()
    } catch (e) {
      this.getUIContext().getPromptAction().showToast({ message: this.i18n().deleteFailed, duration: 2000 })
    }
  }

  selectMember(name: string) {
    this.selectedMember = name
    DataStore.currentMember = name
    this.getUIContext().getPromptAction().showToast({ message: this.i18n().currentMember + ': ' + name, duration: 1500 })
  }

  goBack() {
    this.getUIContext().getRouter().back()
  }

  getGoalLabel(goal: string): string {
    switch (goal) {
      case 'maintain': return this.i18n().goalMaintain
      case 'lose': return this.i18n().goalLose
      case 'gain': return this.i18n().goalGain
      default: return goal
    }
  }

  getGoalColor(goal: string): string {
    switch (goal) {
      case 'maintain': return Theme.PRIMARY
      case 'lose': return Theme.WARNING
      case 'gain': return Theme.SUCCESS
      default: return Theme.TEXT_TERTIARY
    }
  }

  build() {
    Column() {
      // 大标题区
      Row() {
        Blank()

        Button() { Text('+ ' + this.i18n().addMember).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.PRIMARY).fontWeight(600) }
          .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY_LIGHT).height(34)
          .onClick(() => { this.showAdd = !this.showAdd })
      }
      .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD })

      Text(this.i18n().memberTitle).fontFamily('Inter').fontSize(Theme.FONT_TITLE).fontWeight(700).fontColor(Theme.TEXT_SYS)
        .width('100%').margin({ top: Theme.SPACE_SM })
        .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD })

      // 添加成员表单
      if (this.showAdd) {
        Column() {
          Column() {
          Text(this.i18n().addMember).fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT_SYS)
            .width('100%')

          TextInput({ placeholder: this.i18n().memberName, text: this.newName })
            .width('100%').height(44)
            .onChange((v: string) => { this.newName = v })
            .backgroundColor(Theme.BG).borderRadius(Theme.RADIUS_MD)
            .padding({ left: Theme.SPACE_MD })
            .margin({ top: Theme.SPACE_MD })

          Row() {
            ForEach(['maintain', 'lose', 'gain'], (goal: string) => {
              Button() { Text(this.getGoalLabel(goal)).fontFamily('Inter').fontSize(Theme.FONT_CAPTION) }
                .type(ButtonType.Capsule)
                .backgroundColor(this.newGoal === goal ? Theme.PRIMARY : Theme.BG)
                .fontColor(this.newGoal === goal ? '#FFFFFF' : Theme.TEXT_SYS_SECONDARY)
                .height(34).margin({ right: Theme.SPACE_SM })
                .onClick(() => { this.newGoal = goal })
            })
          }
          .width('100%').margin({ top: Theme.SPACE_MD })

          Row() {
            Button() { Text(this.i18n().cancel).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY) }
              .type(ButtonType.Capsule).backgroundColor(Theme.BG).height(38)
              .layoutWeight(1).margin({ right: Theme.SPACE_SM })
              .onClick(() => { this.showAdd = false })
            Button() { Text(this.i18n().confirmAdd).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor('#FFFFFF').fontWeight(600) }
              .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY).linearGradient({ angle: 135, colors: [['#E8967A', 0.0], ['#D97757', 1.0]] }).height(38)
              .layoutWeight(1).margin({ left: Theme.SPACE_SM })
              .onClick(() => this.addMember())
          }
          .width('100%').margin({ top: Theme.SPACE_MD })
        }
          .padding(Theme.SPACE_MD).backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER })
          .borderRadius(Theme.RADIUS_LG)
          .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
          }
          .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_MD })
      }

      // 成员列表
      if (this.isLoading) {
        Column() {
          LoadingProgress().width(32).height(32).color(Theme.PRIMARY)
          Text(this.i18n().loadingMembers).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_TERTIARY)
            .margin({ top: Theme.SPACE_MD })
        }.justifyContent(FlexAlign.Center).width('100%').layoutWeight(1)
      } else if (this.members.length > 0) {
        Text(this.i18n().selectCurrent).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_SECONDARY)
          .padding({ left: Theme.SPACE_MD, top: Theme.SPACE_MD, bottom: Theme.SPACE_XS })

        List() {
          ForEach(this.members, (item: MemberItem) => {
            ListItem() {
              Row() {
                // 选中指示
                Row()
                  .width(this.selectedMember === item.name ? 4 : 0)
                  .height(40).backgroundColor(Theme.PRIMARY).borderRadius(Theme.RADIUS_FULL)
                  .margin({ right: Theme.SPACE_MD })

                Column() {
                  Row() {
                    Text(item.name).fontFamily('Inter').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT_SYS)
                    Text(this.getGoalLabel(item.health_goal))
                      .fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor('#FFFFFF')
                      .padding({ left: Theme.SPACE_SM, right: Theme.SPACE_SM, top: Theme.SPACE_XS, bottom: Theme.SPACE_XS })
                      .backgroundColor(this.getGoalColor(item.health_goal))
                      .borderRadius(Theme.RADIUS_FULL).margin({ left: Theme.SPACE_SM })
                  }

                  if (item.created_at) {
                    Text('加入于 ' + item.created_at).fontFamily('Inter').fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_SYS_TERTIARY)
                      .margin({ top: Theme.SPACE_XS })
                  }
                }
                .alignItems(HorizontalAlign.Start).layoutWeight(1)

                Button() { Text(this.i18n().delete).fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor('#FFFFFF') }
                  .type(ButtonType.Capsule).backgroundColor(Theme.DANGER)
                  .height(30)
                  .onClick(() => this.deleteMember(item))
              }
              .padding(Theme.SPACE_MD).backgroundEffect(Theme.GLASS_EFFECT).linearGradient(Theme.GLASS_GRADIENT).border({ width: 0.5, color: Theme.GLASS_BORDER })
              .borderRadius(Theme.RADIUS_MD)
              .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
              .border({
                width: this.selectedMember === item.name ? 1.5 : 0,
                color: Theme.PRIMARY
              })
              .opacity(this.fontScale > 0 ? 1 : 1)
              .onClick(() => this.selectMember(item.name))
            }
            .margin({ top: Theme.SPACE_SM, left: Theme.SPACE_MD, right: Theme.SPACE_MD })
          })
        }
        .width('100%').layoutWeight(1).margin({ top: Theme.SPACE_SM })
      } else {
        Column() {
          Text(this.statusMsg).fontFamily('Inter').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SYS_TERTIARY)
            .width('100%').textAlign(TextAlign.Center)
        }
        .width('100%').layoutWeight(1).justifyContent(FlexAlign.Center)
      }

      // 提示
      Text(this.i18n().memberHint)
        .fontFamily('Inter').fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_SYS_TERTIARY)
        .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_MD, bottom: Theme.SPACE_MD })
        .textAlign(TextAlign.Center)
    }
    .width('100%').height('100%').linearGradient(Theme.bgGradient(this.themeMode, this.styleMode))
    .opacity(this.themeTick >= 0 && this.fontScale > 0 ? 1 : 1)
  }
}
