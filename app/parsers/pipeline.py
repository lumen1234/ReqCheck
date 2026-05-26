import hashlib
import os
from typing import Dict, Any

from app.parsers.asset_store import AssetStore
from app.parsers.extractors import get_extractor
from app.parsers.preamble import strip_preamble
from app.parsers.tree_builder import build_requirement_tree
from app.parsers.content_render import enrich_tree_display


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
        raise ValueError(
            '未识别到符合 GB/T 8567 编号或 Markdown 标题格式的章节，'
            '请检查文档是否包含如 1、1.1、第1章 或 # 标题 等结构。'
        )

    tree = build_requirement_tree(blocks, root_label=filename, doc_id=doc_id)
    return enrich_tree_display(tree, doc_id=doc_id)


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
