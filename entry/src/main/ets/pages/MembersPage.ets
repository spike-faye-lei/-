import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { httpUtil } from '../utils/HttpUtil'
import { AppStorage, MemberItem } from '../utils/DataModels'

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
      case 'maintain': return '#2a5f8f'
      case 'lose': return '#c96f2e'
      case 'gain': return '#2d8a4e'
      default: return '#8a9aaa'
    }
  }

  build() {
    Column() {
      // 顶部
      Row() {
        Button() { Text('← 返回').fontSize(15).fontColor('#2a5f8f') }
          .type(ButtonType.Capsule).backgroundColor('transparent')
          .onClick(() => this.goBack())

        Text('家庭成员').fontSize(20).fontWeight(700).fontColor('#1a1a2e')
          .layoutWeight(1).textAlign(TextAlign.Center)

        Button() { Text('+ 添加').fontSize(14).fontColor('#2a5f8f').fontWeight(600) }
          .type(ButtonType.Capsule).backgroundColor('#e8edf5').height(34)
          .onClick(() => { this.showAdd = !this.showAdd })
      }
      .width('100%').padding({ top: 16, bottom: 8, left: 12, right: 12 })

      // 添加成员表单
      if (this.showAdd) {
        Column() {
          Text('添加新成员').fontSize(15).fontWeight(600).fontColor('#1a1a2e')
            .width('100%')

          Row() {
            TextInput({ placeholder: '成员名称', text: this.newName })
              .width('100%').height(44)
              .onChange((v) => { this.newName = v })
              .backgroundColor('#f0f2f5').borderRadius(8)
              .padding({ left: 12 })
          }
          .width('100%').margin({ top: 12 })

          Row() {
            ForEach(['maintain', 'lose', 'gain'], (goal: string) => {
              Button() { Text(this.getGoalLabel(goal)).fontSize(13) }
                .type(ButtonType.Capsule)
                .backgroundColor(this.newGoal === goal ? this.getGoalColor(goal) : '#f0f2f5')
                .fontColor(this.newGoal === goal ? '#fff' : '#8a9aaa')
                .height(34).margin({ right: 8 })
                .onClick(() => { this.newGoal = goal })
            })
          }
          .width('100%').margin({ top: 12 })

          Row() {
            Button() { Text('取消').fontSize(14).fontColor('#8a9aaa') }
              .type(ButtonType.Capsule).backgroundColor('#f0f2f5').height(38)
              .layoutWeight(1).margin({ right: 8 })
              .onClick(() => { this.showAdd = false })
            Button() { Text('确认添加').fontSize(14).fontColor('#fff').fontWeight(600) }
              .type(ButtonType.Capsule).backgroundColor('#2a5f8f').height(38)
              .layoutWeight(1).margin({ left: 8 })
              .onClick(() => this.addMember())
          }
          .width('100%').margin({ top: 12 })
        }
        .width('100%').padding(16).backgroundColor('#ffffff').borderRadius(12)
        .margin({ left: 20, right: 20, top: 12 })
      }

      // 成员列表
      if (this.isLoading) {
        Column() {
          LoadingProgress().width(32).height(32)
          Text('加载成员...').fontSize(14).fontColor('#8a9aaa').margin({ top: 12 })
        }.justifyContent(FlexAlign.Center).width('100%').layoutWeight(1)
      } else if (this.members.length > 0) {
        Text('选择当前记录人').fontSize(13).fontColor('#8a9aaa')
          .width('100%').padding({ left: 20, top: 16, bottom: 4 })

        List() {
          ForEach(this.members, (item: MemberItem) => {
            ListItem() {
              Row() {
                // 选中指示
                Row()
                  .width(this.selectedMember === item.name ? 4 : 0)
                  .height(40).backgroundColor('#2a5f8f').borderRadius(2)
                  .margin({ right: 12 })

                Column() {
                  Row() {
                    Text(item.name).fontSize(16).fontWeight(600).fontColor('#1a1a2e')
                    Text(this.getGoalLabel(item.health_goal))
                      .fontSize(11).fontColor('#fff')
                      .padding({ left: 8, right: 8, top: 2, bottom: 2 })
                      .backgroundColor(this.getGoalColor(item.health_goal))
                      .borderRadius(8).margin({ left: 8 })
                  }

                  if (item.created_at) {
                    Text('加入于 ' + item.created_at).fontSize(11).fontColor('#b0b8c8')
                      .margin({ top: 2 })
                  }
                }
                .alignItems(HorizontalAlign.Start).layoutWeight(1)

                Button() { Text('删除').fontSize(12).fontColor('#e05555') }
                  .type(ButtonType.Capsule).backgroundColor('#fef0f0')
                  .height(30)
                  .onClick(() => this.deleteMember(item))
              }
              .width('100%').padding(16).backgroundColor('#ffffff')
              .borderRadius(12).border({
                width: this.selectedMember === item.name ? 1.5 : 0,
                color: '#2a5f8f'
              })
              .onClick(() => this.selectMember(item.name))
            }
            .margin({ top: 6, left: 20, right: 20 })
          })
        }
        .width('100%').layoutWeight(1).margin({ top: 8 })
      } else {
        Text(this.statusMsg).fontSize(14).fontColor('#8a9aaa').margin({ top: 100 })
          .width('100%').textAlign(TextAlign.Center)
      }

      // 提示
      Text('选择的成员将关联后续的饮食记录')
        .fontSize(12).fontColor('#b0b8c8')
        .width('100%').padding({ left: 20, right: 20, top: 12, bottom: 16 })
        .textAlign(TextAlign.Center)
    }
    .width('100%').height('100%').backgroundColor('#f4f6f9')
  }
}
