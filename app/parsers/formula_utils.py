"""公式提取：Word OMML → LaTeX，文本/Markdown 中的 $...$ / $$...$$。"""
from typing import List, Optional

from docx.oxml.ns import qn

from app.parsers.vendor.omml2latex import convert_omml

MATH_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'


def _local_tag(tag: str) -> str:
    return tag.split('}')[-1] if '}' in tag else tag


def _run_text(run_el) -> str:
    parts: List[str] = []
    for t in run_el.findall('.//' + qn('w:t')):
        if t.text:
            parts.append(t.text)
    return ''.join(parts)


def _unwrap_latex_delimiters(latex: str) -> str:
    latex = (latex or '').strip()
    if latex.startswith('$$') and latex.endswith('$$'):
        return latex[2:-2].strip()
    if latex.startswith('$') and latex.endswith('$'):
        return latex[1:-1].strip()
    return latex


def omml_element_to_latex(omath_el, display: bool = False) -> Optional[str]:
    try:
        raw = convert_omml(omath_el)
        inner = _unwrap_latex_delimiters(raw)
        if not inner:
            return None
        if display:
            return f'$${inner}$$'
        return f'${inner}$'
    except Exception:
        return None


def docx_paragraph_text(paragraph) -> str:
    """从 Word 段落提取文本，并将 OMML 公式转为 LaTeX 标记。"""
    el = paragraph._element
    parts: List[str] = []
    for child in el:
        tag = _local_tag(child.tag)
        if tag == 'r':
            text = _run_text(child)
            if text:
                parts.append(text)
        elif tag == 'oMath':
            latex = omml_element_to_latex(child, display=False)
            if latex:
                parts.append(latex)
        elif tag == 'oMathPara':
            for om in child:
                if _local_tag(om.tag) == 'oMath':
                    latex = omml_element_to_latex(om, display=True)
                    if latex:
                        parts.append(f'\n{latex}\n')

    result = ''.join(parts).strip()
    if result:
        return result
    return (paragraph.text or '').strip()


def docx_cell_text(cell) -> str:
    """表格单元格文本（含公式）。"""
    parts: List[str] = []
    for para in cell.paragraphs:
        text = docx_paragraph_text(para)
        if text:
            parts.append(text)
    return '\n'.join(parts).strip()
