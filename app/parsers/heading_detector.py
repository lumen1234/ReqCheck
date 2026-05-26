import re
from typing import Optional, Tuple

# 1.1 标识 / 3.2.X 能力 / 3.7保密性（编号与标题可无空格）
HEADING_NUM_RE = re.compile(
    r'^(\d+(?:\.(?:\d+|[Xx]))*)\s*(.*)$'
)
# 「1范围」「1.1标识」无空格
HEADING_NUM_COMPACT_RE = re.compile(
    r'^(\d+(?:\.(?:\d+|[Xx]))+)([\u4e00-\u9fa5a-zA-Z（(].*)$'
)
HEADING_CHAPTER_COMPACT_RE = re.compile(
    r'^(\d)([\u4e00-\u9fa5a-zA-Z（(][^）\)]*)$'
)
CHAPTER_RE = re.compile(r'^第\s*(\d+)\s*章\s*(.*)$')
MD_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$')
LIST_ITEM_RE = re.compile(r'^[a-zA-Z][\.\)、）]\s*|^（\d+）')
# Word 目录行：制表符 + 末尾页码，或「.\t标题\t页码」
TOC_LINE_RE = re.compile(
    r'^(?:[\d\.]+)?\s*\.?\t.+\t\d{1,4}\s*$|^.+\t\d{1,4}\s*$'
)

_INLINE_BODY_MARKERS = (
    '本条', '本章', '本节', '（若有）', '如需', '应指明', '应描述',
    '应列出', '应概述', '应标识', '应定义', '应包括', '应规定',
)


def is_toc_line(line: str) -> bool:
    """判断是否为 Word 自动目录行。"""
    line = line.strip()
    if not line:
        return False
    if TOC_LINE_RE.match(line):
        return True
    if '\t' in line and re.search(r'\t\d{1,4}\s*$', line):
        return True
    if re.match(r'^\.\t', line):
        return True
    return False


def normalize_heading_label(label: str) -> str:
    """清理目录残留格式。"""
    label = label.strip()
    label = re.sub(r'^\.\s*', '', label)
    label = re.sub(r'\t\d{1,4}\s*$', '', label)
    label = label.replace('\t', ' ').strip()
    return label


def looks_like_body_section_title(text: str) -> bool:
    """正文中的无编号小标题，如「标识」「系统概述」。"""
    text = text.strip()
    if not text or len(text) > 35 or len(text) < 2:
        return False
    if is_toc_line(text) or LIST_ITEM_RE.match(text):
        return False
    if parse_heading_line(text):
        return False
    if text.endswith(('。', '；', ';', '.', '：', ':')):
        return False
    if any(m in text for m in _INLINE_BODY_MARKERS):
        return False
    if re.match(r'^表\s*\d+', text) or re.match(r'^图\s*\d+', text):
        return False
    return True


def level_from_number(number: str) -> int:
    parts = [p for p in number.split('.') if p and p.lower() != 'x']
    return len(parts) if parts else 1


def parse_heading_line(line: str) -> Optional[Tuple[str, str, int]]:
    """解析带数字编号的标题行，返回 (number, label, level)。"""
    line = line.strip()
    if not line or LIST_ITEM_RE.match(line) or is_toc_line(line):
        return None
    # 排除列表项：1）xxx、a）xxx
    if re.match(r'^\d+[）\)]', line):
        return None

    chapter = CHAPTER_RE.match(line)
    if chapter:
        number = chapter.group(1)
        label = chapter.group(2).strip() or f'第{number}章'
        return number, label, 1

    match = HEADING_NUM_RE.match(line)
    if match:
        number = match.group(1)
        label = match.group(2).strip()
    else:
        normalized = line.replace(' ', '').replace('\u3000', '')
        compact = HEADING_NUM_COMPACT_RE.match(normalized)
        if not compact:
            compact = HEADING_CHAPTER_COMPACT_RE.match(normalized)
        if not compact:
            return None
        number = compact.group(1)
        label = compact.group(2).strip()

    if not label:
        return None
    label = normalize_heading_label(label)
    from app.parsers.section_registry import is_not_section_title
    if is_not_section_title(label) or is_toc_line(f'{number} {label}'):
        return None
    if label.isdigit() and len(number.split('.')) == 1:
        return None
    return number, label, level_from_number(number)


def parse_md_atx_heading(line: str) -> Optional[Tuple[Optional[str], str, int]]:
    """解析 Markdown ATX 标题，优先从文本中提取数字编号。"""
    line = line.strip()
    match = MD_HEADING_RE.match(line)
    if not match:
        return None

    md_level = len(match.group(1))
    title_text = match.group(2).strip()

    numbered = parse_heading_line(title_text)
    if numbered:
        number, label, num_level = numbered
        return number, label, num_level

    return None, title_text, md_level


def number_to_node_id(number: str) -> str:
    parts = re.split(r'[.\-]+', number.replace('X', 'x').lower())
    safe = [p for p in parts if p]
    return 'node_' + '_'.join(safe) if safe else 'node_unknown'


def split_heading_label(label: str) -> Tuple[str, Optional[str]]:
    """
    将「标题 + 同行正文」拆开，例如：
    「系统概述 本条应概述…」-> ('系统概述', '本条应概述…')
    """
    label = label.strip()
    if not label:
        return label, None

    for marker in _INLINE_BODY_MARKERS:
        idx = label.find(marker)
        if idx > 0:
            title_part = label[:idx].strip()
            body_part = label[idx:].strip()
            if title_part and len(title_part) <= 50:
                return title_part, body_part
        if idx == 0:
            return '', label

    if len(label) > 40:
        for sep in ('，', '。', '；', ';'):
            idx = label.find(sep)
            if 2 < idx < 25:
                return label[:idx + 1].strip(), label[idx + 1:].strip()

    return label, None
