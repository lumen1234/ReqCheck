"""Smoke-test a running ReqCheck Streamable HTTP MCP server.

Examples:
    python scripts/verify_mcp.py --url http://127.0.0.1:5000/mcp/
    python scripts/verify_mcp.py --url http://localhost:8001/mcp/ --doc-id <id> --download
"""

import argparse
import asyncio
import base64
import json
import os
import tempfile
import urllib.request
import zipfile

from mcp import Client


EXPECTED_TOOLS = {
    "upload_document",
    "list_documents",
    "parse_document",
    "parse_batch",
    "validate_document",
    "export_json",
    "export_batch_json",
    "export_word",
    "export_batch_word",
}


def _structured(result):
    if getattr(result, "isError", False) or getattr(result, "is_error", False):
        raise RuntimeError(str(result))
    payload = getattr(result, "structuredContent", None)
    if payload is None:
        payload = getattr(result, "structured_content", None)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Tool did not return structured JSON: {result}")
    return payload


def _download_and_verify(json_url: str, word_url: str) -> None:
    with tempfile.TemporaryDirectory(prefix="reqcheck_mcp_verify_") as folder:
        json_path = os.path.join(folder, "requirements.json")
        word_path = os.path.join(folder, "report.docx")
        urllib.request.urlretrieve(json_url, json_path)
        urllib.request.urlretrieve(word_url, word_path)
        with open(json_path, "r", encoding="utf-8") as handle:
            exported = json.load(handle)
        if not isinstance(exported, list):
            raise RuntimeError("Exported JSON root must be an array")
        if not zipfile.is_zipfile(word_path):
            raise RuntimeError("Downloaded Word report is not a valid DOCX/ZIP file")
        print(f"download verification ok: json_items={len(exported)}, docx_bytes={os.path.getsize(word_path)}")


async def verify(args) -> None:
    async with Client(args.url, read_timeout_seconds=args.timeout) as client:
        tools_result = await client.list_tools()
        names = {tool.name for tool in tools_result.tools}
        missing = EXPECTED_TOOLS - names
        if missing:
            raise RuntimeError(f"Missing MCP tools: {sorted(missing)}")
        print(f"MCP handshake ok: server={client.server_info}, tools={sorted(names)}")

        listed = _structured(
            await client.call_tool(
                "list_documents",
                {"portal_project_id": args.portal_project_id} if args.portal_project_id else {},
            )
        )
        print(f"list_documents ok: count={listed.get('count', 0)}")

        if args.upload_file:
            upload_path = os.path.abspath(args.upload_file)
            with open(upload_path, "rb") as handle:
                content_base64 = base64.b64encode(handle.read()).decode("ascii")
            uploaded = _structured(
                await client.call_tool(
                    "upload_document",
                    {
                        "filename": os.path.basename(upload_path),
                        "content_base64": content_base64,
                    },
                    read_timeout_seconds=args.timeout,
                )
            )
            args.doc_id = uploaded["doc_id"]
            print(
                "upload_document ok: "
                f"doc_id={args.doc_id}, cached={uploaded.get('cached')}, filename={uploaded.get('filename')}"
            )
            listed_after_upload = _structured(await client.call_tool("list_documents", {}))
            listed_ids = {item.get("doc_id") for item in listed_after_upload.get("documents", [])}
            if args.doc_id not in listed_ids:
                raise RuntimeError("Uploaded document was not returned by list_documents")
            print("upload persistence check ok: uploaded doc_id is present in list_documents")
            if args.upload_only:
                return

        if not args.doc_id:
            if not args.batch_id:
                return
            batch_common = {"batch_id": args.batch_id}
            if args.portal_project_id:
                batch_common["portal_project_id"] = args.portal_project_id
            parsed_batch = _structured(await client.call_tool("parse_batch", batch_common))
            print(
                "parse_batch ok: "
                f"parsed={parsed_batch.get('parsed_count')}, failed={parsed_batch.get('failed_count')}"
            )
            batch_json = _structured(await client.call_tool("export_batch_json", batch_common))
            batch_word = _structured(await client.call_tool("export_batch_word", batch_common))
            print(f"export_batch_json ok: {batch_json.get('download_url')}")
            print(f"export_batch_word ok: {batch_word.get('download_url')}")
            if args.download:
                _download_and_verify(batch_json["download_url"], batch_word["download_url"])
            return

        common = {"doc_id": args.doc_id}
        if args.portal_project_id:
            common["portal_project_id"] = args.portal_project_id
        parsed = _structured(await client.call_tool("parse_document", common))
        print(f"parse_document ok: cached={parsed.get('cached')}, output={parsed.get('output_file')}")

        if not args.skip_validation:
            validated = _structured(
                await client.call_tool(
                    "validate_document",
                    {"doc_id": args.doc_id},
                    read_timeout_seconds=args.timeout,
                )
            )
            print(
                "validate_document ok: "
                f"total={validated.get('total')}, passed={validated.get('passed')}, failed={validated.get('failed')}"
            )

        exported = _structured(await client.call_tool("export_json", common))
        word = _structured(await client.call_tool("export_word", common))
        print(f"export_json ok: {exported.get('download_url')}")
        print(f"export_word ok: {word.get('download_url')}")
        if args.download:
            _download_and_verify(exported["download_url"], word["download_url"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5000/mcp/")
    parser.add_argument("--doc-id")
    parser.add_argument("--upload-file", help="Upload this file through MCP, then use it as --doc-id")
    parser.add_argument("--upload-only", action="store_true", help="Stop after upload and persistence check")
    parser.add_argument("--batch-id")
    parser.add_argument("--portal-project-id")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    asyncio.run(verify(args))


if __name__ == "__main__":
    main()
