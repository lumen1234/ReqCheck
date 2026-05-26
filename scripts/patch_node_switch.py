"""Fix ParseView: content panel must update when tree node changes."""
import glob
import os
import time

dist = os.path.join(os.path.dirname(__file__), "..", "app", "dist", "assets")
files = glob.glob(os.path.join(dist, "index-*.js"))
if not files:
    raise SystemExit("No index-*.js in dist/assets")

path = files[0]
data = open(path, encoding="utf-8", errors="ignore").read()
changed = False

# 1) innerHTML in h() does not reliably patch — use ref callback + key
old_inner = (
    'h("div",{key:i.value.id,class:"prose prose-sm max-w-none",'
    "innerHTML:i.value.content_html||i.value.content||\"\"})"
)
new_inner = (
    'h("div",{key:i.value.id,class:"prose prose-sm max-w-none",'
    'ref:_=>{_&&(_.innerHTML=i.value.content_html||i.value.content||"")}})'
)
if old_inner in data:
    data = data.replace(old_inner, new_inner, 1)
    changed = True
    print("Patched content div: innerHTML -> ref callback")

# legacy without key
old_inner2 = (
    'h("div",{class:"prose prose-sm max-w-none",'
    "innerHTML:i.value.content_html||i.value.content||\"\"})"
)
if old_inner2 in data and old_inner2 not in new_inner:
    data = data.replace(old_inner2, new_inner, 1)
    changed = True
    print("Patched content div (no key variant)")

# 2) bump panel revision on each click so detail panel always re-renders
if "g=R(0),l=(u,d,v)=>" not in data:
    old_click = "l=(u,d,v)=>{i.value=u}"
    new_click = "g=R(0),l=(u,d,v)=>{i.value=u?{...u}:null,g.value++}"
    if old_click in data:
        data = data.replace(old_click, new_click, 1)
        changed = True
        print("Patched node click handler + panel revision ref")

old_panel_key = 'Object.assign({key:i.value.id},$p)'
new_panel_key = "Object.assign({key:i.value.id+\"-\"+g.value},$p)"
if old_panel_key in data and new_panel_key not in data:
    data = data.replace(old_panel_key, new_panel_key, 1)
    changed = True
    print("Patched detail panel key to include revision")

# 3) after API load, select transformed first node with content (not raw a.value[0])
old_init = "a.value&&a.value.length>0&&(i.value=a.value[0])"
new_init = (
    "a.value&&a.value.length>0&&("
    "i.value=(()=>{const q=n=>{for(const x of n||[]){if(x.content||x.content_html)return x;"
    "if(x.children){const r=q(x.children);if(r)return r}}return null};"
    "return q(f(a.value))||f(a.value)[0]})()"
    ")"
)
while old_init in data:
    data = data.replace(old_init, new_init, 1)
    changed = True
    print("Patched initial node selection (prefer first node with content)")

if changed:
    open(path, "w", encoding="utf-8").write(data)
    print("Done:", path)
else:
    print("No changes applied — patterns may already be patched or bundle changed")

# cache-bust index.html
html_path = os.path.join(os.path.dirname(__file__), "..", "app", "dist", "index.html")
html = open(html_path, encoding="utf-8").read()
v = str(int(time.time()))
import re

new_html, n = re.subn(
    r'(src="/assets/index-[^"]+\.js)(\?[^"]*)?(")',
    rf"\1?v={v}\3",
    html,
    count=1,
)
if n:
    open(html_path, "w", encoding="utf-8").write(new_html)
    print("Cache-bust index.html -> ?v=" + v)
