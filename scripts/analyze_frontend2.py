data = open(r'E:\ReqCheck\app\dist\assets\index-DJzDV8BP.js', encoding='utf-8', errors='ignore').read()

idx = data.find('ParseView",setup')
chunk = data[idx:idx+4500]
# find render return
ridx = chunk.find('return')
print(chunk[ridx:ridx+2500])
