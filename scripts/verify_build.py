data = open(r'E:\ReqCheck\app\dist\assets\index-DwNF-GMM.js', encoding='utf-8', errors='ignore').read()
for s in ['content_html', 'display_title', 'pickFirstWithContent', 'v-html', 'UploadView",ValidateView']:
    print(s, '->', s in data or (s.replace('v-html','innerHTML') in data if s=='v-html' else False))

# check keep-alive include
idx = data.find('keep-alive')
print('keep-alive area:', data[data.find('include'):data.find('include')+80] if 'include' in data else 'n/a')
