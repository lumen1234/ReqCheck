import json
import os
import tempfile
import unittest

from app import app
from app.services import project_service


class UniPortalProjectListTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = os.path.join(self.temp_dir.name, "uniportal_storage")
        self.local_workspaces = os.path.join(self.temp_dir.name, "local_workspaces")
        os.makedirs(self.storage)
        os.makedirs(os.path.join(self.local_workspaces, "uploads"))
        self.original_config = {
            "UNIPORTAL_STORAGE_PATH": app.config.get("UNIPORTAL_STORAGE_PATH"),
            "LOCAL_WORKSPACES_DIR": app.config.get("LOCAL_WORKSPACES_DIR"),
            "UPLOAD_FOLDER": app.config.get("UPLOAD_FOLDER"),
        }
        app.config.update(
            UNIPORTAL_STORAGE_PATH=self.storage,
            LOCAL_WORKSPACES_DIR=self.local_workspaces,
            UPLOAD_FOLDER=os.path.join(self.local_workspaces, "uploads"),
        )
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        app.config.update(self.original_config)
        self.app_context.pop()
        self.temp_dir.cleanup()

    def _make_item(self, portal_id, item_id):
        item_dir = os.path.join(self.storage, portal_id, item_id)
        os.makedirs(os.path.join(item_dir, "uniportal"))
        os.makedirs(os.path.join(item_dir, "上传"))
        return item_dir

    def test_manifest_name_and_documents_are_returned_as_project_hierarchy(self):
        portal_id = "portal-project"
        item_id = "5b435d3f-caa9-4d42-92ac-4d046026b55e"
        item_dir = self._make_item(portal_id, item_id)
        manifest = {
            "current_item": {
                "item_id": item_id,
                "name": "上传测试文件",
                "uploaded_at": "2026-08-31T08:04:15.568Z",
            }
        }
        with open(
            os.path.join(item_dir, "uniportal", "project_manifest.json"),
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(manifest, handle, ensure_ascii=False)
        with open(os.path.join(item_dir, "上传", "需求一.docx"), "wb") as handle:
            handle.write(b"docx placeholder")
        with open(os.path.join(item_dir, "上传", "需求二.md"), "w", encoding="utf-8") as handle:
            handle.write("# requirement")
        with open(os.path.join(item_dir, "uniportal", "说明.md"), "w", encoding="utf-8") as handle:
            handle.write("metadata, not a requirement document")

        entries = project_service.list_projects(portal_project_id=portal_id)
        shared_entry = next(entry for entry in entries if entry.project_id == item_id)
        payload = project_service.project_entry_to_dict(shared_entry)

        self.assertEqual(payload["filename"], "上传测试文件")
        self.assertEqual(payload["upload_time"], "2026-08-31T08:04:15.568Z")
        self.assertEqual(payload["file_count"], 2)
        self.assertEqual(len(payload["documents"]), 2)
        self.assertEqual(
            {document["filename"] for document in payload["documents"]},
            {"需求一.docx", "需求二.md"},
        )
        self.assertTrue(
            all(document["relative_path"].startswith("上传/") for document in payload["documents"])
        )

    def test_invalid_manifest_falls_back_to_content_folder_name(self):
        portal_id = "portal-project"
        item_id = "item-with-invalid-manifest"
        item_dir = self._make_item(portal_id, item_id)
        with open(
            os.path.join(item_dir, "uniportal", "project_manifest.json"),
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write("not valid json")
        with open(os.path.join(item_dir, "上传", "需求.docx"), "wb") as handle:
            handle.write(b"docx placeholder")

        entries = project_service.list_projects(portal_project_id=portal_id)
        shared_entry = next(entry for entry in entries if entry.project_id == item_id)

        self.assertEqual(shared_entry.project_name, "上传")
        self.assertEqual(shared_entry.file_count, 1)


if __name__ == "__main__":
    unittest.main()
