from typing import List, Optional

from app.parsers.heading_detector import parse_heading_line, parse_md_atx_heading
from app.parsers.models import DocumentBlock
from app.parsers.heading_detector import normalize_heading_label, split_heading_label


def make_heading_block(
    number: Optional[str],
    label: str,
    level: int,
    text: Optional[str] = None,
) -> DocumentBlock:
    """创建标题块，自动拆分同行正文到 inline_content。"""
    label = normalize_heading_label(label)
    short_label, inline = split_heading_label(label)
    if not short_label and inline:
        display_label = str(number) if number else label[:30]
    else:
        display_label = short_label or label or (number or '')
    return DocumentBlock(
        type='heading',
        number=number,
        label=display_label,
        level=level,
        text=text or label,
        inline_content=inline,
    )


def split_lines_heading_body(raw_text: str) -> List[DocumentBlock]:
    """将含换行的段落拆成「首行标题 + 其余正文」（Word 同段多行）。"""
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    if not lines:
        return []

    first = lines[0]
    md = parse_md_atx_heading(first)
    if md:
        number, label, level = md
        blocks = [make_heading_block(number, label, level, text=first)]
    else:
        numbered = parse_heading_line(first)
        if not numbered:
            return [DocumentBlock(type='paragraph', text=raw_text.strip())]
        number, label, level = numbered
        blocks = [make_heading_block(number, label, level, text=first)]

    rest = '\n'.join(lines[1:]).strip()
    if rest:
        blocks.append(DocumentBlock(type='paragraph', text=rest))
    return blocks
