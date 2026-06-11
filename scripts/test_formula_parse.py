"""Quick check for formula extraction and HTML rendering."""
import os
import importlib.util
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_parser = _load("_parser", os.path.join(ROOT, "app/parsers/vendor/omml2latex/_parser.py"))
_render = _load("content_render", os.path.join(ROOT, "app/parsers/content_render.py"))

xml = """
<m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
  <m:sSup>
    <m:e><m:r><m:t>x</m:t></m:r></m:e>
    <m:sup><m:r><m:t>2</m:t></m:r></m:sup>
  </m:sSup>
</m:oMath>
"""
latex = _parser.convert_omml(ET.fromstring(xml))
print("OMML -> LaTeX:", latex)

html = _render.render_latex_in_html("速度 $v=at$ 与 $$E=mc^2$$")
assert "math-inline" in html and "math-block" in html, html
print("LaTeX -> HTML placeholders: OK")

node = {"content": "公式 $x^2$", "label": "test", "children": []}
_render.enrich_node_display(node)
assert "math-inline" in node.get("content_html", ""), node
print("enrich_node_display: OK")
