"""UniPortal 双数据源：共享卷读写（导出 JSON）+ 私有卷读写。"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from flask import current_app

from app.services.uniportal_paths import (
    export_dir_for_item,
    find_all_documents,
    find_primary_document,
    pick_project_content_name,
)

# 多文档 item 的子文档 ID：{item_id}--{md5(relpath)[:12]}
_SUBDOC_SEP = "--"


@dataclass
class ProjectEntry:
    project_id: str
    project_name: str
    file_count: int
    status: str
    source: str  # "local" | "uniportal"
    upload_time: Optional[str] = None
    file_type: Optional[str] = None
    file_path: Optional[str] = None
    kind: Optional[str] = None  # "batch" | None


@dataclass
class ResolvedDocument:
    project_id: str
    filepath: str
    filename: str
    source: str
    file_type: str = "other"
    relative_path: Optional[str] = None
    item_id: Optional[str] = None


@dataclass
class ItemDocumentEntry:
    """共享卷 item 内的单个文档（用于虚拟 batch）。"""
    doc_id: str
    item_id: str
    filename: str
    relative_path: str
    filepath: str
    file_type: str
    batch_order: int


def _allowed_extensions() -> set[str]:
    return current_app.config.get("ALLOWED_EXTENSIONS", {"txt", "docx", "md", "markdown"})


def _export_subdir() -> str:
    return current_app.config.get("UNIPORTAL_EXPORT_SUBDIR", "document-validator")


def uniportal_storage_path() -> Optional[str]:
    path = current_app.config.get("UNIPORTAL_STORAGE_PATH")
    if path and os.path.isdir(path):
        return path
    return None


def local_workspaces_dir() -> str:
    return current_app.config["LOCAL_WORKSPACES_DIR"]


def upload_folder() -> str:
    return current_app.config["UPLOAD_FOLDER"]


def _relpath_key(item_dir: str, filepath: str) -> str:
    return os.path.relpath(filepath, item_dir).replace("\\", "/")


def make_subdoc_id(item_id: str, relative_path: str) -> str:
    rel = relative_path.replace("\\", "/")
    digest = hashlib.md5(rel.encode("utf-8")).hexdigest()[:12]
    return f"{item_id}{_SUBDOC_SEP}{digest}"


def parse_subdoc_id(doc_id: str) -> Optional[tuple[str, str]]:
    """解析子文档 ID，返回 (item_id, path_digest) 或 None。"""
    if _SUBDOC_SEP not in doc_id:
        return None
    item_id, digest = doc_id.rsplit(_SUBDOC_SEP, 1)
    if not item_id or len(digest) != 12:
        return None
    return item_id, digest


def is_uniportal_item(project_id: str) -> bool:
    """item 仅存在于共享卷（不在本地上传目录）。"""
    storage = uniportal_storage_path()
    if not storage:
        return False
    if _local_upload_path(project_id):
        return False
    item_id = parse_subdoc_id(project_id)[0] if parse_subdoc_id(project_id) else project_id
    return resolve_project_dir(item_id) is not None


def resolve_portal_project_id_for_item(
    item_id: str,
    portal_project_id: Optional[str] = None,
) -> Optional[str]:
    """解析 item_id 所属的 UniPortal 工程 UUID。"""
    storage = uniportal_storage_path()
    if not storage:
        return None

    parsed = parse_subdoc_id(item_id)
    if parsed:
        item_id = parsed[0]

    if portal_project_id:
        candidate = os.path.join(storage, portal_project_id, item_id)
        if os.path.isdir(candidate):
            return portal_project_id
        return None

    for portal_proj in os.listdir(storage):
        portal_path = os.path.join(storage, portal_proj)
        if not os.path.isdir(portal_path):
            continue
        if os.path.isdir(os.path.join(portal_path, item_id)):
            return portal_proj
    return None


def get_uniportal_export_dir(
    item_id: str,
    portal_project_id: Optional[str] = None,
) -> Optional[str]:
    """返回共享卷导出目录：挂在 item 根下，与 project_name 同级（如 {item_id}/document-validator/）。"""
    parsed = parse_subdoc_id(item_id)
    if parsed:
        item_id = parsed[0]
    item_dir = resolve_project_dir(item_id, portal_project_id=portal_project_id)
    storage = uniportal_storage_path()
    if not item_dir or not storage:
        return None
    item_dir = os.path.normpath(item_dir)
    storage = os.path.normpath(storage)
    if not item_dir.startswith(storage):
        return None
    return export_dir_for_item(item_dir, _export_subdir())


def uniportal_export_filename() -> str:
    return current_app.config.get("UNIPORTAL_EXPORT_FILENAME", "requirement.json")


def sync_export_to_uniportal(
    item_id: str,
    requirements: list[dict[str, Any]],
    portal_project_id: Optional[str] = None,
) -> Optional[str]:
    """将导出 JSON 同步写入共享卷；非 UniPortal item 或卷不可写时返回 None。"""
    export_dir = get_uniportal_export_dir(item_id, portal_project_id)
    if not export_dir:
        return None

    try:
        os.makedirs(export_dir, exist_ok=True)
        export_path = os.path.join(export_dir, uniportal_export_filename())
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(requirements, f, ensure_ascii=False, indent=2)
        return export_path
    except OSError as exc:
        current_app.logger.warning("共享卷导出失败: %s", exc)
        return None


def resolve_project_dir(project_id: str, portal_project_id: Optional[str] = None) -> Optional[str]:
    """返回 project_id 对应目录（UniPortal item 目录）。

    读路径解析顺序（与 SUBTOOL_INTEGRATION_GUIDE §4.2 一致）：
    1. 私有卷 local_workspaces/{project_id}（若存在）
    2. 共享卷 /data/uniportal/{portal_project_id}/{project_id}（若指定工程 ID）
    3. 共享卷全工程扫描（未指定 portal_project_id 时，用于 item_id 全局定位）
    """
    parsed = parse_subdoc_id(project_id)
    if parsed:
        project_id = parsed[0]

    local_item = os.path.join(local_workspaces_dir(), project_id)
    if os.path.isdir(local_item):
        return local_item

    storage = uniportal_storage_path()
    if not storage:
        return None

    if portal_project_id:
        candidate = os.path.join(storage, portal_project_id, project_id)
        if os.path.isdir(candidate):
            return candidate
        return None

    for portal_proj in os.listdir(storage):
        portal_path = os.path.join(storage, portal_proj)
        if not os.path.isdir(portal_path):
            continue
        candidate = os.path.join(portal_path, project_id)
        if os.path.isdir(candidate):
            return candidate
    return None


def _local_upload_path(project_id: str) -> Optional[str]:
    folder = upload_folder()
    if not os.path.isdir(folder):
        return None
    prefix = f"{project_id}_"
    for name in os.listdir(folder):
        if name.startswith(prefix):
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path
    return None


def _count_files(root: str) -> int:
    count = 0
    skip = {_export_subdir(), "configuration-test-case-generate"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".")]
        for name in filenames:
            if not name.startswith("."):
                count += 1
    return count


def list_item_documents(
    item_id: str,
    portal_project_id: Optional[str] = None,
) -> list[ItemDocumentEntry]:
    """扫描共享卷 item 目录下全部支持的需求文档（跳过子工具输出目录）。"""
    item_dir = resolve_project_dir(item_id, portal_project_id=portal_project_id)
    if not item_dir:
        return []

    allowed = frozenset(_allowed_extensions())
    docs = find_all_documents(item_dir, skip_subdir=_export_subdir(), allowed_extensions=allowed)
    multi = len(docs) > 1
    entries: list[ItemDocumentEntry] = []
    for order, filepath in enumerate(docs, start=1):
        rel = _relpath_key(item_dir, filepath)
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        # 多文档用稳定子 ID；单文档仍用 item_id（兼容 UniPortal 深链）
        doc_id = make_subdoc_id(item_id, rel) if multi else item_id
        entries.append(
            ItemDocumentEntry(
                doc_id=doc_id,
                item_id=item_id,
                filename=filename,
                relative_path=rel,
                filepath=filepath,
                file_type=ext or "other",
                batch_order=order,
            )
        )
    return entries


def get_uniportal_batch_detail(
    item_id: str,
    portal_project_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """将共享卷 item 映射为与本地 batch 兼容的详情结构。"""
    item_dir = resolve_project_dir(item_id, portal_project_id=portal_project_id)
    if not item_dir:
        return None

    docs = list_item_documents(item_id, portal_project_id=portal_project_id)
    if not docs:
        return None

    batch_name = _pick_display_name(item_dir, item_id)
    mtime = datetime.fromtimestamp(os.path.getmtime(item_dir)).isoformat()
    return {
        "batch_id": item_id,
        "doc_id": item_id,
        "batch_name": batch_name,
        "filename": batch_name,
        "status": "available",
        "upload_time": mtime,
        "doc_count": len(docs),
        "documents": [
            {
                "doc": d.batch_order,
                "doc_id": d.doc_id,
                "id": d.doc_id,
                "filename": d.filename,
                "relative_path": d.relative_path,
                "file_type": d.file_type,
                "status": "available",
                "upload_time": mtime,
                "source": "uniportal",
                "file_path": d.filepath,
            }
            for d in docs
        ],
        "source": "uniportal",
        "kind": "batch",
        "file_path": item_dir,
    }


def _pick_display_name(item_dir: str, project_id: str) -> str:
    folder_name = pick_project_content_name(item_dir, skip_subdir=_export_subdir())
    if folder_name:
        return folder_name
    docs = list_item_documents(project_id)
    if len(docs) == 1:
        return docs[0].filename
    if docs:
        return docs[0].filename
    return project_id


def find_document_file(root: str) -> Optional[str]:
    """在目录树中找第一个支持的文档文件，优先 docx > md > txt。"""
    allowed = frozenset(_allowed_extensions())
    return find_primary_document(root, skip_subdir=_export_subdir(), allowed_extensions=allowed)


def resolve_document(project_id: str, portal_project_id: Optional[str] = None) -> Optional[ResolvedDocument]:
    """先私有上传文件，再 UniPortal item 目录（支持多文档子 ID）。"""
    local_file = _local_upload_path(project_id)
    if local_file:
        filename = local_file.split(f"{project_id}_", 1)[-1] if f"{project_id}_" in os.path.basename(local_file) else os.path.basename(local_file)
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        return ResolvedDocument(
            project_id=project_id,
            filepath=local_file,
            filename=filename,
            source="local",
            file_type=ext or "other",
        )

    sub = parse_subdoc_id(project_id)
    if sub:
        item_id, _digest = sub
        for entry in list_item_documents(item_id, portal_project_id=portal_project_id):
            if make_subdoc_id(item_id, entry.relative_path) == project_id:
                return ResolvedDocument(
                    project_id=project_id,
                    filepath=entry.filepath,
                    filename=entry.filename,
                    source="uniportal",
                    file_type=entry.file_type,
                    relative_path=entry.relative_path,
                    item_id=item_id,
                )
        return None

    item_dir = resolve_project_dir(project_id, portal_project_id=portal_project_id)
    if not item_dir:
        return None

    docs = list_item_documents(project_id, portal_project_id=portal_project_id)
    if not docs:
        return None

    # 单文档：直接用；多文档且用 item_id 访问时取第一篇（兼容旧深链）
    entry = docs[0]
    return ResolvedDocument(
        project_id=project_id,
        filepath=entry.filepath,
        filename=entry.filename,
        source="uniportal",
        file_type=entry.file_type,
        relative_path=entry.relative_path,
        item_id=project_id,
    )


def _scan_uniportal_items(portal_project_id: str) -> list[ProjectEntry]:
    storage = uniportal_storage_path()
    if not storage:
        return []

    proj_path = os.path.join(storage, portal_project_id)
    if not os.path.isdir(proj_path):
        return []

    items: list[ProjectEntry] = []
    for item_id in sorted(os.listdir(proj_path)):
        item_dir = os.path.join(proj_path, item_id)
        if not os.path.isdir(item_dir):
            continue
        docs = list_item_documents(item_id, portal_project_id=portal_project_id)
        doc_count = len(docs)
        mtime = datetime.fromtimestamp(os.path.getmtime(item_dir)).isoformat()
        is_batch = doc_count > 1
        items.append(
            ProjectEntry(
                project_id=item_id,
                project_name=_pick_display_name(item_dir, item_id),
                file_count=doc_count if doc_count else _count_files(item_dir),
                status="available",
                source="uniportal",
                upload_time=mtime,
                file_type="folder" if is_batch else "uniportal",
                file_path=item_dir,
                kind="batch" if is_batch else None,
            )
        )
    return items


def list_projects(portal_project_id: Optional[str] = None) -> list[ProjectEntry]:
    """合并 UniPortal（按工程隔离）+ 本地上传列表。

    工程隔离（SUBTOOL_INTEGRATION_GUIDE §4.3）：
    - 传入 portal_project_id：扫描共享卷该工程下 item + 全部本地上传
    - 未传 portal_project_id：仅本地上传（不暴露 UniPortal 项目，防跨工程泄露）
    """
    from app.models import Document

    items: list[ProjectEntry] = []

    if portal_project_id:
        items.extend(_scan_uniportal_items(portal_project_id))

    for doc in Document.query.order_by(Document.upload_time.desc()).all():
        items.append(
            ProjectEntry(
                project_id=doc.id,
                project_name=doc.filename,
                file_count=1,
                status=doc.status or "已上传",
                source="local",
                upload_time=doc.upload_time.isoformat() if doc.upload_time else None,
                file_type=doc.file_type,
                file_path=doc.file_path,
            )
        )

    return items


def project_entry_to_dict(entry: ProjectEntry) -> dict:
    payload = {
        "id": entry.project_id,
        "doc_id": entry.project_id,
        "filename": entry.project_name,
        "project_name": entry.project_name,
        "file_count": entry.file_count,
        "status": entry.status,
        "source": entry.source,
        "upload_time": entry.upload_time,
        "file_type": entry.file_type,
        "file_path": entry.file_path,
    }
    if entry.kind:
        payload["kind"] = entry.kind
    return payload
