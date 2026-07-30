import os, json
P = 'D:\\SmartKitchen\\'

def w(path, content):
    full = P + path
    os.makedirs(os.path.dirname(full), exist_ok=True)
    if os.path.exists(full): os.remove(full)
    with open(full, 'w', encoding='utf-8') as f:
        if isinstance(content, dict) or isinstance(content, list):
            json.dump(content, f, indent=2, ensure_ascii=False)
        else:
            f.write(content)
    return path.split('/')[-1]

def wets(path, content):
    full = P + path
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)
    return path.split('/')[-1]

# Config files
w('build-profile.json5', {'app':{'signingConfigs':[],'products':[{'name':'default'}]},'modules':[{'name':'entry','srcPath':'./entry','targets':[{'name':'default','applyToProducts':['default']}]}]})
w('hvigorfile.ts', 'import { appTasks } from \\'@ohos/hvigor-ohos-plugin\\';\nexport default { system: appTasks };\n')
w('oh-package.json5', {'name':'SmartKitchen','version':'1.0.0','dependencies':{}})
w('local.properties', 'sdk.dir=C:\\\\Users\\\\22504\\\\AppData\\\\Local\\\\Huawei\\\\Sdk\nnodejs.dir=\n')
w('AppScope/app.json5', {'app':{'bundleName':'com.smartkitchen.app','vendor':'smartkitchen','version':{'code':1,'name':'1.0.0'},'icon':'$media:app_icon','label':'$string:app_name'}})
w('AppScope/resources/base/element/string.json', {'string':[{'name':'app_name','value':'SmartKitchen'}]})
w('hvigor/hvigor-config.json5', {'modelVersion':'5.0.0','dependencies':{}})
w('entry/build-profile.json5', {'apiType':'stageMode','buildOption':{},'buildOptionSet':[{'name':'default','buildOption':{}}],'targets':[{'name':'default','applyToProducts':['default']}]})
w('entry/oh-package.json5', {'name':'entry','version':'1.0.0','dependencies':{}})
w('entry/hvigorfile.ts', 'import { hapTasks } from \\'@ohos/hvigor-ohos-plugin\\';\nexport default { system: hapTasks };\n')
w('entry/src/main/module.json5', {'module':{'name':'entry','type':'entry','description':'Smart Kitchen','mainElement':'EntryAbility','deviceTypes':['phone'],'deliveryWithInstall':True,'installationFree':False,'pages':['pages/Index','pages/NutritionPage','pages/HistoryPage'],'abilities':[{'name':'EntryAbility','srcEntry':'./ets/entryability/EntryAbility.ets','description':'Food Recognition','icon':'$media:icon','label':'SmartKitchen','startWindowIcon':'$media:icon','startWindowBackground':'#1a1a2e','exported':True,'skills':[{'entities':['entity.system.home'],'actions':['action.system.home']}]}],'requestPermissions':[{'name':'ohos.permission.CAMERA','reason':'Take food photos','usedScene':{'abilities':['EntryAbility'],'when':'inuse'}},{'name':'ohos.permission.INTERNET'},{'name':'ohos.permission.READ_MEDIA'}]}})
w('entry/src/main/resources/base/element/string.json', {'string':[{'name':'module_desc','value':'Smart Kitchen'}]})
w('entry/src/main/resources/en_US/element/string.json', {'string':[{'name':'module_desc','value':'Smart Kitchen'}]})
w('entry/src/main/resources/zh_CN/element/string.json', {'string':[{'name':'module_desc','value':'\\u667a\\u80fd\\u53a8\\u623f'}]})

wets('entry/src/main/ets/entryability/EntryAbility.ets', 'import UIAbility from \\'@ohos.app.ability.UIAbility\\';\nimport hilog from \\'@ohos.hilog\\';\nimport window from \\'@ohos.window\\';\n\nexport default class EntryAbility extends UIAbility {\n  onWindowStageCreate(windowStage) {\n    windowStage.loadContent(\\'pages/Index\\', (err) => {\n      if (err.code) hilog.error(0x0000, \\'SK\\', \\'Failed\\');\n    });\n  }\n}\n')

wets('entry/src/main/ets/utils/DataModels.ets', 'export interface RecognizeResult {\\n  name: string\\n  confidence: number\\n}\\n\\nexport interface NutritionInfo {\\n  name: string\\n  calories: number\\n  protein_g: number\\n  fat_g: number\\n  carbs_g: number\\n}\\n\\nexport interface FoodLogItem {\\n  id: number\\n  food_name: string\\n  calories: number\\n  created_at: string\\n}\n')

print('Project created!')
for r in ['build-profile','app.json5','module.json5','Index.ets']:
    p = P + ('entry/src/main/ets/pages/Index.ets' if r=='Index.ets' else '' if 'ets' in r else '')
    e = os.path.exists(p if r=='Index.ets' else (P+r.replace('.json5','')+'.json5'))
    print(f'  {r}: {\"[OK]\" if (r!=\"Index.ets\" or e) else \"[MISS]\"}')
