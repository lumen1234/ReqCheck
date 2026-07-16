import hashlib
import os
from typing import Any, Dict, List, Optional

from app.parsers.asset_store import AssetStore
from app.parsers.extractors import get_extractor
from app.parsers.preamble import strip_preamble
from app.parsers.tree_builder import build_requirement_tree
from app.parsers.content_render import enrich_tree_display
from app.parsers.models import DocumentBlock


def _file_ext(filepath: str) -> str:
    return filepath.rsplit('.', 1)[-1].lower()


def parse_document_to_tree(
    filepath: str,
    filename: str,
    doc_id: str,
    assets_base_folder: str,
    split_by: Optional[str] = None,
) -> Dict[str, Any]:
    ext = _file_ext(filepath)
    extractor_cls = get_extractor(ext)
    if not extractor_cls:
        raise ValueError(f'不支持的文件格式: .{ext}')

    asset_store = AssetStore(doc_id, assets_base_folder)
    extractor = extractor_cls()
    blocks = extractor.extract(filepath, asset_store)
    blocks = strip_preamble(blocks)

    if not any(b.type == 'heading' for b in blocks):
        tree = _build_fallback_tree(blocks, root_label=filename, doc_id=doc_id)
        return enrich_tree_display(tree, doc_id=doc_id)

    tree = build_requirement_tree(blocks, root_label=filename, doc_id=doc_id)
    # 在 enrich（会清除 [TABLE:...] 标记）之前执行内容分块
    if split_by:
        split_content_by_keyword(tree, split_by)
    return enrich_tree_display(tree, doc_id=doc_id)


def _build_fallback_tree(
    blocks: list[DocumentBlock],
    root_label: str,
    doc_id: str,
) -> Dict[str, Any]:
    """在模板无可识别标题时生成单节点树，避免整篇文档解析失败。"""
    node: Dict[str, Any] = {
        'id': 'node_inferred_1',
        'label': root_label,
        'content': None,
        'level': 1,
        'v_status': True,
        'e_status': 'pending',
        'children': [],
    }
    content_parts = []
    table_counter = 0
    image_counter = 0

    for block in blocks:
        if block.type == 'paragraph' and block.text:
            content_parts.append(block.text.strip())
        elif block.type == 'table' and block.table:
            table_counter += 1
            table = block.table.to_dict()
            table['id'] = f'tbl_{table_counter:03d}'
            node.setdefault('tables', []).append(table)
        elif block.type == 'image' and block.image:
            image_counter += 1
            image = block.image.to_dict(doc_id)
            image['id'] = image.get('id') or f'img_{image_counter:03d}'
            node.setdefault('images', []).append(image)

    content = '\n'.join(p for p in content_parts if p).strip()
    if content:
        node['content'] = content

    return {
        'id': 'root',
        'label': root_label,
        'content': None,
        'level': 0,
        'v_status': True,
        'e_status': 'pending',
        'children': [node],
    }


def split_content_by_keyword(tree: Dict[str, Any], keyword: str) -> Dict[str, Any]:
    """按关键词对每个节点的 content 进行分块。

    不修改标题结构（children / level / label），仅在每个节点上
    新增 content_blocks 字段。前端据此渲染虚拟分块节点。
    识别 [TABLE:id] 占位标记，将表格关联到对应的分块。
    """
    if not tree or not keyword or not keyword.strip():
        return tree

    kw = keyword.strip()

    def _split_node(node: Dict[str, Any]) -> None:
        content = (node.get('content') or '').strip()
        if not content:
            node['content_blocks'] = []
        else:
            node['content_blocks'] = [b for b in _split_text_by_keyword(content, kw) if b.get('label')]
            # 将表格 ID 解析为实际的表格数据
            node_tables = {t.get('id', ''): t for t in (node.get('tables') or [])}
            for block in node['content_blocks']:
                table_ids = block.pop('table_ids', [])
                resolved = []
                for tid in table_ids:
                    if tid in node_tables:
                        resolved.append(node_tables[tid])
                if resolved:
                    block['tables'] = resolved

        for child in node.get('children') or []:
            _split_node(child)

    _split_node(tree)
    return tree


def _split_text_by_keyword(text: str, kw: str) -> List[Dict[str, Any]]:
    """将文本按关键词拆分为若干块。每块以包含关键词的行开头。
    识别 [TABLE:id] 占位标记，收集表格 ID 到对应块。"""
    import re
    lines = text.split('\n')
    blocks: List[Dict[str, Any]] = []
    block_lines: List[str] = []
    block_label: Optional[str] = None
    block_table_ids: List[str] = []
    _table_marker = re.compile(r'^\[TABLE:(.+)\]$')

    def _flush() -> None:
        nonlocal block_label, block_lines, block_table_ids
        if block_label is not None:
            # 过滤掉表格占位行，不显示在 content 中
            body_lines = [l for l in block_lines if not _table_marker.match(l.strip())]
            body = '\n'.join(body_lines).strip()
            blocks.append({
                'id': f'cb_{len(blocks):03d}',
                'label': block_label[:80],
                'content': body,
                'table_ids': list(block_table_ids),
            })
        elif block_lines:
            # 没有匹配到关键词：不产生空 label 块，这些内容留在原始 content 中
            pass
        block_lines = []
        block_label = None
        block_table_ids = []

    for line in lines:
        stripped = line.strip()
        m = _table_marker.match(stripped)
        if m:
            block_table_ids.append(m.group(1))
            block_lines.append(line)
            continue
        if stripped.startswith(kw):
            _flush()
            block_label = stripped
            block_lines = []
        else:
            block_lines.append(line)

    _flush()
    return blocks


def compute_document_text_hash(filepath: str) -> str:
    """计算文档纯文本哈希，用于解析缓存。"""
    ext = _file_ext(filepath)
    text = ''

    if ext == 'docx':
        from docx import Document
        doc = Document(filepath)
        parts = []
        for para in doc.paragraphs:
            t = para.text.strip()
            if t:
                parts.append(t)
        for table in doc.tables:
            for row in table.rows:
                parts.append('\t'.join(cell.text.strip() for cell in row.cells))
        text = '\n'.join(parts)
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()

    digest = hashlib.md5()
    digest.update(text.encode('utf-8'))
    return digest.hexdigest()
