data = open(r'E:\ReqCheck\app\dist\assets\index-DJzDV8BP.js', encoding='utf-8', errors='ignore').read()
# wo alias
idx = data.find('wo=')
print('wo defs:', [data[i:i+30] for i in range(len(data)) if data.startswith('wo=', i)][:5])
# find import wo
import re
m = re.search(r'wo as \w+|,\s*wo\s*[,}]', data)
print('import', m.group() if m else None)

# index.html
import os
for root, dirs, files in os.walk(r'E:\ReqCheck\app\dist'):
    for f in files:
        if f.endswith('.html'):
            print(os.path.join(root,f))
            print(open(os.path.join(root,f), encoding='utf-8').read()[:500])
