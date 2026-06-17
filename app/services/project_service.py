"""UniPortal 双数据源：共享卷读写（导出 JSON）+ 私有卷读写。"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Optional

from flask import current_app

from app.services.uniportal_paths import export_dir_for_item, find_primary_document


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


@dataclass
class ResolvedDocument:
    project_id: str
    filepath: str
    filename: str
    source: str
    file_type: str = "other"


def _allowed_extensions() -> set[str]:
    return current_app.config.get("ALLOWED_EXTENSIONS", {"txt", "docx", "md", "markdown"})


def uniportal_storage_path() -> Optional[str]:
    path = current_app.config.get("UNIPORTAL_STORAGE_PATH")
    if path and os.path.isdir(path):
        return path
    return None


def local_workspaces_dir() -> str:
    return current_app.config["LOCAL_WORKSPACES_DIR"]


def upload_folder() -> str:
    return current_app.config["UPLOAD_FOLDER"]


def is_uniportal_item(project_id: str) -> bool:
    """item 仅存在于共享卷（不在本地上传目录）。"""
    storage = uniportal_storage_path()
    if not storage:
        return False
    if _local_upload_path(project_id):
        return False
    return resolve_project_dir(project_id) is not None


def resolve_portal_project_id_for_item(
    item_id: str,
    portal_project_id: Optional[str] = None,
) -> Optional[str]:
    """解析 item_id 所属的 UniPortal 工程 UUID。"""
    storage = uniportal_storage_path()
    if not storage:
        return None

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
    """返回共享卷导出目录：与主文档同层（如 MEMS陀螺软件-new/document-validator/）。"""
    item_dir = resolve_project_dir(item_id, portal_project_id=portal_project_id)
    storage = uniportal_storage_path()
    if not item_dir or not storage:
        return None
    item_dir = os.path.normpath(item_dir)
    storage = os.path.normpath(storage)
    if not item_dir.startswith(storage):
        return None
    subdir = current_app.config.get("UNIPORTAL_EXPORT_SUBDIR", "document-validator")
    return export_dir_for_item(item_dir, subdir)


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
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if not name.startswith("."):
                count += 1
    return count


def _pick_display_name(item_dir: str, project_id: str) -> str:
    doc = find_document_file(item_dir)
    if doc:
        return os.path.basename(doc)
    return project_id


def find_document_file(root: str) -> Optional[str]:
    """在目录树中找第一个支持的文档文件，优先 docx > md > txt。"""
    subdir = current_app.config.get("UNIPORTAL_EXPORT_SUBDIR", "document-validator")
    allowed = frozenset(_allowed_extensions())
    return find_primary_document(root, skip_subdir=subdir, allowed_extensions=allowed)


def resolve_document(project_id: str, portal_project_id: Optional[str] = None) -> Optional[ResolvedDocument]:
    """先私有上传文件，再 UniPortal item 目录。"""
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

    item_dir = resolve_project_dir(project_id, portal_project_id=portal_project_id)
    if not item_dir:
        return None

    doc_path = find_document_file(item_dir)
    if not doc_path:
        return None

    filename = os.path.basename(doc_path)
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    return ResolvedDocument(
        project_id=project_id,
        filepath=doc_path,
        filename=filename,
        source="uniportal",
        file_type=ext or "other",
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
        mtime = datetime.fromtimestamp(os.path.getmtime(item_dir)).isoformat()
        items.append(
            ProjectEntry(
                project_id=item_id,
                project_name=_pick_display_name(item_dir, item_id),
                file_count=_count_files(item_dir),
                status="available",
                source="uniportal",
                upload_time=mtime,
                file_type="uniportal",
                file_path=item_dir,
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
    return {
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
