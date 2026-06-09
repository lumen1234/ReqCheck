#!/usr/bin/env python3
"""诊断 ReqCheck 共享卷 / 私有工作区挂载情况。

用法:
  python scripts/check_volumes.py              # 读取当前环境变量
  python scripts/check_volumes.py --probe      # 额外写入探针文件测读写
  python scripts/check_volumes.py --mock D:/uniportal_data   # 本地模拟共享卷路径
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config  # noqa: E402


def _status(ok: bool) -> str:
    return "OK" if ok else "FAIL"


def _dir_summary(path: str, max_entries: int = 8) -> dict:
    p = Path(path)
    if not p.is_dir():
        return {"exists": False, "entries": []}
    entries = []
    try:
        names = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        for item in names[:max_entries]:
            kind = "dir" if item.is_dir() else "file"
            try:
                size = item.stat().st_size if item.is_file() else None
            except OSError:
                size = None
            entries.append({"name": item.name, "type": kind, "size": size})
        extra = max(0, len(names) - max_entries)
    except OSError as exc:
        return {"exists": True, "error": str(exc), "entries": []}
    return {"exists": True, "entry_count": len(names), "shown": len(entries), "extra": extra, "entries": entries}


def _writable_probe(path: str, label: str) -> dict:
    p = Path(path)
    result = {"label": label, "path": path, "can_write": False}
    if not p.is_dir():
        result["error"] = "目录不存在"
        return result
    probe_dir = p / ".reqcheck_probe"
    probe_file = probe_dir / f"probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        probe_dir.mkdir(parents=True, exist_ok=True)
        probe_file.write_text(f"probe at {datetime.now().isoformat()}\n", encoding="utf-8")
        content = probe_file.read_text(encoding="utf-8")
        probe_file.unlink(missing_ok=True)
        if probe_dir.exists() and not any(probe_dir.iterdir()):
            probe_dir.rmdir()
        result["can_write"] = bool(content)
    except OSError as exc:
        result["error"] = str(exc)
    return result


def _scan_uniportal(storage: str, export_subdir: str, export_filename: str) -> dict:
    root = Path(storage)
    if not root.is_dir():
        return {"projects": []}

    projects = []
    for portal_proj in sorted(root.iterdir()):
        if not portal_proj.is_dir() or portal_proj.name.startswith("."):
            continue
        items = []
        for item_dir in sorted(portal_proj.iterdir()):
            if not item_dir.is_dir() or item_dir.name.startswith("."):
                continue
            export_dir = item_dir / export_subdir
            exports = []
            if export_dir.is_dir():
                primary = export_dir / export_filename
                if primary.is_file():
                    exports.append(export_filename)
                exports.extend(
                    name for name in sorted(f.name for f in export_dir.glob("export_*.json"))
                    if name not in exports
                )
            doc_files = []
            for pattern in ("*.docx", "*.md", "*.txt"):
                doc_files.extend(f.name for f in item_dir.rglob(pattern))
            items.append(
                {
                    "item_id": item_dir.name,
                    "export_dir": str(export_dir),
                    "export_files": exports,
                    "doc_files": doc_files[:3],
                }
            )
        projects.append({"portal_project_id": portal_proj.name, "item_count": len(items), "items": items[:5]})
    return {"projects": projects}


def _local_workspaces_report(base: str) -> dict:
    subdirs = ("uploads", "parse_results", "parse_assets", "validate_results", "export_results")
    report = {"root": base, "subdirs": {}}
    for name in subdirs:
        path = os.path.join(base, name)
        summary = _dir_summary(path)
        if summary.get("exists"):
            if name == "export_results":
                summary["export_json_count"] = len(list(Path(path).glob("export_*.json")))
            if name == "parse_results":
                summary["parse_json_count"] = len(list(Path(path).glob("*.json"))) - (
                    1 if (Path(path) / "cache_index.json").exists() else 0
                )
        report["subdirs"][name] = summary
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="ReqCheck 共享卷 / 工作区诊断")
    parser.add_argument("--probe", action="store_true", help="写入探针文件测试读写权限")
    parser.add_argument("--mock", metavar="PATH", help="临时覆盖 UNIPORTAL_STORAGE_PATH（本地模拟 Docker 共享卷）")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = parser.parse_args()

    local_dir = os.environ.get("LOCAL_WORKSPACES_DIR", config.LOCAL_WORKSPACES_DIR)
    uniportal = args.mock or os.environ.get("UNIPORTAL_STORAGE_PATH", config.UNIPORTAL_STORAGE_PATH)
    export_subdir = os.environ.get("UNIPORTAL_EXPORT_SUBDIR", config.UNIPORTAL_EXPORT_SUBDIR)
    export_filename = os.environ.get("UNIPORTAL_EXPORT_FILENAME", config.UNIPORTAL_EXPORT_FILENAME)

    mode = "uniportal" if uniportal else "standalone"
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "environment": {
            "LOCAL_WORKSPACES_DIR": local_dir,
            "UNIPORTAL_STORAGE_PATH": uniportal,
            "UNIPORTAL_EXPORT_SUBDIR": export_subdir,
            "UNIPORTAL_EXPORT_FILENAME": export_filename,
            "cwd": os.getcwd(),
            "in_docker": Path("/.dockerenv").exists(),
        },
        "local_workspaces": _local_workspaces_report(local_dir),
        "uniportal": None,
        "probes": [],
    }

    if uniportal:
        up = Path(uniportal)
        report["uniportal"] = {
            "path": uniportal,
            "exists": up.is_dir(),
            "is_mock": bool(args.mock),
            "scan": _scan_uniportal(uniportal, export_subdir, export_filename),
        }

    if args.probe:
        report["probes"].append(_writable_probe(local_dir, "local_workspaces"))
        if uniportal:
            report["probes"].append(_writable_probe(uniportal, "uniportal_storage"))

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print("=" * 60)
    print("ReqCheck 卷 / 工作区诊断")
    print("=" * 60)
    print(f"运行模式     : {'UniPortal 集成' if mode == 'uniportal' else '独立模式（无共享卷）'}")
    print(f"Docker 容器  : {'是' if report['environment']['in_docker'] else '否'}")
    print(f"私有工作区   : {local_dir}  [{_status(Path(local_dir).is_dir())}]")
    print(f"共享卷路径   : {uniportal or '(未设置)'}")
    if uniportal:
        print(f"  存在       : {_status(Path(uniportal).is_dir())}" + (" [mock]" if args.mock else ""))
        print(f"  共享卷导出   : {export_subdir}/{export_filename}")

    print("\n--- 私有工作区子目录 ---")
    for name, info in report["local_workspaces"]["subdirs"].items():
        if not info.get("exists"):
            print(f"  {name:18s} (不存在)")
            continue
        extra = info.get("extra", 0)
        suffix = ""
        if "export_json_count" in info:
            suffix = f", export JSON: {info['export_json_count']}"
        elif "parse_json_count" in info:
            suffix = f", parse JSON: {info['parse_json_count']}"
        print(f"  {name:18s} {info.get('entry_count', 0)} 项{suffix}" + (f" (+{extra} 未显示)" if extra else ""))
        for ent in info.get("entries", [])[:4]:
            tag = "[dir]" if ent["type"] == "dir" else "[file]"
            size = f" ({ent['size']} B)" if ent.get("size") is not None else ""
            print(f"      {tag} {ent['name']}{size}")

    if uniportal and report["uniportal"]["exists"]:
        scan = report["uniportal"]["scan"]
        print("\n--- UniPortal 共享卷结构 ---")
        if not scan["projects"]:
            print("  (空目录或无 portal 工程)")
        for proj in scan["projects"]:
            print(f"  工程 {proj['portal_project_id']}  ({proj['item_count']} items)")
            for item in proj["items"]:
                exp = ", ".join(item["export_files"]) or "(无导出)"
                docs = ", ".join(item["doc_files"]) or "(无文档)"
                print(f"    item {item['item_id']}")
                print(f"      文档: {docs}")
                print(f"      导出: {exp}")

    if args.probe:
        print("\n--- 读写探针 ---")
        for probe in report["probes"]:
            status = _status(probe.get("can_write"))
            err = probe.get("error", "")
            print(f"  {probe['label']:20s} [{status}]  {probe['path']}" + (f"  ({err})" if err else ""))

    print("\n--- 建议 ---")
    if mode == "standalone":
        print("  当前为独立模式。Docker 部署需设置 UNIPORTAL_STORAGE_PATH=/data/uniportal")
        print("  本地模拟共享卷: python scripts/check_volumes.py --mock D:/uniportal_data --probe")
    elif not Path(uniportal).is_dir():
        print("  共享卷路径已配置但目录不存在，请检查 docker volume 或 bind mount。")
        print("  docker volume ls | findstr uniportal")
    else:
        print("  共享卷可读。导出将写入 {portal_project_id}/{item_id}/_reqcheck/")
        print("  用 --probe 确认写权限（compose 中勿加 :ro）。")

    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
