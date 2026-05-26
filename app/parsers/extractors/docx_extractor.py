import os
from typing import List, Optional

from docx import Document
from docx.document import Document as DocumentType
from docx.oxml.ns import qn
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from docx.oxml.ns import qn

from app.parsers.asset_store import AssetStore
from app.parsers.block_utils import make_heading_block, split_lines_heading_body
from app.parsers.heading_detector import is_toc_line, parse_heading_line
from app.parsers.models import DocumentBlock, TableData
from app.parsers.section_registry import SectionContext, is_not_section_title

# OOXML 命名空间（含 Word VML 图片）
_A_NS = 'http://schemas.openxmlformats.org/drawingml/2006/main'
_R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
_VML_NS = 'urn:schemas-microsoft-com:vml'
_OOXML_NS = {'a': _A_NS, 'r': _R_NS, 'v': _VML_NS}

HEADING_STYLES = {
    'heading 1': 1, 'heading 2': 2, 'heading 3': 3,
    'heading 4': 4, 'heading 5': 5, 'heading 6': 6,
    '标题 1': 1, '标题 2': 2, '标题 3': 3,
    '标题 4': 4, '标题 5': 5, '标题 6': 6,
}

TOC_STYLES = {
    'toc 1', 'toc 2', 'toc 3', 'toc 4', 'toc 5', 'toc 6', 'toc 7', 'toc 8', 'toc 9',
    '目录 1', '目录 2', '目录 3',
}


class DocxExtractor:
    def __init__(self):
        self.section_ctx = SectionContext()
        self.body_started = False

    def extract(self, filepath: str, asset_store: AssetStore) -> List[DocumentBlock]:
        doc = Document(filepath)
        self.section_ctx = SectionContext()
        self.body_started = False
        body_items = list(_iter_block_items(doc))

        blocks: List[DocumentBlock] = []
        i = 0
        while i < len(body_items):
            item = body_items[i]
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
            i += 1
        return blocks

    def _parse_paragraph(
        self,
        paragraph: Paragraph,
        doc: Document,
        asset_store: AssetStore,
        next_paragraph: Optional[Paragraph] = None,
    ) -> List[DocumentBlock]:
        text = paragraph.text.strip()
        blocks: List[DocumentBlock] = []

        for image in _extract_inline_images(paragraph, doc, asset_store, next_paragraph):
            if self.body_started:
                blocks.append(DocumentBlock(type='image', image=image))

        if not text or is_toc_line(text):
            return blocks

        style_name = ''
        if paragraph.style and paragraph.style.name:
            style_name = paragraph.style.name.lower()
        if style_name in TOC_STYLES:
            return blocks

        if '\n' in text:
            for sub in split_lines_heading_body(text):
                if sub.type == 'heading' and sub.number:
                    self._mark_body_started(sub.number, sub.label or '')
                    self.section_ctx.sync_number(sub.number)
                    if self.body_started or sub.number == '1':
                        self.body_started = True
                        blocks.append(sub)
                elif self.body_started:
                    blocks.extend(self._classify_block(sub, style_name, next_paragraph, raw_text=sub.text))
            return blocks

        blocks.extend(self._classify_block(
            DocumentBlock(type='paragraph', text=text),
            style_name,
            next_paragraph,
            raw_text=text,
        ))
        return blocks

    def _classify_block(
        self,
        block: DocumentBlock,
        style_name: str,
        next_paragraph: Optional[Paragraph],
        raw_text: Optional[str] = None,
    ) -> List[DocumentBlock]:
        text = raw_text or block.text or ''
        text = text.strip()
        if not text:
            return []

        if is_not_section_title(text):
            if self.body_started:
                return [DocumentBlock(type='paragraph', text=text)]
            return []

        numbered = parse_heading_line(text)
        if numbered:
            number, label, level = numbered
            if is_not_section_title(label):
                numbered = None
            else:
                self._mark_body_started(number, label)
                self.section_ctx.sync_number(number)
                return [make_heading_block(number, label, level, text=text)]

        reg = self.section_ctx.resolve(text, HEADING_STYLES.get(style_name))
        if reg and reg[0]:
            number, label, level = reg
            self._mark_body_started(number, label)
            self.section_ctx.sync_number(number)
            return [make_heading_block(number, label, level, text=text)]

        outline_level = _paragraph_outline_level_from_style(style_name)
        if outline_level and self.body_started:
            return [make_heading_block(None, text, outline_level, text=text)]

        if not self.body_started:
            return []

        return [DocumentBlock(type='paragraph', text=text)]

    def _mark_body_started(self, number: str, label: str) -> None:
        if self.body_started:
            return
        if number == '1' or '范围' in (label or ''):
            self.body_started = True


def _paragraph_outline_level_from_style(style_name: str) -> Optional[int]:
    return HEADING_STYLES.get(style_name)


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
            cells.append(cell.text.strip())
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
    text = paragraph.text.strip()
    if text:
        return text
    if next_paragraph:
        nxt = next_paragraph.text.strip()
        if nxt.startswith('图') or nxt.lower().startswith('fig'):
            return nxt
    return ''


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
                    alt=caption or '图片',
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
                            alt=caption or '图片',
                            caption=caption or None,
                        )
                    )
                except Exception:
                    continue
    return images
