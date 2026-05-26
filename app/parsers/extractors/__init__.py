from app.parsers.extractors.txt_extractor import TxtExtractor
from app.parsers.extractors.md_extractor import MdExtractor
from app.parsers.extractors.docx_extractor import DocxExtractor

EXTRACTORS = {
    'txt': TxtExtractor,
    'md': MdExtractor,
    'markdown': MdExtractor,
    'docx': DocxExtractor,
}


def get_extractor(ext: str):
    return EXTRACTORS.get(ext.lower())
