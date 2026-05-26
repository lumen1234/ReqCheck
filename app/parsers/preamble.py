"""跳过封面、目录，从正文「范围」开始。"""
from typing import List

from app.parsers.block_utils import make_heading_block
from app.parsers.heading_detector import parse_heading_line
from app.parsers.models import DocumentBlock
from app.parsers.section_registry import SectionContext, is_not_section_title


def strip_preamble(blocks: List[DocumentBlock]) -> List[DocumentBlock]:
    ctx = SectionContext()
    start = 0
    for i, block in enumerate(blocks):
        if block.type == 'heading' and block.number:
            if block.number == '1' or (block.label and '范围' in block.label):
                return _trim_root_leading_paragraphs(blocks[i:])
        if block.type == 'paragraph':
            text = (block.text or '').strip()
            if text in ('范围', '1 范围', '1范围', '1.\t范围', '1.\t范围\t1'):
                reg = ctx.resolve('范围')
                if reg:
                    n, l, lv = reg
                    return [make_heading_block(n, l, lv, text=text)] + blocks[i + 1:]
            numbered = parse_heading_line(text.replace('\t', ' '))
            if numbered:
                num, label, level = numbered
                if num == '1' and '范围' in label and not is_not_section_title(label):
                    return [make_heading_block(num, label, level, text=text)] + blocks[i + 1:]
    return blocks


def _trim_root_leading_paragraphs(blocks: List[DocumentBlock]) -> List[DocumentBlock]:
    return blocks
