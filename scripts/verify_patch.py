data = open(r'E:\ReqCheck\app\dist\assets\index-DJzDV8BP.js', encoding='utf-8', errors='ignore').read()
checks = [
    'ref:_=>{_&&(_.innerHTML=i.value.content_html',
    'g=R(0),l=(u,d,v)=>',
    'key:i.value.id+"-"+g.value',
    'return q(f(a.value))',
    'innerHTML:i.value.content_html',
    'i.value=a.value[0]',
]
for c in checks:
    print(c, '->', data.count(c))

html = open(r'E:\ReqCheck\app\dist\index.html', encoding='utf-8').read()
print('index.html script:', [line for line in html.splitlines() if 'index-' in line][0])
