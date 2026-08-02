# SmartKitchen — 鸿蒙端智能厨房助手

基于 HarmonyOS NEXT（API 24）开发的智能厨房食材识别 APP，与 [SmartKitchen 后端](https://github.com/spike-faye-lei/-) 配合使用。

## 📱 功能

| 页面 | 功能 |
|---|---|
| 🏠 首页 | 拍照识别食材，底部导航入口 |
| 📊 营养 | 食物营养详情查询 |
| 🍽️ 菜谱 | 分类菜谱推荐（早餐/午餐/晚餐） |
| 📋 记录 | 饮食历史记录与统计 |
| 📖 指南 | 中国居民膳食指南 |
| 👥 成员 | 家庭成员管理（CRUD） |
| 👤 人脸 | 人脸识别注册/验证 |

## 🔧 使用

### 1. 配置后端地址

`entry/src/main/ets/utils/DataModels.ets` 中修改：

```typescript
static backendUrl: string = 'http://<你的电脑IP>:8686'
```

### 2. 编译

DevEco Studio 打开 `A11451411/`，Sync → Build → 部署到设备。

## 🙏 致谢

- [HarmonyOS](https://developer.huawei.com) — ArkTS/ArkUI 框架
- [SmartKitchen](https://github.com/spike-faye-lei/-) — 后端 AI 服务（CLIP 92.69%）
- [CountBot](https://github.com/countbot-ai/CountBot) — 人脸识别模块参考

## 📄 许可证与免责声明

- [MIT License](LICENSE)
- [免责声明](DISCLAIMER.md) — 学习用途，AI 内容仅供参考，不构成医疗建议
- [隐私政策](PRIVACY.md) — 人脸/健康/AI 数据收集与保护说明（上架用）
