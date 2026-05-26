from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class TableData:
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    caption: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'headers': self.headers,
            'rows': self.rows,
            'caption': self.caption,
        }


@dataclass
class ImageData:
    asset_id: str
    filename: str
    alt: str = ''
    caption: Optional[str] = None

    def to_dict(self, doc_id: str) -> Dict[str, Any]:
        return {
            'id': self.asset_id,
            'path': f'/api/parse/{doc_id}/assets/{self.filename}',
            'alt': self.alt,
            'caption': self.caption,
        }


@dataclass
class DocumentBlock:
    type: str  # heading | paragraph | table | image
    level: Optional[int] = None
    number: Optional[str] = None
    label: Optional[str] = None
    text: Optional[str] = None
    inline_content: Optional[str] = None  # 与标题同行的正文
    table: Optional[TableData] = None
    image: Optional[ImageData] = None
