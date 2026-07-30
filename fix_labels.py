import os, json
P = 'D:\\A11451411'

# Fix module.json5 labels
pp = os.path.join(P, 'entry', 'src', 'main', 'module.json5')
with open(pp, 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('"label": "SmartKitchen"', '"label": "$string:app_name"')
c = c.replace('"startWindowBackground": "#1a1a2e"', '"startWindowBackground": "$color:start_window_background"')
with open(pp, 'w', encoding='utf-8') as f:
    f.write(c)
print('[OK] module.json5')

# Add color resource
cp = os.path.join(P, 'entry', 'src', 'main', 'resources', 'base', 'element', 'color.json')
with open(cp, 'w', encoding='utf-8') as f:
    json.dump({'color': [{'name': 'start_window_background', 'value': '#1a1a2e'}]}, f, indent=2)
print('[OK] color.json')

# Add app_name string
sp = os.path.join(P, 'entry', 'src', 'main', 'resources', 'base', 'element', 'string.json')
s = json.load(open(sp, 'r', encoding='utf-8'))
already = any(x['name'] == 'app_name' for x in s['string'])
if not already:
    s['string'].append({'name': 'app_name', 'value': 'SmartKitchen'})
    json.dump(s, open(sp, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print('[OK] string.json updated')
else:
    print('[OK] app_name already exists')

# Verify
with open(pp, 'r') as f:
    d = json.load(f)
    print('label:', d['module']['abilities'][0]['label'])
    print('bg:', d['module']['abilities'][0]['startWindowBackground'])
print('Done! Build should work now.')
