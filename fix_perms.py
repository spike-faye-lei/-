import json
m = json.load(open(r'D:\A11451411\entry\src\main\module.json5'))
for p in m['module']['requestPermissions']:
    if 'reason' not in p:
        p['reason'] = '$string:camera_reason'
    if 'usedScene' not in p:
        p['usedScene'] = {'abilities': ['EntryAbility'], 'when': 'inuse'}
json.dump(m, open(r'D:\A11451411\entry\src\main\module.json5', 'w'), indent=2, ensure_ascii=False)
print('Fixed all permissions')
for p in m['module']['requestPermissions']:
    print(' ', p['name'], '- ok')
