"""跳过封面、目录等前置内容，定位正文第一章。"""
from typing import List

from app.parsers.models import DocumentBlock


def strip_preamble(blocks: List[DocumentBlock]) -> List[DocumentBlock]:
    """丢弃第一个标题之前的所有内容（封面、修订记录、目录等）。

    正文起点由 DocxExtractor._mark_body_started 在更早阶段判定，
    此函数作为安全网：找到第一个 heading block，从这里开始。
    """
    for i, block in enumerate(blocks):
        if block.type == 'heading':
            return blocks[i:]
    return blocks
