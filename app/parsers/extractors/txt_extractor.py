import os
import re
from typing import List, Optional, Tuple

from app.parsers.asset_store import AssetStore
from app.parsers.heading_detector import (
    LIST_ITEM_RE,
    is_toc_line,
    parse_heading_line,
    parse_md_atx_heading,
)
from app.parsers.block_utils import make_heading_block
from app.parsers.models import DocumentBlock, TableData

MD_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
MD_TABLE_SEP_RE = re.compile(r'^\|[\s\-\|:]+\|$')


class TxtExtractor:
    def extract(self, filepath: str, asset_store: AssetStore) -> List[DocumentBlock]:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        blocks: List[DocumentBlock] = []
        i = 0
        while i < len(lines):
            raw = lines[i].rstrip('\n\r')
            line = raw.strip()

            if not line:
                i += 1
                continue

            if is_toc_line(line):
                i += 1
                continue

            md_heading = parse_md_atx_heading(raw)
            if md_heading:
                number, label, level = md_heading
                blocks.append(make_heading_block(number, label, level, text=raw.strip()))
                i += 1
                continue

            numbered = parse_heading_line(line)
            if numbered and not LIST_ITEM_RE.match(line):
                number, label, level = numbered
                blocks.append(make_heading_block(number, label, level, text=line))
                i += 1
                continue

            if line.startswith('|') and i + 1 < len(lines):
                table_lines, next_i = _collect_md_table(lines, i)
                if table_lines:
                    table = _parse_md_table_lines(table_lines)
                    if table:
                        blocks.append(DocumentBlock(type='table', table=table))
                        i = next_i
                        continue

            tab_table, next_i = _try_tab_table(lines, i)
            if tab_table:
                blocks.append(DocumentBlock(type='table', table=tab_table))
                i = next_i
                continue

            img_match = MD_IMAGE_RE.search(line)
            if img_match:
                alt, src = img_match.group(1), img_match.group(2)
                image = asset_store.resolve_md_image(src, filepath)
                if image:
                    blocks.append(DocumentBlock(type='image', image=image))
                text_without = MD_IMAGE_RE.sub('', line).strip()
                if text_without:
                    blocks.append(DocumentBlock(type='paragraph', text=text_without))
                i += 1
                continue

            blocks.append(DocumentBlock(type='paragraph', text=line))
            i += 1

        return blocks


def _collect_md_table(lines: List[str], start: int):
    collected = []
    i = start
    while i < len(lines):
        s = lines[i].strip()
        if not s.startswith('|'):
            break
        collected.append(s)
        i += 1
    if len(collected) < 2:
        return None, start + 1
    if not MD_TABLE_SEP_RE.match(collected[1]):
        return None, start + 1
    return collected, i


def _parse_md_table_lines(table_lines: List[str]) -> Optional[TableData]:
    def split_row(row: str) -> List[str]:
        row = row.strip().strip('|')
        return [c.strip() for c in row.split('|')]

    headers = split_row(table_lines[0])
    rows = [split_row(r) for r in table_lines[2:]]
    if not headers:
        return None
    return TableData(headers=headers, rows=rows)


def _try_tab_table(lines: List[str], start: int):
    row = lines[start].rstrip('\n\r')
    if '\t' not in row:
        parts = re.split(r'\s{2,}', row.strip())
        if len(parts) < 2:
            return None, start + 1
    else:
        parts = [p.strip() for p in row.split('\t')]

    collected = [parts]
    i = start + 1
    while i < len(lines):
        nxt = lines[i].rstrip('\n\r')
        if not nxt.strip():
            break
        if parse_heading_line(nxt.strip()):
            break
        if '\t' in nxt:
            collected.append([p.strip() for p in nxt.split('\t')])
        else:
            cols = re.split(r'\s{2,}', nxt.strip())
            if len(cols) != len(parts):
                break
            collected.append(cols)
        i += 1

    if len(collected) < 2:
        return None, start + 1

    return TableData(headers=collected[0], rows=collected[1:]), i
