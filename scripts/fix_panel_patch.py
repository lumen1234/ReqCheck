path = r'E:\ReqCheck\app\dist\assets\index-DJzDV8BP.js'
data = open(path, encoding='utf-8', errors='ignore').read()

broken = 'k("div",{key:i.value.id},$p,['
# Vue3: merge key into props object - $p is {class:"max-w-3xl space-y-6"}
fixed = 'k("div",Object.assign({key:i.value.id},$p),['

if broken in data:
    data = data.replace(broken, fixed, 1)
    open(path, 'w', encoding='utf-8').write(data)
    print('Fixed panel key merge')
else:
    print('Broken pattern not found:', broken in data)
