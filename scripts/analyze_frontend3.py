import re
data = open(r'E:\ReqCheck\app\dist\assets\index-DJzDV8BP.js', encoding='utf-8', errors='ignore').read()

# Find wo component
for pat in ['wo=Z', '__name:"Requirement', 'tree-data', 'onNodeClick', 'current-node']:
    for m in re.finditer(pat, data):
        if m.start() > 0:
            print(pat, '@', m.start())
            print(data[m.start()-80:m.start()+400])
            print('---')
            break

# full parse view template after wo
idx = data.find('"tree-data":c.value')
print('\n=== tree usage ===')
print(data[idx:idx+800])
