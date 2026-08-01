import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { httpUtil } from '../utils/HttpUtil'
import { AppStorage, MemberItem } from '../utils/DataModels'
import { Theme } from '../utils/Theme'

@Entry
@Component
struct MembersPage {
  @State members: MemberItem[] = []
  @State isLoading: boolean = true
  @State statusMsg: string = '加载中...'
  @State newName: string = ''
  @State newGoal: string = 'maintain'
  @State showAdd: boolean = false
  @State selectedMember: string = AppStorage.currentMember

  aboutToAppear() {
    this.loadMembers()
  }

  async loadMembers() {
    this.isLoading = true
    try {
      let resp = await httpUtil.getMembers()
      this.members = resp.members
      this.statusMsg = resp.members.length > 0 ? '' : '暂无成员'
      // 同步当前选中
      let current = this.members.find(m => m.name === this.selectedMember)
      if (!current && this.members.length > 0) {
        this.selectedMember = this.members[0].name
        AppStorage.currentMember = this.selectedMember
      }
    } catch (e) {
      this.statusMsg = '加载失败: ' + JSON.stringify(e)
    }
    this.isLoading = false
  }

  async addMember() {
    let name = this.newName.trim()
    if (!name) {
      promptAction.showToast({ message: '请输入成员名称', duration: 2000 })
      return
    }
    try {
      await httpUtil.addMember(name, this.newGoal)
      promptAction.showToast({ message: '已添加 ' + name, duration: 1500 })
      this.newName = ''
      this.showAdd = false
      await this.loadMembers()
    } catch (e) {
      promptAction.showToast({ message: '添加失败', duration: 2000 })
    }
  }

  async deleteMember(item: MemberItem) {
    if (item.name === 'default') {
      promptAction.showToast({ message: '默认成员不可删除', duration: 1500 })
      return
    }
    try {
      await httpUtil.deleteMember(item.id)
      promptAction.showToast({ message: '已删除 ' + item.name, duration: 1500 })
      if (this.selectedMember === item.name) {
        this.selectedMember = 'default'
        AppStorage.currentMember = 'default'
      }
      await this.loadMembers()
    } catch (e) {
      promptAction.showToast({ message: '删除失败', duration: 2000 })
    }
  }

  selectMember(name: string) {
    this.selectedMember = name
    AppStorage.currentMember = name
    promptAction.showToast({ message: '当前成员: ' + name, duration: 1500 })
  }

  goBack() {
    router.back()
  }

  getGoalLabel(goal: string): string {
    switch (goal) {
      case 'maintain': return '保持体重'
      case 'lose': return '减重'
      case 'gain': return '增重'
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
        Text('← 返回').fontSize(Theme.FONT_SUB).fontColor(Theme.PRIMARY)
          .onClick(() => this.goBack())

        Blank()

        Button() { Text('+ 添加').fontSize(Theme.FONT_BODY).fontColor(Theme.PRIMARY).fontWeight(600) }
          .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY_LIGHT).height(34)
          .onClick(() => { this.showAdd = !this.showAdd })
      }
      .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD })

      Text('家庭成员').fontSize(Theme.FONT_TITLE).fontWeight(700).fontColor(Theme.TEXT)
        .width('100%').margin({ top: Theme.SPACE_SM })
        .padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD })

      // 添加成员表单
      if (this.showAdd) {
        Column() {
          Text('添加新成员').fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT)
            .width('100%')

          TextInput({ placeholder: '成员名称', text: this.newName })
            .width('100%').height(44)
            .onChange((v: string) => { this.newName = v })
            .backgroundColor(Theme.BG).borderRadius(Theme.RADIUS_MD)
            .padding({ left: Theme.SPACE_MD })
            .margin({ top: Theme.SPACE_MD })

          Row() {
            ForEach(['maintain', 'lose', 'gain'], (goal: string) => {
              Button() { Text(this.getGoalLabel(goal)).fontSize(Theme.FONT_CAPTION) }
                .type(ButtonType.Capsule)
                .backgroundColor(this.newGoal === goal ? Theme.PRIMARY : Theme.BG)
                .fontColor(this.newGoal === goal ? '#FFFFFF' : Theme.TEXT_SECONDARY)
                .height(34).margin({ right: Theme.SPACE_SM })
                .onClick(() => { this.newGoal = goal })
            })
          }
          .width('100%').margin({ top: Theme.SPACE_MD })

          Row() {
            Button() { Text('取消').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SECONDARY) }
              .type(ButtonType.Capsule).backgroundColor(Theme.BG).height(38)
              .layoutWeight(1).margin({ right: Theme.SPACE_SM })
              .onClick(() => { this.showAdd = false })
            Button() { Text('确认添加').fontSize(Theme.FONT_BODY).fontColor('#FFFFFF').fontWeight(600) }
              .type(ButtonType.Capsule).backgroundColor(Theme.PRIMARY).height(38)
              .layoutWeight(1).margin({ left: Theme.SPACE_SM })
              .onClick(() => this.addMember())
          }
          .width('100%').margin({ top: Theme.SPACE_MD })
        }
        .width('100%').padding(Theme.SPACE_MD).backgroundColor(Theme.SURFACE)
        .borderRadius(Theme.RADIUS_LG)
        .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
        .margin({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_MD })
      }

      // 成员列表
      if (this.isLoading) {
        Column() {
          LoadingProgress().width(32).height(32).color(Theme.PRIMARY)
          Text('加载成员...').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_TERTIARY)
            .margin({ top: Theme.SPACE_MD })
        }.justifyContent(FlexAlign.Center).width('100%').layoutWeight(1)
      } else if (this.members.length > 0) {
        Text('选择当前记录人').fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_SECONDARY)
          .width('100%').padding({ left: Theme.SPACE_MD, top: Theme.SPACE_MD, bottom: Theme.SPACE_XS })

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
                    Text(item.name).fontSize(Theme.FONT_SUB).fontWeight(600).fontColor(Theme.TEXT)
                    Text(this.getGoalLabel(item.health_goal))
                      .fontSize(Theme.FONT_MICRO).fontColor('#FFFFFF')
                      .padding({ left: Theme.SPACE_SM, right: Theme.SPACE_SM, top: Theme.SPACE_XS, bottom: Theme.SPACE_XS })
                      .backgroundColor(this.getGoalColor(item.health_goal))
                      .borderRadius(Theme.RADIUS_FULL).margin({ left: Theme.SPACE_SM })
                  }

                  if (item.created_at) {
                    Text('加入于 ' + item.created_at).fontSize(Theme.FONT_MICRO).fontColor(Theme.TEXT_TERTIARY)
                      .margin({ top: Theme.SPACE_XS })
                  }
                }
                .alignItems(HorizontalAlign.Start).layoutWeight(1)

                Button() { Text('删除').fontSize(Theme.FONT_CAPTION).fontColor('#FFFFFF') }
                  .type(ButtonType.Capsule).backgroundColor(Theme.DANGER)
                  .height(30)
                  .onClick(() => this.deleteMember(item))
              }
              .width('100%').padding(Theme.SPACE_MD).backgroundColor(Theme.SURFACE)
              .borderRadius(Theme.RADIUS_MD)
              .shadow({ radius: Theme.SHADOW, color: '#11000000', offsetY: 2 })
              .border({
                width: this.selectedMember === item.name ? 1.5 : 0,
                color: Theme.PRIMARY
              })
              .onClick(() => this.selectMember(item.name))
            }
            .margin({ top: Theme.SPACE_SM, left: Theme.SPACE_MD, right: Theme.SPACE_MD })
          })
        }
        .width('100%').layoutWeight(1).margin({ top: Theme.SPACE_SM })
      } else {
        Column() {
          Text(this.statusMsg).fontSize(Theme.FONT_BODY).fontColor(Theme.TEXT_TERTIARY)
            .width('100%').textAlign(TextAlign.Center)
        }
        .width('100%').layoutWeight(1).justifyContent(FlexAlign.Center)
      }

      // 提示
      Text('选择的成员将关联后续的饮食记录')
        .fontSize(Theme.FONT_CAPTION).fontColor(Theme.TEXT_TERTIARY)
        .width('100%').padding({ left: Theme.SPACE_MD, right: Theme.SPACE_MD, top: Theme.SPACE_MD, bottom: Theme.SPACE_MD })
        .textAlign(TextAlign.Center)
    }
    .width('100%').height('100%').backgroundColor(Theme.BG)
  }
}
