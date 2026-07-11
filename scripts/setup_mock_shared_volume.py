#!/usr/bin/env python3
"""创建本地虚拟 UniPortal 共享卷并测试导出路径。

目标层级：
  {portal_project_id}/{project_id}/
    ├── {project_name}/src/...
    ├── configuration-test-case-generate/
    └── document-validator/requirement.json

用法:
  python scripts/setup_mock_shared_volume.py
  python scripts/setup_mock_shared_volume.py --mock local_workspaces/_mock_uniportal
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import config  # noqa: E402
from app import app  # noqa: E402
from app.services import project_service  # noqa: E402
from app.services.uniportal_paths import export_dir_for_item  # noqa: E402


PORTAL_ID = "demo-portal-uuid"
ITEM_ID = "demo-item-uuid"
CONTENT_DIR = "MEMS陀螺软件-new"
DOC_NAME = "MEMS陀螺软件需求规格说明_新.docx"
OTHER_TOOL_DIR = "configuration-test-case-generate"


def create_mock_tree(storage: Path) -> dict:
    """模拟：{portal}/{item}/{project_name}/docx，导出应落在 item 根下。"""
    item_dir = storage / PORTAL_ID / ITEM_ID
    content_dir = item_dir / CONTENT_DIR
    src_dir = content_dir / "src"
    other_tool = item_dir / OTHER_TOOL_DIR
    src_dir.mkdir(parents=True, exist_ok=True)
    other_tool.mkdir(parents=True, exist_ok=True)

    doc = content_dir / DOC_NAME
    if not doc.exists():
        doc.write_bytes(b"PK mock docx")

    return {
        "storage": str(storage.resolve()),
        "item_dir": str(item_dir.resolve()),
        "content_dir": str(content_dir.resolve()),
        "doc": str(doc.resolve()),
    }


def run_export_test(storage: str) -> dict:
    app.config["UNIPORTAL_STORAGE_PATH"] = storage
    sample = [{"id": "req1", "title": "测试需求", "content": "mock"}]

    with app.app_context():
        export_dir = project_service.get_uniportal_export_dir(ITEM_ID, portal_project_id=PORTAL_ID)
        export_path = project_service.sync_export_to_uniportal(
            ITEM_ID,
            sample,
            portal_project_id=PORTAL_ID,
        )

    item_dir = Path(storage) / PORTAL_ID / ITEM_ID
    expected_dir = export_dir_for_item(str(item_dir), config.UNIPORTAL_EXPORT_SUBDIR)
    expected_file = str(Path(expected_dir) / config.UNIPORTAL_EXPORT_FILENAME)

    ok = export_path == expected_file and Path(export_path).is_file()
    # 导出必须在 item 根下，不能嵌进 project_name
    at_item_root = (
        export_dir is not None
        and Path(export_dir).parent == item_dir.resolve()
        and CONTENT_DIR not in Path(export_dir).parts
    )
    return {
        "export_dir": export_dir,
        "export_path": export_path,
        "expected_dir": expected_dir,
        "expected_file": expected_file,
        "ok": ok and at_item_root,
        "at_item_root": at_item_root,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="本地虚拟共享卷 + 导出路径测试")
    parser.add_argument(
        "--mock",
        default=str(BASE / "local_workspaces" / "_mock_uniportal"),
        help="虚拟共享卷根目录",
    )
    args = parser.parse_args()

    storage = Path(args.mock)
    info = create_mock_tree(storage)
    result = run_export_test(str(storage))

    print("=" * 60)
    print("本地虚拟 UniPortal 共享卷")
    print("=" * 60)
    print(f"共享卷根目录   : {info['storage']}")
    print(f"item 目录      : {info['item_dir']}")
    print(f"内容目录       : {info['content_dir']}")
    print(f"主文档         : {info['doc']}")
    print()
    print("目录树:")
    print(f"  {PORTAL_ID}/")
    print(f"    {ITEM_ID}/")
    print(f"      {CONTENT_DIR}/")
    print(f"        src/")
    print(f"        {DOC_NAME}")
    print(f"      {OTHER_TOOL_DIR}/")
    print(f"      document-validator/")
    print(f"        {config.UNIPORTAL_EXPORT_FILENAME}")
    print()
    print("导出测试结果:")
    print(f"  导出目录     : {result['export_dir']}")
    print(f"  导出文件     : {result['export_path']}")
    print(f"  在 item 根下 : {'是' if result['at_item_root'] else '否'}")
    print(f"  测试         : {'PASS' if result['ok'] else 'FAIL'}")
    print("=" * 60)
    print()
    print("后续命令:")
    print(f"  python scripts/check_uniportal_item.py --mock {storage} \\")
    print(f"    --portal-project-id {PORTAL_ID} --item-id {ITEM_ID}")
    print(f"  python scripts/verify_uniportal_integration.py --mock {storage}")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
