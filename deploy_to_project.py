import os, json, shutil

PROJ = 'D:\\A11451411'

def read_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)

# 1. Update module.json5: more pages + permissions
mod_path = os.path.join(PROJ, 'entry', 'src', 'main', 'module.json5')
mod = read_json(mod_path)
mod['module']['pages'] = ['pages/Index', 'pages/NutritionPage', 'pages/HistoryPage']
mod['module']['requestPermissions'] = [
    {'name': 'ohos.permission.CAMERA', 'reason': 'Take food photos',
     'usedScene': {'abilities': ['EntryAbility'], 'when': 'inuse'}},
    {'name': 'ohos.permission.INTERNET'},
    {'name': 'ohos.permission.READ_MEDIA'}
]
write_json(mod_path, mod)
print('[OK] module.json5')

# 2. Update string.json
str_path = os.path.join(PROJ, 'entry', 'src', 'main', 'resources', 'base', 'element', 'string.json')
strings = read_json(str_path)
base_strings = {
    'take_photo': 'Take Photo',
    'recognizing': 'Recognizing...',
    'nutrition': 'Nutrition',
    'history': 'History',
    'log_food': 'Log Food',
}
for name, value in base_strings.items():
    strings['string'].append({'name': name, 'value': value})
write_json(str_path, strings)
print('[OK] string.json')

# 3. Create icons
try:
    from PIL import Image, ImageDraw
    img = Image.new('RGBA', (256, 256), (42, 95, 191, 255))
    draw = ImageDraw.Draw(img)
    draw.text((80, 105), 'SK', fill=(255, 255, 255))
    # AppScope icon
    p1 = os.path.join(PROJ, 'AppScope', 'resources', 'base', 'media', 'app_icon.png')
    os.makedirs(os.path.dirname(p1), exist_ok=True)
    img.save(p1)
    # Entry icon
    p2 = os.path.join(PROJ, 'entry', 'src', 'main', 'resources', 'base', 'media', 'icon.png')
    os.makedirs(os.path.dirname(p2), exist_ok=True)
    img.resize((128, 128)).save(p2)
    print('[OK] icons')
except ImportError:
    print('[!] PIL not available, skipping icons')

# 4. Write code files
BASE_ETS = os.path.join(PROJ, 'entry', 'src', 'main', 'ets')

write_text(os.path.join(BASE_ETS, 'pages', 'Index.ets'),
'''@Entry
@Component
struct Index {
  @State statusText: string = 'SmartKitchen - 拍照识别食材'
  build() {
    Column() {
      Text(this.statusText).fontSize(20).fontWeight(700).padding(20)
      Button('Take Photo').width(200).height(48).onClick(() => {})
    }.width('100%').height('100%')
  }
}''')

write_text(os.path.join(BASE_ETS, 'pages', 'NutritionPage.ets'),
'''@Entry
@Component
struct NutritionPage {
  build() {
    Column() {
      Text('Nutrition').fontSize(20).fontWeight(700).padding(20)
    }.width('100%').height('100%')
  }
}''')

write_text(os.path.join(BASE_ETS, 'pages', 'HistoryPage.ets'),
'''@Entry
@Component
struct HistoryPage {
  build() {
    Column() {
      Text('History').fontSize(20).fontWeight(700).padding(20)
    }.width('100%').height('100%')
  }
}''')

write_text(os.path.join(BASE_ETS, 'utils', 'DataModels.ets'),
'''export interface RecognizeResult { name: string; confidence: number }
export interface NutritionInfo { name: string; calories: number; protein_g: number; fat_g: number; carbs_g: number }
export interface FoodLogItem { id: number; food_name: string; calories: number; created_at: string }''')

write_text(os.path.join(BASE_ETS, 'utils', 'HttpUtil.ets'),
'''import http from '@ohos.net.http';
export class HttpUtil {
  private baseUrl: string = 'http://127.0.0.1:8686';
  async recognize(path: string): Promise<Object> {
    return {};
  }
}
export const httpUtil = new HttpUtil();''')

print('[OK] code files')
print('\\nAll deployed to', PROJ)
import os, json

PROJ = 'D:\\A11451411'

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)

# 1. Write module.json5 (full replace, json5 compat)
mod_path = os.path.join(PROJ, 'entry', 'src', 'main', 'module.json5')
os.makedirs(os.path.dirname(mod_path), exist_ok=True)
if os.path.exists(mod_path): os.remove(mod_path)
with open(mod_path, 'w', encoding='utf-8') as f:
    f.write('''{\n  "module": {\n    "name": "entry",\n    "type": "entry",\n    "description": "SmartKitchen",\n    "mainElement": "EntryAbility",\n    "deviceTypes": ["phone"],\n    "deliveryWithInstall": true,\n    "installationFree": false,\n    "pages": [\n      "pages/Index",\n      "pages/NutritionPage",\n      "pages/HistoryPage"\n    ],\n    "abilities": [\n      {\n        "name": "EntryAbility",\n        "srcEntry": "./ets/entryability/EntryAbility.ets",\n        "description": "SmartKitchen",\n        "icon": "$media:icon",\n        "label": "SmartKitchen",\n        "startWindowIcon": "$media:icon",\n        "startWindowBackground": "#1a1a2e",\n        "exported": true,\n        "skills": [\n          {\n            "entities": ["entity.system.home"],\n            "actions": ["action.system.home"]\n          }\n        ]\n      }\n    ],\n    "requestPermissions": [\n      {"name": "ohos.permission.CAMERA", "reason": "Take food photos",\n       "usedScene": {"abilities": ["EntryAbility"], "when": "inuse"}},\n      {"name": "ohos.permission.INTERNET"},\n      {"name": "ohos.permission.READ_MEDIA"}\n    ]\n  }\n}''')
print('[OK] module.json5')

# 2. Update string.json  
str_path = os.path.join(PROJ, 'entry', 'src', 'main', 'resources', 'base', 'element', 'string.json')
strings = [
    {'name': 'module_desc', 'value': 'Smart Kitchen'},
    {'name': 'EntryAbility_desc', 'value': 'Food Recognition'},
    {'name': 'take_photo', 'value': 'Take Photo'},
    {'name': 'recognizing', 'value': 'Recognizing...'},
    {'name': 'nutrition', 'value': 'Nutrition'},
    {'name': 'history', 'value': 'History'},
]
write_json(str_path, {'string': strings})
print('[OK] string.json')

# 3. Icons
try:
    from PIL import Image, ImageDraw
    img = Image.new('RGBA', (256, 256), (42, 95, 191, 255))
    draw = ImageDraw.Draw(img)
    draw.text((80, 105), 'SK', fill=(255, 255, 255))
    for p in [
        os.path.join(PROJ, 'AppScope', 'resources', 'base', 'media', 'app_icon.png'),
        os.path.join(PROJ, 'entry', 'src', 'main', 'resources', 'base', 'media', 'icon.png')
    ]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        img.save(p)
    print('[OK] icons')
except ImportError:
    print('[!] no PIL')

# 4. Code files
BASE = os.path.join(PROJ, 'entry', 'src', 'main', 'ets')
f = os.path.join

# Index.ets
write_text(f(BASE, 'pages', 'Index.ets'),
'@Entry\\n@Component\\nstruct Index {\\n  @State msg: string = "SmartKitchen"\\n  build() {\\n    Column() {\\n      Text(this.msg).fontSize(20).padding(20)\\n      Button("Take Photo").width(200).onClick(() => {})\\n    }.width("100%").height("100%")\\n  }\\n}')

write_text(f(BASE, 'pages', 'NutritionPage.ets'), '@Entry\\n@Component\\nstruct NutritionPage { build() { Column() { Text("Nutrition").fontSize(20) }.width("100%") } }')
write_text(f(BASE, 'pages', 'HistoryPage.ets'), '@Entry\\n@Component\\nstruct HistoryPage { build() { Column() { Text("History").fontSize(20) }.width("100%") } }')
write_text(f(BASE, 'utils', 'DataModels.ets'), 'export interface RecognizeResult { name: string; confidence: number }\\nexport interface NutritionInfo { name: string; calories: number }')
write_text(f(BASE, 'utils', 'HttpUtil.ets'), 'import http from \\'@ohos.net.http\\';\\nexport class HttpUtil {}\\nexport const httpUtil = new HttpUtil();')

print('[OK] code files')
print('\\nDone! Project at', PROJ)
