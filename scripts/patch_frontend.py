"""Patch frontend: node content switch + copy content_html in tree transform."""
import glob
import os

dist = os.path.join(os.path.dirname(__file__), '..', 'app', 'dist', 'assets')
files = glob.glob(os.path.join(dist, 'index-*.js'))
if not files:
    print('No index-*.js found')
    exit(1)

path = files[0]
data = open(path, encoding='utf-8', errors='ignore').read()
changed = False

# 1. 切换节点时强制重绘 innerHTML（Vue 复用 DOM 导致内容不更新）
old_html = 'h("div",{class:"prose prose-sm max-w-none",innerHTML:i.value.content_html||i.value.content||""})'
new_html = 'h("div",{key:i.value.id,class:"prose prose-sm max-w-none",innerHTML:i.value.content_html||i.value.content||""})'
if old_html in data:
    data = data.replace(old_html, new_html, 1)
    changed = True
    print('Patched innerHTML key')

# 详情面板整体也加 key（合并进 props，避免 createElement 参数错误）
old_panel = 'i.value?(C(),k("div",$p,['
new_panel = 'i.value?(C(),k("div",Object.assign({key:i.value.id},$p),['
if old_panel in data:
    data = data.replace(old_panel, new_panel, 1)
    changed = True
    print('Patched detail panel key')

# 2. 树数据转换时保留 content_html 等字段
old_map = 'const w={id:v.id,label:v.label||"未命名节点",content:v.content||"",level:v.level||1,v_status:v.v_status||"",e_status:v.e_status||"",children:[]}'
new_map = (
    'const w={id:v.id,label:v.display_title||v.label||"未命名节点",'
    'content:v.content||"",content_html:v.content_html||"",number:v.number,'
    'level:v.level||1,v_status:v.v_status||"",e_status:v.e_status||"",'
    'tables:v.tables,images:v.images,children:[]}'
)
if old_map in data:
    data = data.replace(old_map, new_map, 1)
    changed = True
    print('Patched tree transform')

# 3. v-if 改为有 content 或 content_html 时显示
old_if = 'i.value.content?(C(),k("div",Lp,'
new_if = '(i.value.content||i.value.content_html)?(C(),k("div",Lp,'
if old_if in data:
    data = data.replace(old_if, new_if, 1)
    changed = True
    print('Patched content v-if')

if changed:
    open(path, 'w', encoding='utf-8').write(data)
    print('Done:', path)
else:
    print('No patterns matched - bundle may need manual check')
