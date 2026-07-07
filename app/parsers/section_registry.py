# GJB 438C 软件需求规格说明 — 标准章节标题匹配（不包含文档特定的子节标题）
from typing import Dict, List, Optional, Tuple

CHAPTER_1: Dict[str, List[str]] = {
    '1': ['范围'],
    '2': ['引用文档'],
    '3': ['需求'],
    '4': ['合格性规定', '合格性'],
    '5': ['需求可追踪性', '可追踪性'],
    '6': ['注释'],
}

CHAPTER_2: Dict[str, List[Tuple[str, List[str]]]] = {
    '1': [
        ('1.1', ['标识']),
        ('1.2', ['系统概述']),
        ('1.3', ['文档概述']),
    ],
    '3': [
        ('3.1', ['要求的状态和方式', '状态和方式']),
        ('3.2', ['能力需求']),
        ('3.3', ['外部接口需求', '外部接口']),
        ('3.4', ['内部接口需求', '内部接口']),
        ('3.5', ['内部数据', '系统的内部数据', '内部数据需求']),
        ('3.6', ['适应性需求']),
        ('3.7', ['保密性']),
        ('3.8', ['安全性']),
        ('3.9', ['环境适应性', '环境适应性需求']),
        ('3.10', ['其他质量特性', '质量特性']),
        ('3.11', ['计算机资源']),
        ('3.12', ['设计和实现约束', '设计约束']),
        ('3.13', ['人员相关']),
        ('3.14', ['训练相关']),
        ('3.15', ['软件保障']),
        ('3.16', ['包装需求', '包装']),
        ('3.17', ['优先顺序', '关键程度', '关键程度']),
        ('3.18', ['其他需求']),
    ],
    '4': [
        ('4.1', ['合格性方法']),
        ('4.2', ['合格性级别']),
    ],
}

NOT_SECTION_KEYWORDS = (
    '一览表', '参考表', '追踪表', '见表', '数据帧',
)


def is_not_section_title(text: str) -> bool:
    text = text.strip()
    return any(kw in text for kw in NOT_SECTION_KEYWORDS)


class SectionContext:
    """章节上下文：用于无编号/无样式标题时，按 GJB 438C 标准章节名匹配。"""

    def __init__(self):
        self.current_chapter: Optional[str] = None
        self.current_section: Optional[str] = None

    def sync_number(self, number: str) -> None:
        parts = number.split('.')
        if parts and parts[0].isdigit():
            self.current_chapter = parts[0]
            if len(parts) >= 2:
                self.current_section = '.'.join(parts[:2])
            else:
                self.current_section = None

    def resolve(self, text: str, style_level: Optional[int] = None) -> Optional[Tuple[str, str, int]]:
        """返回 (编号, 短标签, 层级) 或 None。仅匹配 GJB 438C 标准的一/二级章节标题。"""
        label = text.strip()
        if not label or len(label) > 60 or is_not_section_title(label):
            return None

        for num, keys in CHAPTER_1.items():
            if _label_matches(label, keys):
                self.current_chapter = num
                self.current_section = None
                short = _pick_short_label(label, keys)
                return num, short, 1

        if self.current_chapter and self.current_chapter in CHAPTER_2:
            for sub_num, keys in CHAPTER_2[self.current_chapter]:
                if _label_matches(label, keys):
                    self.current_section = sub_num
                    short = _pick_short_label(label, keys)
                    return sub_num, short, 2

        return None


def _label_matches(label: str, keys: List[str]) -> bool:
    norm = label.replace(' ', '').replace('　', '')
    for k in keys:
        k = k.replace(' ', '')
        if norm == k:
            return True
        if len(k) >= 3 and len(norm) <= len(k) + 4 and k in norm:
            return True
    return False


def _pick_short_label(label: str, keys: List[str]) -> str:
    for k in keys:
        if k in label:
            return k
    return label[:30] if len(label) > 30 else label
