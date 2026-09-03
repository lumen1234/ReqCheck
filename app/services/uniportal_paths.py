"""UniPortal 共享卷路径：document-validator 与 project_name 同级（挂在 item 根下）。"""
from __future__ import annotations

import os
from typing import Optional

_DEFAULT_ALLOWED = frozenset({"txt", "docx", "md", "markdown"})
_DOC_PRIORITY = (".docx", ".md", ".markdown", ".txt")

# item 根下与 project_name 同级的子工具输出目录，扫描文档时跳过
TOOL_OUTPUT_DIR_NAMES = frozenset(
    {
        "document-validator",
        "configuration-test-case-generate",
        "uniportal",
    }
)


def _skip_dir_names(skip_subdir: Optional[str] = None) -> set[str]:
    names = set(TOOL_OUTPUT_DIR_NAMES)
    if skip_subdir:
        names.add(skip_subdir)
    return names


def _iter_document_files(
    root: str,
    *,
    skip_subdir: str = "document-validator",
    allowed_extensions: Optional[frozenset[str]] = None,
):
    """递归遍历 item 目录下的支持文档，跳过子工具输出目录。"""
    if not root or not os.path.isdir(root):
        return

    allowed = allowed_extensions or _DEFAULT_ALLOWED
    skip_names = _skip_dir_names(skip_subdir)

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_names and not d.startswith(".")]
        for name in filenames:
            if name.startswith("."):
                continue
            ext = os.path.splitext(name)[1].lower().lstrip(".")
            if ext not in allowed:
                continue
            yield os.path.join(dirpath, name)


def find_all_documents(
    root: str,
    *,
    skip_subdir: str = "document-validator",
    allowed_extensions: Optional[frozenset[str]] = None,
) -> list[str]:
    """返回目录树中全部支持的文档路径，按扩展名优先级 + 路径排序。"""
    found: list[tuple[int, str]] = []
    for full in _iter_document_files(
        root, skip_subdir=skip_subdir, allowed_extensions=allowed_extensions
    ):
        ext = os.path.splitext(full)[1].lower()
        prio = _DOC_PRIORITY.index(ext) if ext in _DOC_PRIORITY else len(_DOC_PRIORITY)
        found.append((prio, full))

    found.sort(key=lambda x: (x[0], x[1].replace("\\", "/").lower()))
    return [path for _, path in found]


def find_primary_document(
    root: str,
    *,
    skip_subdir: str = "document-validator",
    allowed_extensions: Optional[frozenset[str]] = None,
) -> Optional[str]:
    docs = find_all_documents(
        root, skip_subdir=skip_subdir, allowed_extensions=allowed_extensions
    )
    return docs[0] if docs else None


def pick_project_content_name(
    item_dir: str,
    *,
    skip_subdir: str = "document-validator",
) -> Optional[str]:
    """推断 item 下的 project_name 目录（非工具输出的唯一内容目录）。"""
    if not item_dir or not os.path.isdir(item_dir):
        return None
    skip_names = _skip_dir_names(skip_subdir)
    candidates = [
        name
        for name in sorted(os.listdir(item_dir))
        if not name.startswith(".")
        and name not in skip_names
        and os.path.isdir(os.path.join(item_dir, name))
    ]
    if len(candidates) == 1:
        return candidates[0]
    return None


def export_dir_for_item(item_dir: str, export_subdir: str = "document-validator") -> str:
    """返回 {item_dir}/{export_subdir}，与 project_name / configuration-test-case-generate 同级。"""
    return os.path.join(item_dir, export_subdir)
