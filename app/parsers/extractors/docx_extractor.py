import os
from typing import List, Optional

from docx import Document
from docx.document import Document as DocumentType
from docx.oxml.ns import qn
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from app.parsers.asset_store import AssetStore
from app.parsers.formula_utils import docx_cell_text, docx_paragraph_text
from app.parsers.heading_detector import is_toc_line
from app.parsers.models import DocumentBlock, TableData

# OOXML 命名空间（含 Word VML 图片）
_A_NS = 'http://schemas.openxmlformats.org/drawingml/2006/main'
_R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
_VML_NS = 'urn:schemas-microsoft-com:vml'
_OOXML_NS = {'a': _A_NS, 'r': _R_NS, 'v': _VML_NS}

TOC_STYLES = {
    'toc 1', 'toc 2', 'toc 3', 'toc 4', 'toc 5', 'toc 6', 'toc 7', 'toc 8', 'toc 9',
    '目录 1', '目录 2', '目录 3',
}


class DocxExtractor:
    """Docx 文档提取器。

    段落分类的唯一依据是 Word 大纲级别（w:outlineLvl）：
    - 有大纲级别 → 标题（大纲级别决定了标题层级）
    - 无大纲级别 → 正文

    大纲级别来源（按优先级）：
    1. 段落 XML 中显式设置的 w:outlineLvl
    2. 段落样式中定义的 w:outlineLvl（如 Heading 1/2/3 内置样式）
    """

    def __init__(self):
        self.body_started = False

    def extract(self, filepath: str, asset_store: AssetStore) -> List[DocumentBlock]:
        doc = Document(filepath)
        self.body_started = False
        body_items = list(_iter_block_items(doc))

        blocks: List[DocumentBlock] = []
        for i, item in enumerate(body_items):
            if isinstance(item, Paragraph):
                next_para = None
                if i + 1 < len(body_items) and isinstance(body_items[i + 1], Paragraph):
                    next_para = body_items[i + 1]
                blocks.extend(self._parse_paragraph(item, doc, asset_store, next_para))
            elif isinstance(item, Table):
                if self.body_started:
                    table = _table_to_data(item)
                    if table.headers or table.rows:
                        blocks.append(DocumentBlock(type='table', table=table))
                    for row in item.rows:
                        for cell in row.cells:
                            for cell_para in cell.paragraphs:
                                for image in _extract_inline_images(cell_para, doc, asset_store):
                                    blocks.append(DocumentBlock(type='image', image=image))
        return blocks

    def _parse_paragraph(
        self,
        paragraph: Paragraph,
        doc: Document,
        asset_store: AssetStore,
        next_paragraph: Optional[Paragraph] = None,
    ) -> List[DocumentBlock]:
        text = docx_paragraph_text(paragraph)
        blocks: List[DocumentBlock] = []

        for image in _extract_inline_images(paragraph, doc, asset_store, next_paragraph):
            if self.body_started:
                blocks.append(DocumentBlock(type='image', image=image))

        # ── 大纲级别检查必须在文本内容检查之前 ──
        # 有空文本但有大纲级别的段落（空标题）仍然算标题
        outline_level = _get_effective_outline_level(paragraph, doc)

        if outline_level is not None:
            self.body_started = True
            # 过滤 TOC 样式和目录行
            style_name = ''
            if paragraph.style and paragraph.style.name:
                style_name = paragraph.style.name.lower()
            if style_name in TOC_STYLES or (text and is_toc_line(text)):
                return blocks
            # 空标题：保留为 DocumentBlock heading，label 用空字符串
            label_text = text.strip() if text else ''
            if '\n' in label_text:
                lines = [ln.strip() for ln in label_text.splitlines() if ln.strip()]
                first = lines[0]
                blocks.append(DocumentBlock(
                    type='heading', number=None, label=first or '',
                    level=outline_level, text=first,
                ))
                rest = '\n'.join(lines[1:]).strip()
                if rest:
                    blocks.append(DocumentBlock(type='paragraph', text=rest))
                return blocks
            return blocks + [DocumentBlock(
                type='heading', number=None, label=label_text,
                level=outline_level, text=label_text,
            )]

        # 正文（无大纲级别）
        if not text or is_toc_line(text):
            return blocks

        style_name = ''
        if paragraph.style and paragraph.style.name:
            style_name = paragraph.style.name.lower()
        if style_name in TOC_STYLES:
            return blocks

        if not self.body_started:
            return []

        if '\n' in text:
            for line in text.splitlines():
                line = line.strip()
                if line:
                    blocks.append(DocumentBlock(type='paragraph', text=line))
            return blocks

        return [DocumentBlock(type='paragraph', text=text)]


# ── 大纲级别读取 ──

def _get_effective_outline_level(paragraph: Paragraph, doc: Document) -> Optional[int]:
    """获取段落有效的大纲级别。

    优先级：
    1. 段落 XML 中显式设置的 w:outlineLvl
    2. 段落样式定义中的 w:outlineLvl（如 Heading 1/2/3 等内置样式）

    Word 使用 0-based 值（0 = Level 1），返回 parser 内部 1-based level。
    无大纲级别时返回 None（视为正文）。
    """
    # 1) 段落级别 w:outlineLvl
    pPr = paragraph._element.find(qn('w:pPr'))
    if pPr is not None:
        ol = pPr.find(qn('w:outlineLvl'))
        if ol is not None:
            try:
                val = int(ol.get(qn('w:val')))
                if val >= 0:
                    return val + 1  # 0-based → 1-based
            except (TypeError, ValueError):
                pass

    # 2) 样式级别 w:outlineLvl（从 styles.xml 读取）
    style = paragraph.style
    if style is not None:
        style_pPr = style.element.find(qn('w:pPr'))
        if style_pPr is not None:
            ol = style_pPr.find(qn('w:outlineLvl'))
            if ol is not None:
                try:
                    val = int(ol.get(qn('w:val')))
                    if val >= 0:
                        return val + 1  # 0-based → 1-based
                except (TypeError, ValueError):
                    pass

    return None


# ── 表格 / 图片 / 迭代 ──

def _iter_block_items(parent):
    if isinstance(parent, DocumentType):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError('Unsupported container for block iteration')

    for child in parent_elm.iterchildren():
        if child.tag == qn('w:p'):
            yield Paragraph(child, parent)
        elif child.tag == qn('w:tbl'):
            yield Table(child, parent)


def _table_to_data(table: Table) -> TableData:
    rows_data: List[List[str]] = []
    for row in table.rows:
        cells = []
        seen = set()
        for cell in row.cells:
            cell_id = id(cell._tc)
            if cell_id in seen:
                continue
            seen.add(cell_id)
            cells.append(docx_cell_text(cell))
        if cells:
            rows_data.append(cells)

    if not rows_data:
        return TableData()

    return TableData(headers=rows_data[0], rows=rows_data[1:])


def _collect_embed_ids(element) -> List[str]:
    """收集段落/单元格中的图片关系 ID（DrawingML blip + VML imagedata）。"""
    ids: List[str] = []
    for blip in element.findall('.//a:blip', _OOXML_NS):
        embed = blip.get(f'{{{_R_NS}}}embed')
        if embed:
            ids.append(embed)
    for im in element.findall('.//v:imagedata', _OOXML_NS):
        rid = im.get(f'{{{_R_NS}}}id')
        if rid:
            ids.append(rid)
    return ids


def _caption_for_image(paragraph: Paragraph, next_paragraph: Optional[Paragraph]) -> str:
    return paragraph.text.strip()


def _extract_inline_images(
    paragraph: Paragraph,
    doc: Document,
    asset_store: AssetStore,
    next_paragraph: Optional[Paragraph] = None,
) -> List:
    images = []
    part = doc.part
    el = paragraph._element
    caption = _caption_for_image(paragraph, next_paragraph)

    for embed in _collect_embed_ids(el):
        if embed not in part.related_parts:
            continue
        image_part = part.related_parts[embed]
        ext = os.path.splitext(image_part.partname)[1] or '.png'
        try:
            images.append(
                asset_store.save_bytes(
                    image_part.blob,
                    ext,
                    alt=caption or '',
                    caption=caption or None,
                )
            )
        except Exception:
            continue

    # 兼容：部分文档 blip 仅在 run 层级（旧逻辑保留）
    if not images:
        for run in paragraph.runs:
            for blip in run._element.findall('.//' + qn('a:blip')):
                embed = blip.get(qn('r:embed'))
                if not embed or embed not in part.related_parts:
                    continue
                image_part = part.related_parts[embed]
                ext = os.path.splitext(image_part.partname)[1] or '.png'
                try:
                    images.append(
                        asset_store.save_bytes(
                            image_part.blob,
                            ext,
                            alt=caption or '',
                            caption=caption or None,
                        )
                    )
                except Exception:
                    continue
    return images
