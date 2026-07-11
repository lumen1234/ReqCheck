#!/usr/bin/env python3
"""Quick smoke test for UniPortal multi-doc folder scan."""
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from app import app  # noqa: E402
from app.services import project_service  # noqa: E402

mock = BASE / "local_workspaces" / "_mock_uniportal"
item = mock / "demo-portal-uuid" / "demo-item-uuid"
content = item / "MEMS陀螺软件-new"
content.mkdir(parents=True, exist_ok=True)
(content / "req1.docx").write_bytes(b"PK mock1")
(content / "subdir").mkdir(exist_ok=True)
(content / "subdir" / "req2.md").write_text("# req2", encoding="utf-8")
(content / "notes.txt").write_text("notes", encoding="utf-8")
(item / "document-validator").mkdir(exist_ok=True)
(item / "document-validator" / "requirement.json").write_text("{}", encoding="utf-8")
(item / "configuration-test-case-generate").mkdir(exist_ok=True)
(item / "configuration-test-case-generate" / "skip.md").write_text("skip", encoding="utf-8")

app.config["UNIPORTAL_STORAGE_PATH"] = str(mock.resolve())
with app.app_context():
    docs = project_service.list_item_documents(
        "demo-item-uuid", portal_project_id="demo-portal-uuid"
    )
    print("DOC_COUNT", len(docs))
    assert len(docs) >= 3, docs
    for d in docs:
        print(d.batch_order, d.doc_id, d.relative_path)
        assert "document-validator" not in d.relative_path
        assert "configuration-test-case-generate" not in d.relative_path

    batch = project_service.get_uniportal_batch_detail(
        "demo-item-uuid", portal_project_id="demo-portal-uuid"
    )
    assert batch and batch["kind"] == "batch" and batch["doc_count"] == len(docs)
    print("BATCH", batch["kind"], batch["doc_count"], batch["batch_name"])

    items = project_service.list_projects("demo-portal-uuid")
    up = [it for it in items if it.source == "uniportal"]
    assert up and up[0].kind == "batch" and up[0].file_count == len(docs)
    print("LIST", up[0].project_id, up[0].kind, up[0].file_count, up[0].project_name)

    for d in docs:
        r = project_service.resolve_document(
            d.doc_id, portal_project_id="demo-portal-uuid"
        )
        assert r is not None, d.doc_id
        print("RESOLVE", d.doc_id, "->", r.relative_path)

print("PASS")
