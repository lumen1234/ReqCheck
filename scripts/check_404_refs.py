import re
data = open(r'E:\ReqCheck\app\dist\assets\index-DJzDV8BP.js', encoding='utf-8', errors='ignore').read()
# dynamic imports
for m in re.finditer(r'import\s*\(\s*["\']([^"\']+)["\']', data):
    print('dynamic import:', m.group(1))
for m in re.finditer(r'["\']/(assets|api)/[^"\']+["\']', data):
    s = m.group(0)
    if 'parse' in s or 'assets' in s:
        pass
# fetch urls
for m in re.finditer(r'["\'](/[^"\']{3,80})["\']', data):
    u = m.group(1)
    if u.startswith('/api') or u.startswith('/assets'):
        print('url:', u)
