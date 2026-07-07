import os
import re
from typing import List, Optional, Tuple

from markdown_it import MarkdownIt
from markdown_it.token import Token

from app.parsers.asset_store import AssetStore
from app.parsers.block_utils import make_heading_block
from app.parsers.heading_detector import is_toc_line, parse_heading_line
from app.parsers.models import DocumentBlock, TableData
from app.parsers.extractors.txt_extractor import (
    MD_IMAGE_RE,
    _collect_md_table,
    _parse_md_table_lines,
)

MD_IMAGE_INLINE_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')


class MdExtractor:
    def __init__(self):
        self.md = MarkdownIt('commonmark').enable(['table'])

    def extract(self, filepath: str, asset_store: AssetStore) -> List[DocumentBlock]:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 先处理未在标准 token 中稳定出现的 GFM 表格（按行兜底）
        if '|' in content and '\n|' in content:
            return self._extract_hybrid(filepath, content, asset_store)

        tokens = self.md.parse(content)
        return self._tokens_to_blocks(tokens, filepath, asset_store)

    def _extract_hybrid(self, filepath: str, content: str, asset_store: AssetStore) -> List[DocumentBlock]:
        """Markdown 源码行级解析，兼容表格与图片。"""
        lines = content.splitlines()
        blocks: List[DocumentBlock] = []
        i = 0
        while i < len(lines):
            raw = lines[i]
            line = raw.strip()
            if not line:
                i += 1
                continue

            if is_toc_line(line):
                i += 1
                continue

            if line.startswith('#'):
                from app.parsers.heading_detector import parse_md_atx_heading, label_looks_like_requirement_content
                parsed = parse_md_atx_heading(line)
                if parsed:
                    number, label, level = parsed
                    blocks.append(make_heading_block(number, label, level, text=line))
                    i += 1
                    continue

            numbered = parse_heading_line(line.lstrip('#').strip())
            if numbered:
                number, label, level = numbered
                if not label_looks_like_requirement_content(label):
                    blocks.append(make_heading_block(number, label, level, text=line))
                    i += 1
                    continue
                # 数字模式但内容像需求正文 → 降级为普通段落

            if line.startswith('|') and i + 1 < len(lines):
                table_lines, next_i = _collect_md_table(lines, i)
                if table_lines:
                    table = _parse_md_table_lines(table_lines)
                    if table:
                        blocks.append(DocumentBlock(type='table', table=table))
                        i = next_i
                        continue

            for alt, src in MD_IMAGE_INLINE_RE.findall(line):
                image = asset_store.resolve_md_image(src, filepath)
                if image:
                    image.alt = alt or image.alt
                    blocks.append(DocumentBlock(type='image', image=image))

            text_only = MD_IMAGE_INLINE_RE.sub('', line).strip()
            if text_only:
                blocks.append(DocumentBlock(type='paragraph', text=text_only))
            i += 1

        return blocks

    def _tokens_to_blocks(
        self,
        tokens: List[Token],
        filepath: str,
        asset_store: AssetStore,
    ) -> List[DocumentBlock]:
        blocks: List[DocumentBlock] = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]

            if tok.type == 'heading_open':
                level = int(tok.tag[1])
                inline = tokens[i + 1]
                title = inline.content if inline.type == 'inline' else ''
                numbered = parse_heading_line(title)
                if numbered:
                    number, label, num_level = numbered
                    blocks.append(make_heading_block(number, label, num_level, text=title))
                else:
                    blocks.append(make_heading_block(None, title, level, text=title))
                i += 3
                continue

            if tok.type == 'paragraph_open':
                inline = tokens[i + 1]
                if inline.type == 'inline':
                    text, images = self._inline_content(inline, filepath, asset_store)
                    for img in images:
                        blocks.append(DocumentBlock(type='image', image=img))
                    if text.strip():
                        blocks.append(DocumentBlock(type='paragraph', text=text.strip()))
                i += 3
                continue

            if tok.type == 'table_open':
                table, i = self._parse_table(tokens, i)
                if table:
                    blocks.append(DocumentBlock(type='table', table=table))
                continue

            if tok.type == 'fence':
                blocks.append(DocumentBlock(type='paragraph', text=tok.content))
                i += 1
                continue

            i += 1

        return blocks

    def _inline_content(self, inline: Token, filepath: str, asset_store: AssetStore):
        text_parts = []
        images = []
        for child in inline.children or []:
            if child.type == 'text':
                text_parts.append(child.content)
            elif child.type == 'code_inline':
                text_parts.append(child.content)
            elif child.type == 'softbreak':
                text_parts.append('\n')
            elif child.type == 'image':
                src = child.attrs.get('src', '') if child.attrs else ''
                alt = child.content or ''
                image = asset_store.resolve_md_image(src, filepath)
                if image:
                    image.alt = alt
                    images.append(image)
        return ''.join(text_parts), images

    def _parse_table(self, tokens: List[Token], start: int) -> Tuple[Optional[TableData], int]:
        i = start + 1
        headers: List[str] = []
        rows: List[List[str]] = []

        while i < len(tokens) and tokens[i].type != 'table_close':
            if tokens[i].type == 'tr_open':
                i += 1
                row = []
                while i < len(tokens) and tokens[i].type != 'tr_close':
                    if tokens[i].type in ('th_open', 'td_open'):
                        cell_inline = tokens[i + 1]
                        cell_text = cell_inline.content if cell_inline.type == 'inline' else ''
                        row.append(cell_text.strip())
                        i += 3
                    else:
                        i += 1
                if row:
                    if not headers and tokens[start + 1].type == 'thead_open':
                        headers = row
                    else:
                        rows.append(row)
                i += 1
                continue
            i += 1

        if headers or rows:
            if not headers and rows:
                headers = rows[0]
                rows = rows[1:]
            return TableData(headers=headers, rows=rows), i + 1
        return None, i + 1
