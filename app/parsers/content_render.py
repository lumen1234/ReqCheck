"""生成 content_html；并将 content 整理为前端可读的纯文本（含表格/图片说明）。"""
import html
import re
from typing import Any, Dict, List


def _esc(text: str) -> str:
    return html.escape(text or '')


def _strip_markdown_tables(text: str) -> str:
    """去掉曾写入 content 的 Markdown 表格块。"""
    if not text:
        return ''
    lines = text.split('\n')
    out: List[str] = []
    skip = False
    for line in lines:
        if re.match(r'^\*\*tbl_', line.strip()) or re.match(r'^\|', line.strip()):
            skip = True
            continue
        if skip and not line.strip():
            skip = False
            continue
        if skip and line.strip().startswith('|'):
            continue
        if not skip:
            out.append(line)
    return '\n'.join(out).strip()


def table_to_html(table: Dict[str, Any]) -> str:
    headers = table.get('headers') or []
    rows = table.get('rows') or []
    if not headers and not rows:
        return ''
    parts = ['<table class="req-table" border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">']
    if headers:
        parts.append('<thead><tr>')
        for h in headers:
            parts.append(f'<th style="border:1px solid #ccc;padding:6px;background:#f5f5f5">{_esc(str(h))}</th>')
        parts.append('</tr></thead>')
    if rows:
        parts.append('<tbody>')
        for row in rows:
            parts.append('<tr>')
            for cell in row:
                parts.append(f'<td style="border:1px solid #ccc;padding:6px">{_esc(str(cell))}</td>')
            parts.append('</tr>')
        parts.append('</tbody>')
    parts.append('</table>')
    return ''.join(parts)


def table_to_plain(table: Dict[str, Any]) -> str:
    headers = table.get('headers') or []
    rows = table.get('rows') or []
    if not headers and not rows:
        return ''
    lines = []
    cap = table.get('caption') or table.get('id', '')
    if cap:
        lines.append(f'【{cap}】')
    if headers:
        lines.append('\t'.join(str(h) for h in headers))
        lines.append('-' * 40)
    for row in rows:
        lines.append('\t'.join(str(c) for c in row))
    return '\n'.join(lines)


def _strip_plain_table_blocks(text: str) -> str:
    """去掉 content 中的 ASCII 表格块（【tbl_xxx】+ 制表符行），避免与 HTML 表格重复展示。"""
    if not text:
        return ''
    lines = text.split('\n')
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if re.match(r'^【tbl_', stripped):
            i += 1
            while i < len(lines):
                ln = lines[i]
                if not ln.strip():
                    i += 1
                    break
                if (
                    '\t' in ln
                    or re.match(r'^-+$', ln.strip())
                    or re.match(r'^【tbl_', ln.strip())
                ):
                    i += 1
                    continue
                break
            continue
        out.append(line)
        i += 1
    return '\n'.join(out).strip()


def _strip_image_placeholders(text: str) -> str:
    """去掉 content 中的 [图片] 占位行及 API 路径行。"""
    if not text:
        return ''
    lines = text.split('\n')
    out: List[str] = []
    for line in lines:
        s = line.strip()
        if s.startswith('[图片]'):
            continue
        if s.startswith('/api/parse/') and '/assets/' in s:
            continue
        out.append(line)
    return '\n'.join(out).strip()


def build_display_content(node: Dict[str, Any]) -> str:
    """纯文本展示：不含表格/图片占位，结构化数据见 tables / images 字段。"""
    base = _strip_image_placeholders(
        _strip_plain_table_blocks(_strip_markdown_tables((node.get('content') or '').strip()))
    )
    return base


def _image_to_html(img: Dict[str, Any]) -> str:
    path = img.get('path', '')
    if path and not path.startswith('http'):
        path = path if path.startswith('/') else f'/{path.lstrip("/")}'
    alt = _esc(img.get('caption') or img.get('alt') or '图片')
    if not path:
        return ''
    return (
        f'<figure style="margin:16px 0">'
        f'<img src="{_esc(path)}" alt="{alt}" style="max-width:100%;border:1px solid #e2e8f0"/>'
        f'<figcaption style="font-size:12px;color:#64748b">{alt}</figcaption>'
        f'</figure>'
    )


def enrich_node_display(node: Dict[str, Any], doc_id: str = '') -> Dict[str, Any]:
    html_parts: List[str] = []
    display = build_display_content(node)

    if display:
        for para in display.split('\n\n'):
            p = para.strip()
            if p:
                html_parts.append(f'<p style="margin:0 0 12px;line-height:1.6">{_esc(p).replace(chr(10), "<br/>")}</p>')

    for table in node.get('tables') or []:
        tbl_html = table_to_html(table)
        if tbl_html:
            html_parts.append(tbl_html)

    if html_parts:
        node['content_html'] = '\n'.join(html_parts)

    node['content'] = display or None

    number = node.get('number')
    label = (node.get('label') or '').strip()
    if number:
        short = label
        if label.startswith(str(number)):
            short = label[len(str(number)):].strip()
        node['display_title'] = f'{number} {short}'.strip()
        node['label'] = node['display_title']
    elif label:
        node['display_title'] = label

    for child in node.get('children') or []:
        enrich_node_display(child, doc_id)

    return node


def enrich_tree_display(tree: Dict[str, Any], doc_id: str = '') -> Dict[str, Any]:
    tree['children'] = tree.get('children') or []
    return enrich_node_display(tree, doc_id)
