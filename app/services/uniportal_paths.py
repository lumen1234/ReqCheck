"""UniPortal 共享卷路径：document-validator 与主文档同层。"""
from __future__ import annotations

import os
from typing import Optional

_DEFAULT_ALLOWED = frozenset({"txt", "docx", "md", "markdown"})
_DOC_PRIORITY = (".docx", ".md", ".markdown", ".txt")


def find_primary_document(
    root: str,
    *,
    skip_subdir: str = "document-validator",
    allowed_extensions: Optional[frozenset[str]] = None,
) -> Optional[str]:
    if not root or not os.path.isdir(root):
        return None

    allowed = allowed_extensions or _DEFAULT_ALLOWED
    found: list[tuple[int, str]] = []

    for dirpath, dirnames, filenames in os.walk(root):
        if skip_subdir:
            dirnames[:] = [d for d in dirnames if d != skip_subdir and not d.startswith(".")]
        for name in filenames:
            if name.startswith("."):
                continue
            ext = os.path.splitext(name)[1].lower().lstrip(".")
            if ext not in allowed:
                continue
            full = os.path.join(dirpath, name)
            ext_dot = f".{ext}"
            prio = _DOC_PRIORITY.index(ext_dot) if ext_dot in _DOC_PRIORITY else len(_DOC_PRIORITY)
            found.append((prio, full))

    if not found:
        return None
    found.sort(key=lambda x: (x[0], x[1]))
    return found[0][1]


def export_parent_dir(item_dir: str, export_subdir: str = "document-validator") -> str:
    doc_path = find_primary_document(item_dir, skip_subdir=export_subdir)
    if doc_path:
        return os.path.dirname(doc_path)
    return item_dir


def export_dir_for_item(item_dir: str, export_subdir: str = "document-validator") -> str:
    return os.path.join(export_parent_dir(item_dir, export_subdir), export_subdir)
