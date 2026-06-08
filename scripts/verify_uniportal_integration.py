#!/usr/bin/env python3
"""UniPortal 双数据源集成验证（对照 SUBTOOL_INTEGRATION_GUIDE §七）。

用法:
  python scripts/verify_uniportal_integration.py
  python scripts/verify_uniportal_integration.py --mock local_workspaces/_mock_uniportal
  docker exec reqcheck python scripts/verify_uniportal_integration.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config  # noqa: E402


def check(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "ok": ok, "detail": detail}


def main() -> int:
    parser = argparse.ArgumentParser(description="UniPortal 集成验证清单")
    parser.add_argument("--mock", metavar="PATH", help="模拟 UNIPORTAL_STORAGE_PATH")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    local_dir = os.environ.get("LOCAL_WORKSPACES_DIR", config.LOCAL_WORKSPACES_DIR)
    uniportal = args.mock or os.environ.get("UNIPORTAL_STORAGE_PATH") or config.UNIPORTAL_STORAGE_PATH
    in_docker = Path("/.dockerenv").exists()

    results: list[dict] = []

    # 1. 环境变量
    results.append(
        check(
            "UNIPORTAL_STORAGE_PATH 已配置",
            bool(uniportal),
            uniportal or "(未设置，独立模式)",
        )
    )
    results.append(
        check(
            "LOCAL_WORKSPACES_DIR 可访问",
            Path(local_dir).is_dir(),
            local_dir,
        )
    )

    # 2. 共享卷可读
    up = Path(uniportal) if uniportal else None
    results.append(
        check(
            "共享卷目录存在",
            bool(up and up.is_dir()),
            str(up) if up else "N/A",
        )
    )

    # 3. 私有工作区可写
    probe = Path(local_dir) / ".verify_probe"
    writable_local = False
    try:
        probe.write_text("ok", encoding="utf-8")
        writable_local = probe.read_text(encoding="utf-8") == "ok"
        probe.unlink(missing_ok=True)
    except OSError as exc:
        results.append(check("私有工作区可写", False, str(exc)))
    else:
        results.append(check("私有工作区可写", writable_local, local_dir))

    # 4. 共享卷扫描（工程隔离结构）
    portal_projects: list[str] = []
    if up and up.is_dir():
        portal_projects = sorted(
            p.name for p in up.iterdir() if p.is_dir() and not p.name.startswith(".")
        )
    results.append(
        check(
            "共享卷含 portal 工程目录",
            len(portal_projects) > 0,
            ", ".join(portal_projects[:5]) or "(空，门户尚未上传项目)",
        )
    )

    # 5. 子目录约定
    subdirs = ("uploads", "parse_results", "parse_assets", "validate_results", "export_results")
    missing = [d for d in subdirs if not (Path(local_dir) / d).is_dir()]
    results.append(
        check(
            "私有工作区子目录齐全",
            len(missing) == 0,
            f"缺少: {missing}" if missing else "OK",
        )
    )

    # 6. Docker 提示
    if in_docker:
        results.append(check("运行在 Docker 容器内", True, ""))
    else:
        results.append(
            check(
                "运行在 Docker 容器内",
                False,
                "本地 python run.py 为独立模式；生产请 docker compose up",
            )
        )

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    report = {
        "passed": passed,
        "total": total,
        "all_ok": passed == total,
        "in_docker": in_docker,
        "uniportal_path": uniportal,
        "local_workspaces": local_dir,
        "portal_projects": portal_projects,
        "checks": results,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["all_ok"] else 1

    print("=" * 60)
    print("UniPortal 集成验证")
    print("=" * 60)
    for r in results:
        mark = "PASS" if r["ok"] else "FAIL"
        line = f"  [{mark}] {r['name']}"
        if r["detail"]:
            line += f"  —  {r['detail']}"
        print(line)
    print("-" * 60)
    print(f"通过 {passed}/{total}")
    if not uniportal:
        print("\n提示: 独立开发模式正常；对接门户请挂载 uniportal_storage 并设置 UNIPORTAL_STORAGE_PATH")
    elif not portal_projects:
        print("\n提示: 共享卷为空，请在 UniPortal 上传项目后再测列表/解析")
    print("=" * 60)
    return 0 if passed >= 4 else 1  # 空共享卷在联调初期允许部分 FAIL


if __name__ == "__main__":
    raise SystemExit(main())
