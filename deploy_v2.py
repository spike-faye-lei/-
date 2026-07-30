import os, json
P = 'D:\\A11451411'

def w(relpath, content):
    full = os.path.join(P, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)

w('entry/src/main/module.json5', '{"module":{"name":"entry","type":"entry","description":"SmartKitchen","mainElement":"EntryAbility","deviceTypes":["phone"],"pages":["pages/Index","pages/NutritionPage","pages/HistoryPage"],"abilities":[{"name":"EntryAbility","srcEntry":"./ets/entryability/EntryAbility.ets","icon":"$media:icon","label":"SmartKitchen","startWindowIcon":"$media:icon","startWindowBackground":"#1a1a2e","exported":true,"skills":[{"entities":["entity.system.home"],"actions":["action.system.home"]}]}],"requestPermissions":[{"name":"ohos.permission.CAMERA","reason":"food","usedScene":{"abilities":["EntryAbility"],"when":"inuse"}},{"name":"ohos.permission.INTERNET"},{"name":"ohos.permission.READ_MEDIA"}]}')
w('entry/src/main/ets/pages/Index.ets', '@Entry\n@Component\nstruct Index {\n  @State msg: string = "SmartKitchen"\n  build() {\n    Column() {\n      Text(this.msg).fontSize(24).fontWeight(700).width("100%").textAlign(TextAlign.Center).padding(20)\n      Button("Take Photo").width(200).height(48).margin({top: 40})\n    }.width("100%").height("100%").backgroundColor("#f4f6f9")\n  }\n}')
w('entry/src/main/ets/pages/NutritionPage.ets', '@Entry\n@Component\nstruct NutritionPage { build() { Column() { Text("Nutrition").fontSize(20).padding(20) }.width("100%").height("100%") } }')
w('entry/src/main/ets/pages/HistoryPage.ets', '@Entry\n@Component\nstruct HistoryPage { build() { Column() { Text("History").fontSize(20).padding(20) }.width("100%").height("100%") } }')
w('entry/src/main/ets/utils/DataModels.ets', 'export interface Result { name: string; confidence: number }')
w('entry/src/main/ets/utils/HttpUtil.ets', 'import http from "@ohos.net.http";\nexport class HttpUtil {}\nexport const httpUtil = new HttpUtil();')

print('Deployed to', P)
for f in ['module.json5','Index.ets','NutritionPage.ets','HistoryPage.ets','DataModels.ets','HttpUtil.ets']:
    print('  ' + f)
