data = open(r'E:\ReqCheck\app\dist\assets\index-DJzDV8BP.js', encoding='utf-8', errors='ignore').read()
idx = data.find('__name:"RequirementTree"')
if idx < 0:
    idx = data.find('Np={')
idx = data.find('Np={')
print(data[idx:idx + 1500])
