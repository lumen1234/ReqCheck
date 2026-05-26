import re
data = open(r'E:\ReqCheck\app\dist\assets\index-DJzDV8BP.js', encoding='utf-8', errors='ignore').read()
idx = data.find('ParseView",setup')
print(data[idx:idx + 3200])
