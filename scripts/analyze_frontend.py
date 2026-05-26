data = open(r'E:\ReqCheck\app\dist\assets\index-DJzDV8BP.js', encoding='utf-8', errors='ignore').read()

markers = [
    'ParseView",setup',
    'onNodeClick:l',
    'l=(u,d,v)=>',
    'innerHTML:i.value',
    'key:i.value.id',
    'content_html:v.content_html',
    'Object.assign({key:i.value.id},$p)',
    'i.value.content||i.value.content_html',
]

for m in markers:
    print(m, '->', m in data)

idx = data.find('ParseView",setup')
print('\n--- setup excerpt ---')
print(data[idx:idx+1200])
