from typing import Any, Dict, List, Optional

from app.parsers.heading_detector import (
    is_toc_line,
    level_from_number,
    normalize_heading_label,
    number_to_node_id,
    split_heading_label,
)
from app.parsers.models import DocumentBlock


def _empty_children() -> List[Dict[str, Any]]:
    return []


def _is_toc_label(label: str) -> bool:
    label = label or ''
    return is_toc_line(label) or '\t' in label or label.strip().startswith('.')


def _finalize_node(node: Dict[str, Any]) -> Dict[str, Any]:
    children = node.get('children') or []
    if children:
        node['children'] = [_finalize_node(c) for c in children]
        if not (node.get('content') or '').strip():
            node['content'] = None
    else:
        node['children'] = []
        content = (node.get('content') or '').strip()
        if not content:
            label = (node.get('label') or '').strip()
            short_label, body = split_heading_label(label)
            if body:
                node['label'] = short_label or node.get('number') or label
                node['content'] = body
            else:
                node['content'] = None
            if not (node.get('label') or '').strip() and node.get('number'):
                node['label'] = str(node['number'])
        else:
            node['content'] = content
    node['label'] = normalize_heading_label(node.get('label') or '')
    if not node.get('tables'):
        node.pop('tables', None)
    if not node.get('images'):
        node.pop('images', None)
    return node


def _rebuild_stack(root: Dict[str, Any], target: Dict[str, Any]) -> List[Dict[str, Any]]:
    """重建栈，使后续正文写入指定节点。"""
    path: List[Dict[str, Any]] = []

    def find_path(node: Dict[str, Any]) -> bool:
        path.append(node)
        if node is target:
            return True
        for child in node.get('children') or []:
            if find_path(child):
                return True
        path.pop()
        return False

    if find_path(root):
        return path
    return [root]


def build_requirement_tree(
    blocks: List[DocumentBlock],
    root_label: str,
    doc_id: str,
) -> Dict[str, Any]:
    root: Dict[str, Any] = {
        'id': 'root',
        'label': root_label,
        'content': None,
        'level': 0,
        'v_status': True,
        'e_status': 'pending',
        'children': _empty_children(),
    }

    stack: List[Dict[str, Any]] = [root]
    number_index: Dict[str, Dict[str, Any]] = {}
    content_parts: List[str] = []
    table_counter = 0
    image_counter = 0
    inferred_counter = 0

    def flush_content(target: Dict[str, Any]) -> None:
        nonlocal content_parts
        if content_parts:
            existing = target.get('content') or ''
            merged = '\n'.join(content_parts).strip()
            target['content'] = (existing + '\n' + merged).strip() if existing else merged
            content_parts = []

    def append_table(target: Dict[str, Any], table_data) -> None:
        nonlocal table_counter
        table_counter += 1
        entry = table_data.to_dict()
        entry['id'] = f'tbl_{table_counter:03d}'
        target.setdefault('tables', []).append(entry)

    def append_image(target: Dict[str, Any], image_data) -> None:
        nonlocal image_counter
        image_counter += 1
        entry = image_data.to_dict(doc_id)
        target.setdefault('images', []).append(entry)

    for block in blocks:
        if block.type == 'heading':
            flush_content(stack[-1])

            number = block.number
            label = normalize_heading_label(block.label or block.text or '')
            # 优先使用提取器已确定的层级（来自 Word 样式/大纲级别/编号缩进），
            # 仅在没有时才从数字文本推算，避免正文中以数字开头的内容被误判层级
            if block.level:
                level = block.level
            elif number:
                level = level_from_number(number)
            else:
                level = 1

            if _is_toc_label(label) or (block.text and is_toc_line(block.text)):
                continue

            if block.inline_content:
                content_parts.append(block.inline_content)

            if number and number in number_index:
                existing = number_index[number]
                if _is_toc_label(existing.get('label', '')) and label:
                    existing['label'] = label
                stack = _rebuild_stack(root, existing)
                continue

            if number:
                node_id = number_to_node_id(number)
            else:
                inferred_counter += 1
                node_id = f'node_inferred_{inferred_counter}'
            node: Dict[str, Any] = {
                'id': node_id,
                'label': label,
                'content': None,
                'level': level,
                'v_status': True,
                'e_status': 'pending',
                'children': _empty_children(),
            }
            if number:
                node['number'] = number
                number_index[number] = node

            while len(stack) > 1 and stack[-1].get('level', 0) >= level:
                stack.pop()

            stack[-1]['children'].append(node)
            stack.append(node)

        elif block.type == 'paragraph':
            if block.text and not is_toc_line(block.text):
                content_parts.append(block.text)

        elif block.type == 'table':
            flush_content(stack[-1])
            if block.table:
                append_table(stack[-1], block.table)
                # 在正文中插入占位标记，供后续按关键词分块时关联表格
                content_parts.append(f'[TABLE:tbl_{table_counter:03d}]')

        elif block.type == 'image':
            flush_content(stack[-1])
            if block.image:
                append_image(stack[-1], block.image)

    flush_content(stack[-1])
    return _finalize_node(root)
