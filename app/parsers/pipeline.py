import hashlib
import os
from typing import Dict, Any

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
        lenient_extract = getattr(extractor, 'extract_lenient', None)
        if callable(lenient_extract):
            blocks = lenient_extract(filepath, asset_store)
            blocks = strip_preamble(blocks)

    if not any(b.type == 'heading' for b in blocks):
        tree = _build_fallback_tree(blocks, root_label=filename, doc_id=doc_id)
        return enrich_tree_display(tree, doc_id=doc_id)

    tree = build_requirement_tree(blocks, root_label=filename, doc_id=doc_id)
    return enrich_tree_display(tree, doc_id=doc_id)


def _build_fallback_tree(
    blocks: list[DocumentBlock],
    root_label: str,
    doc_id: str,
) -> Dict[str, Any]:
    """在模板无可识别标题时生成单节点树，避免整篇文档解析失败。"""
    node: Dict[str, Any] = {
        'id': 'node_inferred_1',
        'label': '文档内容',
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
