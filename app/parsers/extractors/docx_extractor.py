import os
import re
from typing import List, Optional

from docx import Document
from docx.document import Document as DocumentType
from docx.oxml.ns import qn
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from docx.oxml.ns import qn

from app.parsers.asset_store import AssetStore
from app.parsers.block_utils import make_heading_block, split_lines_heading_body
from app.parsers.formula_utils import docx_cell_text, docx_paragraph_text
from app.parsers.heading_detector import (
    is_toc_line,
    label_looks_like_requirement_content,
    level_from_number,
    looks_like_body_section_title,
    parse_heading_line,
)
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

_TEMPLATE_REQUIREMENT_START_RE = re.compile(r'^\s*需求标识\s*[:：]\s*\S+')
_TEMPLATE_FIELD_RE = re.compile(r'^\s*[^:：\s]{2,20}\s*[:：]\s*.+$')

_LENIENT_TOP_TITLES = {
    '更改登记',
    '目录',
    '范围',
    '引用文档',
    '需求',
    '合格性规定',
    '需求可追踪性',
    '注释',
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
        """统一的段落解析，适用于正式文档和模板文档。"""
        text = docx_paragraph_text(paragraph)
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

        # XML 大纲级别（w:outlineLvl）— 国军标文档常用 Normal + 大纲级别定义章节
        xml_outline_level = _paragraph_outline_level_from_xml(paragraph)
        if xml_outline_level is not None:
            self._mark_body_started(f'{xml_outline_level}', text)
            return blocks + [make_heading_block(None, text, xml_outline_level, text=text)]

        # 段落 XML 大纲级别（已在上面检查过，这里仅对无 outlineLvl 的段落做样式回退）
        if not xml_outline_level:
            outline_level = _paragraph_outline_level_from_style(style_name)
            if outline_level:
                self.body_started = True
                return blocks + [make_heading_block(None, text, outline_level, text=text)]

        if '\n' in text:
            is_first = True
            for sub in split_lines_heading_body(text):
                if sub.type == 'heading' and sub.number:
                    is_first = False
                    # 验证：数字编号开头不一定是真标题
                    if _validate_numbered_heading(paragraph, style_name, sub.label or '', next_paragraph):
                        fmt_level = _determine_heading_level(paragraph, sub.number, style_name)
                        if fmt_level:
                            sub.level = fmt_level
                        self._mark_body_started(sub.number, sub.label or '')
                        self.section_ctx.sync_number(sub.number)
                        if self.body_started or sub.number == '1':
                            blocks.append(sub)
                    elif self.body_started:
                        # 验证不通过 → 数字编号只是内容，降级为正文段落
                        blocks.append(DocumentBlock(type='paragraph', text=sub.text or ''))
                elif self.body_started:
                    if is_first:
                        # 单行段落（首行无编号）→ 正常分类
                        blocks.extend(self._classify_block(sub, style_name, next_paragraph, paragraph, raw_text=sub.text))
                    else:
                        # 多行拆分后的剩余行 → 直接作正文，不重新分类
                        if sub.text and sub.text.strip():
                            blocks.append(DocumentBlock(type='paragraph', text=sub.text))
                is_first = False
                # 正文未开始时的非标题换行段落：忽略（封面/修订记录等前置内容）
            return blocks

        blocks.extend(self._classify_block(
            DocumentBlock(type='paragraph', text=text),
            style_name,
            next_paragraph,
            paragraph,
            raw_text=text,
        ))
        return blocks

    def _classify_block(
        self,
        block: DocumentBlock,
        style_name: str,
        next_paragraph: Optional[Paragraph],
        paragraph: Optional[Paragraph] = None,
        raw_text: Optional[str] = None,
    ) -> List[DocumentBlock]:
        """统一的段落分类级联，同时适用于正式文档和模板文档。"""
        text = raw_text or block.text or ''
        text = text.strip()
        if not text:
            return []

        # 非章节标题关键词 → 正文
        if is_not_section_title(text):
            if self.body_started:
                return [DocumentBlock(type='paragraph', text=text)]
            return []

        # 1) 带编号标题：仅在段落有 Word 格式信号时才从数字文本提取编号。
        #    正文也常以数字开头（如 "3.2.1 描述了系统…"），
        #    无格式的数字行不当作标题。
        numbered = parse_heading_line(text)
        if numbered:
            number, label, _ = numbered  # 忽略文本推算的层级
            if not is_not_section_title(label):
                if _validate_numbered_heading(paragraph, style_name, label, next_paragraph):
                    self._mark_body_started(number, label)
                    self.section_ctx.sync_number(number)
                    level = _determine_heading_level(paragraph, number, style_name)
                    return [make_heading_block(number, label, level, text=text)]
                # 验证不通过：数字开头但实质是正文，继续落入后续步骤

        # 2) GJB 438C 标准章节名匹配（无编号/无样式时的回退）
        reg = self.section_ctx.resolve(text, HEADING_STYLES.get(style_name))
        if reg and reg[0]:
            number, label, level = reg
            self._mark_body_started(number, label)
            self.section_ctx.sync_number(number)
            return [make_heading_block(number, label, level, text=text)]

        # 3) Word 样式标题（Heading 1..6 / 标题 1..6）
        outline_level = _paragraph_outline_level_from_style(style_name)
        if outline_level:
            self.body_started = True
            return [make_heading_block(None, text, outline_level, text=text)]

        # 4) 模板需求起始行（如「需求标识: REQ-001」）
        if _is_template_requirement_start(text):
            self.body_started = True
            return [make_heading_block(None, text, 2, text=text)]

        # 5) 模板元数据字段（如「需求来源: N/A」）→ 正文，不提升为标题
        if _is_template_metadata_field(text):
            if self.body_started:
                return [DocumentBlock(type='paragraph', text=text)]
            return []

        # 6) 启发式短文本标题
        if looks_like_body_section_title(text):
            if '：' not in text and ':' not in text and not text.startswith('$$'):
                if _is_lenient_top_title(text):
                    # 已知的顶级章节名（范围/需求/合格性规定等）→ 无条件接受
                    self.body_started = True
                    return [make_heading_block(None, text, 1, text=text)]
                elif self.body_started and _next_paragraph_looks_like_body(next_paragraph):
                    return [make_heading_block(None, text, 2, text=text)]

        # 7) 正文段落（仅在正文开始后收集）
        if not self.body_started:
            return []
        return [DocumentBlock(type='paragraph', text=text)]

    def _mark_body_started(self, number: str, label: str) -> None:
        """标记正文起点。封面/目录已被上游过滤，第一个到达的标题即为正文第一章。"""
        if self.body_started:
            return
        self.body_started = True


def _paragraph_outline_level_from_style(style_name: str) -> Optional[int]:
    return HEADING_STYLES.get(style_name)


def _paragraph_outline_level_from_xml(paragraph: Paragraph) -> Optional[int]:
    """读取 Word 段落 XML 中的 w:outlineLvl 属性。

    Word 允许将任意段落的大纲级别设为「正文文本」以外的值（1-9 级），
    即使段落样式不是 Heading 1..6。这在国军标文档中很常见。

    返回 parser 内部 level（即 outlineLvl + 1），或 None。
    """
    pPr = paragraph._element.find(qn('w:pPr'))
    if pPr is None:
        return None
    ol = pPr.find(qn('w:outlineLvl'))
    if ol is None:
        return None
    try:
        outline_lvl = int(ol.get(qn('w:val')))
        return outline_lvl + 1  # 0-based → 1-based
    except (TypeError, ValueError):
        return None


def _paragraph_numbering_level_from_xml(paragraph: Paragraph) -> Optional[int]:
    """读取 Word 段落自动编号的缩进级别（w:numPr/w:ilvl）。

    Word 的自动编号（如 "3.2.1"）会在段落属性中记录列表层级，
    ilvl 值从 0 开始，返回 parser 内部 level（ilvl + 1）。

    这比从数字文本中点号数量推断层级更可靠，因为正文内容
    也可能以数字开头。
    """
    pPr = paragraph._element.find(qn('w:pPr'))
    if pPr is None:
        return None
    numPr = pPr.find(qn('w:numPr'))
    if numPr is None:
        return None
    ilvl = numPr.find(qn('w:ilvl'))
    if ilvl is None:
        return None
    try:
        return int(ilvl.get(qn('w:val'))) + 1  # 0-based → 1-based
    except (TypeError, ValueError):
        return None



def _paragraph_has_bold_formatting(paragraph: Paragraph) -> bool:
    """检查段落任意 run 是否有加粗格式（<w:b/> 或 <w:b w:val='1'/>）。"""
    for run in paragraph._element.findall(qn('w:r')):
        rPr = run.find(qn('w:rPr'))
        if rPr is None:
            continue
        b = rPr.find(qn('w:b'))
        if b is None:
            continue
        val = b.get(qn('w:val'))
        if val is None or val in ('1', 'true', 'on'):
            return True
    return False


def _paragraph_font_size_pt(paragraph: Paragraph):
    """读取段落首个 run 的字号，半磅转 pt（w:val='32' = 16pt）。无信息返回 None。"""
    for run in paragraph._element.findall(qn('w:r')):
        rPr = run.find(qn('w:rPr'))
        if rPr is None:
            continue
        sz = rPr.find(qn('w:sz'))
        if sz is not None:
            try:
                return int(sz.get(qn('w:val'))) / 2.0
            except (TypeError, ValueError):
                continue
    return None


def _paragraph_has_heading_font(paragraph: Paragraph) -> bool:
    """检查段落字体格式是否像标题（加粗 / >=13pt 且加粗 / >=16pt）。"""
    font_size = _paragraph_font_size_pt(paragraph)
    is_bold = _paragraph_has_bold_formatting(paragraph)
    if is_bold and font_size is not None and font_size >= 13:
        return True
    if is_bold:
        return True
    if font_size is not None and font_size >= 16:
        return True
    return False


def _determine_heading_level(
    paragraph: Optional[Paragraph],
    number: str,
    style_name: str = '',
) -> int:
    """综合多种信号确定标题层级，避免仅依赖数字文本中点号数量。

    优先级：
    1. Word 标题样式（Heading 1-6 / 标题 1-6）
    2. Word 自动编号缩进级别（w:numPr/w:ilvl）
    3. 从数字文本推算（兜底）
    """
    # 1) Word 样式
    if style_name:
        style_level = HEADING_STYLES.get(style_name)
        if style_level:
            return style_level
    # 2) Word 自动编号缩进级别
    if paragraph is not None:
        num_level = _paragraph_numbering_level_from_xml(paragraph)
        if num_level:
            return num_level
    # 3) 兜底：从数字文本推算
    return level_from_number(number)


def _is_template_requirement_start(text: str) -> bool:
    return bool(_TEMPLATE_REQUIREMENT_START_RE.match(text or ''))


def _is_template_metadata_field(text: str) -> bool:
    text = (text or '').strip()
    if not text or _is_template_requirement_start(text):
        return False
    return bool(_TEMPLATE_FIELD_RE.match(text))


def _is_lenient_top_title(text: str) -> bool:
    normalized = (text or '').strip().replace(' ', '').replace('\u3000', '')
    return normalized in _LENIENT_TOP_TITLES


# \u2500\u2500\u2500 \u7f16\u53f7\u6807\u9898\u9a8c\u8bc1\uff1a\u6570\u5b57\u5f00\u5934\u4e0d\u7b49\u4e8e\u6807\u9898 \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def _has_word_heading_formatting(
    paragraph: Optional[Paragraph],
    style_name: str = '',
) -> bool:
    """检查段落是否有 Word 格式信号表明它是真正的标题。

    信号包括：样式名、大纲级别、自动编号缩进、字体格式（加粗/大字号）。
    不包括数字文本模式。
    """
    if style_name and style_name in HEADING_STYLES:
        return True
    if paragraph is not None:
        if _paragraph_numbering_level_from_xml(paragraph) is not None:
            return True
        if _paragraph_outline_level_from_xml(paragraph) is not None:
            return True
        if _paragraph_has_heading_font(paragraph):
            return True
    return False


def _next_paragraph_looks_like_body(next_paragraph: Optional[Paragraph]) -> bool:
    """检查下一段是否像正文（而非标题），用于上下文判定。

    如果当前行疑似标题但无格式信号，看下一段：
    - 下一段是长文本/需求句式 → 像正文 → 当前更像标题
    - 下一段也有标题特征 → 当前大概率也是正文
    - 无下一段 → 保守返回 False
    """
    if next_paragraph is None:
        return False
    next_text = docx_paragraph_text(next_paragraph).strip()
    if not next_text:
        return False
    # 下一段有 Word 标题格式 → 后继是标题，削弱当前是标题的可能性
    next_style = (next_paragraph.style.name.lower()
                  if next_paragraph.style and next_paragraph.style.name else '')
    if _has_word_heading_formatting(next_paragraph, next_style):
        return False
    # 下一段是长文本（>50字）→ 像正文
    if len(next_text) > 50:
        return True
    # 下一段包含需求关键词 → 像需求正文
    if label_looks_like_requirement_content(next_text):
        return True
    # 下一段也像短标题 → 当前不像标题
    if looks_like_body_section_title(next_text):
        return False
    return False


def _validate_numbered_heading(
    paragraph: Optional[Paragraph],
    style_name: str,
    label: str,
    next_paragraph: Optional[Paragraph] = None,
) -> bool:
    """验证一个以数字编号开头的行是否为真正的标题。

    需要满足以下任一条件：
    1. 段落有 Word 格式信号（样式 / 自动编号 / 大纲级别 / 字体格式）
    2. 标签文本像标题，且下一段像正文（无格式信号时必须）
    """
    if _has_word_heading_formatting(paragraph, style_name):
        return True
    if label_looks_like_requirement_content(label):
        return False
    # 无格式信号时，要求下一段像正文，否则倾向于拒绝
    if next_paragraph is not None and not _next_paragraph_looks_like_body(next_paragraph):
        return False
    return True

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
