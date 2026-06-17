#!/usr/bin/env python3
"""检查项目/条目是否出现在 UniPortal 共享卷中（虚拟测试 + 真实挂载诊断）。

用法:
  # 扫描共享卷里所有工程与 item
  python scripts/check_uniportal_item.py --mock local_workspaces/_mock_uniportal

  # 检查指定 item 是否在共享卷（门户 UUID）
  python scripts/check_uniportal_item.py --mock local_workspaces/_mock_uniportal \\
      --portal-project-id demo-project-uuid --item-id demo-item-uuid

  # 对比本地 export JSON 的 doc_id 能否同步到共享卷
  python scripts/check_uniportal_item.py --all-local

  # 创建虚拟共享卷目录树（本地联调）
  python scripts/check_uniportal_item.py --setup-mock local_workspaces/_mock_uniportal \\
      --portal-project-id my-proj-uuid --item-id my-item-uuid

  # Docker 容器内（已挂 uniportal_storage）
  docker exec reqcheck python scripts/check_uniportal_item.py --item-id <UUID> --portal-project-id <UUID>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config  # noqa: E402
from app.services.uniportal_paths import export_dir_for_item  # noqa: E402

DOC_EXTS = {".docx", ".md", ".markdown", ".txt"}


def _storage_path(mock: Optional[str]) -> Optional[str]:
    if mock:
        return os.path.abspath(mock)
    env = os.environ.get("UNIPORTAL_STORAGE_PATH", config.UNIPORTAL_STORAGE_PATH)
    return env or None


def _export_subdir() -> str:
    return os.environ.get("UNIPORTAL_EXPORT_SUBDIR", config.UNIPORTAL_EXPORT_SUBDIR)


def _export_filename() -> str:
    return os.environ.get("UNIPORTAL_EXPORT_FILENAME", config.UNIPORTAL_EXPORT_FILENAME)


def _local_dir() -> str:
    return os.environ.get("LOCAL_WORKSPACES_DIR", config.LOCAL_WORKSPACES_DIR)


def resolve_portal_project_id(
    storage: str,
    item_id: str,
    portal_project_id: Optional[str] = None,
) -> Optional[str]:
    if portal_project_id:
        candidate = Path(storage) / portal_project_id / item_id
        return portal_project_id if candidate.is_dir() else None

    root = Path(storage)
    if not root.is_dir():
        return None
    for portal_proj in sorted(root.iterdir()):
        if portal_proj.is_dir() and (portal_proj / item_id).is_dir():
            return portal_proj.name
    return None


def find_docs(item_dir: Path) -> list[str]:
    found: list[str] = []
    for path in item_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in DOC_EXTS and not path.name.startswith("."):
            found.append(str(path.relative_to(item_dir)))
    return sorted(found)[:5]


def _shared_export_files(export_dir: Path, export_filename: str) -> list[str]:
    if not export_dir.is_dir():
        return []
    files: list[str] = []
    primary = export_dir / export_filename
    if primary.is_file():
        files.append(export_filename)
    files.extend(
        name for name in sorted(f.name for f in export_dir.glob("export_*.json"))
        if name not in files
    )
    return files


def inspect_item(
    storage: Optional[str],
    item_id: str,
    portal_project_id: Optional[str] = None,
    export_subdir: str = "_reqcheck",
    export_filename: str = "requirement.json",
) -> dict:
    local_upload = Path(_local_dir()) / "uploads"
    local_export = Path(_local_dir()) / "export_results" / f"export_{item_id}.json"

    prefix = f"{item_id}_"
    local_upload_files = []
    if local_upload.is_dir():
        local_upload_files = [f.name for f in local_upload.iterdir() if f.is_file() and f.name.startswith(prefix)]

    result = {
        "item_id": item_id,
        "portal_project_id_hint": portal_project_id,
        "in_shared_volume": False,
        "in_local_upload": bool(local_upload_files),
        "local_upload_files": local_upload_files,
        "local_export_exists": local_export.is_file(),
        "local_export_path": str(local_export) if local_export.is_file() else None,
        "shared_item_dir": None,
        "shared_docs": [],
        "export_dir": None,
        "export_files": [],
        "export_sync_ready": False,
        "source_guess": "unknown",
        "verdict": "",
    }

    if not storage:
        result["verdict"] = "共享卷未配置（UNIPORTAL_STORAGE_PATH 未设置）"
        result["source_guess"] = "local" if result["in_local_upload"] else "unknown"
        return result

    storage_path = Path(storage)
    if not storage_path.is_dir():
        result["verdict"] = f"共享卷路径不存在: {storage}"
        result["source_guess"] = "local" if result["in_local_upload"] else "unknown"
        return result

    resolved_portal = resolve_portal_project_id(storage, item_id, portal_project_id)
    if not resolved_portal:
        result["verdict"] = "不在共享卷中（未找到 {portal_project_id}/{item_id}/ 目录）"
        result["source_guess"] = "local" if result["in_local_upload"] else "not_found"
        return result

    item_dir = storage_path / resolved_portal / item_id
    export_dir = Path(export_dir_for_item(str(item_dir), export_subdir))
    export_files = _shared_export_files(export_dir, export_filename)

    result.update(
        {
            "in_shared_volume": True,
            "portal_project_id": resolved_portal,
            "shared_item_dir": str(item_dir),
            "shared_docs": find_docs(item_dir),
            "export_dir": str(export_dir),
            "export_files": export_files,
            "export_sync_ready": True,
            "source_guess": "uniportal",
        }
    )

    if result["in_local_upload"]:
        result["source_guess"] = "both"
        result["verdict"] = "同时在共享卷与本地上传目录（本地上传优先解析）"
    elif export_files:
        result["verdict"] = "已在共享卷，且已有导出 JSON"
    else:
        result["verdict"] = "已在共享卷，导出目录可写入（尚未有 export JSON）"

    return result


def list_shared_items(storage: str, export_subdir: str, export_filename: str) -> list[dict]:
    root = Path(storage)
    if not root.is_dir():
        return []

    rows: list[dict] = []
    for portal_proj in sorted(root.iterdir()):
        if not portal_proj.is_dir() or portal_proj.name.startswith("."):
            continue
        for item_dir in sorted(portal_proj.iterdir()):
            if not item_dir.is_dir() or item_dir.name.startswith("."):
                continue
            export_dir = Path(export_dir_for_item(str(item_dir), export_subdir))
            exports = _shared_export_files(export_dir, export_filename)
            rows.append(
                {
                    "portal_project_id": portal_proj.name,
                    "item_id": item_dir.name,
                    "item_dir": str(item_dir),
                    "docs": find_docs(item_dir),
                    "export_files": exports,
                }
            )
    return rows


def list_local_doc_ids() -> list[str]:
    export_dir = Path(_local_dir()) / "export_results"
    if not export_dir.is_dir():
        return []
    return sorted(p.stem.replace("export_", "", 1) for p in export_dir.glob("export_*.json"))


def setup_mock(storage: str, portal_project_id: str, item_id: str, export_subdir: str, export_filename: str) -> dict:
    root = Path(storage)
    item_dir = root / portal_project_id / item_id
    export_dir = item_dir / export_subdir
    item_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)

    sample_doc = item_dir / "sample_requirements.docx"
    if not sample_doc.exists():
        sample_doc.write_bytes(b"PK mock docx for reqcheck volume test")

    sample_export = export_dir / export_filename
    if not sample_export.exists():
        sample_export.write_text("[]\n", encoding="utf-8")

    return {
        "created": True,
        "storage": str(root.resolve()),
        "item_dir": str(item_dir.resolve()),
        "export_dir": str(export_dir.resolve()),
        "sample_doc": str(sample_doc.resolve()),
        "sample_export": str(sample_export.resolve()),
    }


def probe_export_write(
    storage: str,
    item_id: str,
    portal_project_id: Optional[str],
    export_subdir: str,
    export_filename: str,
) -> dict:
    resolved = resolve_portal_project_id(storage, item_id, portal_project_id)
    if not resolved:
        return {"ok": False, "error": "item 不在共享卷，无法探针写入"}

    item_dir = Path(storage) / resolved / item_id
    export_dir = Path(export_dir_for_item(str(item_dir), export_subdir))
    probe_path = export_dir / f".probe_export_{datetime.now().strftime('%H%M%S')}.json"
    try:
        export_dir.mkdir(parents=True, exist_ok=True)
        probe_path.write_text('{"probe": true}\n', encoding="utf-8")
        ok = probe_path.exists()
        probe_path.unlink(missing_ok=True)
        return {
            "ok": ok,
            "export_dir": str(export_dir),
            "target_export": str(export_dir / export_filename),
        }
    except OSError as exc:
        return {"ok": False, "error": str(exc), "export_dir": str(export_dir)}


def _print_item(r: dict) -> None:
    print(f"  item_id              : {r['item_id']}")
    if r.get("portal_project_id"):
        print(f"  portal_project_id    : {r['portal_project_id']}")
    print(f"  在共享卷             : {'是' if r['in_shared_volume'] else '否'}")
    print(f"  在本地上传           : {'是' if r['in_local_upload'] else '否'}")
    print(f"  本地 export JSON     : {'有' if r['local_export_exists'] else '无'}")
    if r.get("shared_item_dir"):
        print(f"  共享卷 item 目录     : {r['shared_item_dir']}")
        print(f"  共享卷文档           : {', '.join(r['shared_docs']) or '(无)'}")
        print(f"  导出目录             : {r['export_dir']}")
        print(f"  已有 export JSON     : {', '.join(r['export_files']) or '(无)'}")
        print(f"  可自动同步导出       : {'是' if r['export_sync_ready'] else '否'}")
    print(f"  判定                 : {r['verdict']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="检查项目是否挂载在 UniPortal 共享卷")
    parser.add_argument("--mock", metavar="PATH", help="模拟共享卷根目录（覆盖 UNIPORTAL_STORAGE_PATH）")
    parser.add_argument("--portal-project-id", help="UniPortal 工程 UUID")
    parser.add_argument("--item-id", help="条目 UUID / doc_id")
    parser.add_argument("--all-local", action="store_true", help="检查本地 export_results 中所有 doc_id")
    parser.add_argument("--list", action="store_true", help="列出共享卷中全部 item")
    parser.add_argument("--setup-mock", metavar="PATH", help="创建虚拟共享卷目录树")
    parser.add_argument("--probe-export", action="store_true", help="向 _reqcheck 目录写入探针 JSON")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    export_subdir = _export_subdir()
    export_filename = _export_filename()
    storage = _storage_path(args.mock)

    if args.setup_mock:
        if not args.portal_project_id or not args.item_id:
            print("错误: --setup-mock 需同时指定 --portal-project-id 和 --item-id", file=sys.stderr)
            return 2
        info = setup_mock(
            args.setup_mock, args.portal_project_id, args.item_id, export_subdir, export_filename
        )
        if args.json:
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            print("已创建虚拟共享卷结构:")
            for k, v in info.items():
                print(f"  {k}: {v}")
            print("\n验证:")
            print(
                f"  python scripts/check_uniportal_item.py --mock {args.setup_mock} "
                f"--portal-project-id {args.portal_project_id} --item-id {args.item_id}"
            )
        return 0

    report: dict = {
        "timestamp": datetime.now().isoformat(),
        "in_docker": Path("/.dockerenv").exists(),
        "storage_path": storage,
        "storage_exists": bool(storage and Path(storage).is_dir()),
        "export_subdir": export_subdir,
        "export_filename": export_filename,
        "local_workspaces": _local_dir(),
    }

    if args.list:
        if not storage or not Path(storage).is_dir():
            report["items"] = []
            report["error"] = "共享卷不可用"
        else:
            report["items"] = list_shared_items(storage, export_subdir, export_filename)

        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report.get("items") is not None else 1

        print("=" * 60)
        print("UniPortal 共享卷 item 列表")
        print("=" * 60)
        print(f"共享卷: {storage or '(未设置)'}")
        items = report.get("items") or []
        if not items:
            print("(空或未挂载)")
        for row in items:
            docs = ", ".join(row["docs"]) or "(无文档)"
            exports = ", ".join(row["export_files"]) or "(无导出)"
            print(f"\n  [{row['portal_project_id']}] / {row['item_id']}")
            print(f"    文档: {docs}")
            print(f"    导出: {exports}")
        print("=" * 60)
        return 0

    item_ids: list[str] = []
    if args.all_local:
        item_ids = list_local_doc_ids()
        if not item_ids:
            print("local_workspaces/export_results/ 下没有 export_*.json", file=sys.stderr)
            return 1
    elif args.item_id:
        item_ids = [args.item_id]
    else:
        parser.print_help()
        return 2

    checks = [
        inspect_item(storage, iid, args.portal_project_id, export_subdir, export_filename)
        for iid in item_ids
    ]
    report["checks"] = checks

    if args.probe_export and storage and args.item_id:
        report["probe_export"] = probe_export_write(
            storage, args.item_id, args.portal_project_id, export_subdir, export_filename
        )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print("=" * 60)
    print("UniPortal 共享卷 item 检查")
    print("=" * 60)
    print(f"Docker 容器   : {'是' if report['in_docker'] else '否'}")
    print(f"共享卷路径    : {storage or '(未设置)'}")
    print(f"共享卷可访问  : {'是' if report['storage_exists'] else '否'}")
    print(f"本地工作区    : {report['local_workspaces']}")

    for r in checks:
        print("\n--- 检查条目 ---")
        _print_item(r)

    if report.get("probe_export"):
        pe = report["probe_export"]
        print("\n--- 导出目录写探针 ---")
        if pe.get("ok"):
            print(f"  [OK] 可写入 {pe['export_dir']}")
            print(f"  正式路径: {pe['target_export']}")
        else:
            print(f"  [FAIL] {pe.get('error', '写入失败')}")

    print("\n--- 说明 ---")
    print("  in_shared_volume=是  -> 门户上传的项目，ReqCheck 可从共享卷读取")
    print(f"  export_sync_ready=是 -> 调用 /api/export 时会写入 {export_subdir}/{export_filename}")
    print("  本地上传 doc_id 为文件哈希，通常不在共享卷，需从门户跳转使用 item UUID")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
