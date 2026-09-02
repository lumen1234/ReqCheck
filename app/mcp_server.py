"""ReqCheck MCP tools.

The MCP layer intentionally reuses the existing Flask application services and
route handlers in-process.  This keeps the browser API and the agent API on the
same data store without making loopback HTTP requests.
"""

import base64
import binascii
from io import BytesIO
from typing import Any, Callable, Optional
from urllib.parse import quote

from flask import Response
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from starlette.responses import JSONResponse

from app import app


SERVER_INSTRUCTIONS = """
ReqCheck analyses software requirement documents. Use upload_document when the
user supplies a new local attachment; otherwise start with list_documents when
the document ID is unknown. For a document, call parse_document before
validate_document, then use export_json and/or export_word. Batch IDs use the
corresponding batch tools. Pass portal_project_id for UniPortal project isolation.
Export tools create server-side results and return download URLs; do not invent
paths or IDs. Parsing and validation can take several minutes.
""".strip()


mcp = MCPServer(
    name="ReqCheck",
    description="需求文档解析、分类、规范验证以及 JSON/Word 导出服务",
    instructions=SERVER_INSTRUCTIONS,
    version="1.1.0",
)


@mcp.custom_route("/health", methods=["GET"])
async def mcp_health(_):
    """Browser-friendly health check; the MCP protocol endpoint itself is not a web page."""
    return JSONResponse({
        "status": "ok",
        "service": "ReqCheck MCP",
        "protocol_endpoint": "/mcp/",
    })


def _absolute_url(path: str) -> str:
    return f"{app.config['PUBLIC_BASE_URL']}/{path.lstrip('/')}"


def _invoke_json_view(
    view: Callable[..., Any],
    path: str,
    *,
    view_args: tuple[Any, ...] = (),
    query: Optional[dict[str, Any]] = None,
    method: str = "GET",
    data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Invoke an existing Flask JSON endpoint without a loopback HTTP request."""
    clean_query = {key: value for key, value in (query or {}).items() if value is not None}
    with app.test_request_context(path, query_string=clean_query, method=method, data=data):
        response: Response = app.make_response(view(*view_args))
        payload = response.get_json(silent=True)
        if response.status_code >= 400:
            if isinstance(payload, dict):
                message = payload.get("error") or str(payload)
            else:
                message = response.get_data(as_text=True) or f"HTTP {response.status_code}"
            raise ToolError(message)
        if not isinstance(payload, dict):
            raise ToolError("ReqCheck endpoint did not return a JSON object")
        return payload


def _compact_parse_result(payload: dict[str, Any]) -> dict[str, Any]:
    tree = payload.get("requirement_tree") or {}
    return {
        "success": True,
        "cached": bool(payload.get("cached")),
        "cached_from": payload.get("cached_from"),
        "document_title": tree.get("label"),
        "output_file": payload.get("output_file"),
        "requirement_tree": tree,
    }


@mcp.tool()
def upload_document(filename: str, content_base64: str) -> dict[str, Any]:
    """上传一个新文档到 ReqCheck 的服务器持久化存储。

    Args:
        filename: 包含扩展名的原始文件名；支持 docx、txt、md、markdown。
        content_base64: 文件二进制内容的 Base64 字符串，也可使用 data URL 格式。

    Returns:
        上传后的 doc_id、文件名、类型、状态，以及是否命中已有文件缓存。
    """
    from app.routes.upload import allowed_file, upload_file

    safe_name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not safe_name or safe_name in {".", ".."}:
        raise ToolError("filename is required")
    if not allowed_file(safe_name):
        raise ToolError("File type not allowed; supported: docx, txt, md, markdown")
    if not isinstance(content_base64, str) or not content_base64.strip():
        raise ToolError("content_base64 is required")

    encoded = content_base64.strip()
    if encoded.startswith("data:"):
        header, separator, encoded = encoded.partition(",")
        if not separator or ";base64" not in header.lower():
            raise ToolError("Invalid data URL; expected a base64 data URL")
    encoded = "".join(encoded.split())

    # Base64 is about 4/3 the original size. Reject oversized input before decoding.
    max_bytes = int(app.config.get("MAX_MCP_UPLOAD_BYTES", 20 * 1024 * 1024))
    estimated_bytes = (len(encoded) * 3) // 4
    if estimated_bytes > max_bytes:
        raise ToolError(f"File is too large; maximum upload size is {max_bytes} bytes")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ToolError("content_base64 is not valid Base64") from exc
    if not content:
        raise ToolError("Uploaded file is empty")
    if len(content) > max_bytes:
        raise ToolError(f"File is too large; maximum upload size is {max_bytes} bytes")

    file_type = safe_name.rsplit(".", 1)[1].lower()
    payload = _invoke_json_view(
        upload_file,
        "/api/upload",
        method="POST",
        data={
            "file": (BytesIO(content), safe_name),
            "file_type": file_type,
        },
    )
    return {
        "success": True,
        "doc_id": payload.get("doc_id"),
        "filename": payload.get("filename"),
        "file_type": payload.get("file_type"),
        "status": "已上传",
        "cached": bool(payload.get("cached")),
        "source": payload.get("source", "local"),
        "message": payload.get("message"),
    }


@mcp.tool()
def list_documents(portal_project_id: Optional[str] = None) -> dict[str, Any]:
    """列出 ReqCheck 可处理的本地已有文档、批次和 UniPortal 文档。

    Args:
        portal_project_id: 可选的 UniPortal 工程 UUID；提供后按该工程隔离扫描。
    """
    from app.routes.upload import list_documents as list_documents_view

    payload = _invoke_json_view(
        list_documents_view,
        "/api/documents",
        query={"portal_project_id": portal_project_id},
    )
    documents = payload.get("documents") or []
    return {"success": True, "count": len(documents), "documents": documents}


@mcp.tool()
def parse_document(
    doc_id: str,
    portal_project_id: Optional[str] = None,
    force: bool = False,
    split_by: Optional[str] = None,
) -> dict[str, Any]:
    """解析一个本地或 UniPortal 文档并生成需求树。

    Args:
        doc_id: list_documents 返回的文档 ID。
        portal_project_id: UniPortal 工程 UUID；处理 UniPortal 文档时建议提供。
        force: 是否忽略解析缓存并重新解析。
        split_by: 可选的正文分块关键词。
    """
    from app.routes.parse import parse_document_payload

    try:
        with app.app_context():
            payload = parse_document_payload(
                doc_id,
                force=force,
                portal_project_id=portal_project_id,
                split_by=split_by,
            )
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(str(exc)) from exc
    return _compact_parse_result(payload)


@mcp.tool()
def parse_batch(
    batch_id: str,
    portal_project_id: Optional[str] = None,
    force: bool = False,
) -> dict[str, Any]:
    """解析一个本地批次或 UniPortal 条目中的全部文档。"""
    from app.routes.parse import parse_batch as parse_batch_view

    payload = _invoke_json_view(
        parse_batch_view,
        f"/api/parse/batch/{batch_id}",
        view_args=(batch_id,),
        query={"portal_project_id": portal_project_id, "force": "1" if force else None},
    )
    documents = []
    for item in payload.get("documents") or []:
        tree = item.get("requirement_tree") or {}
        documents.append({
            "doc": item.get("doc"),
            "doc_id": item.get("doc_id"),
            "filename": item.get("filename"),
            "cached": bool(item.get("cached")),
            "document_title": tree.get("label"),
            "output_file": item.get("output_file"),
        })
    return {
        "success": not bool(payload.get("errors")),
        "batch_id": payload.get("batch_id"),
        "batch_name": payload.get("batch_name"),
        "doc_count": payload.get("doc_count", 0),
        "parsed_count": payload.get("parsed_count", 0),
        "failed_count": payload.get("failed_count", 0),
        "documents": documents,
        "errors": payload.get("errors") or [],
    }


@mcp.tool()
def validate_document(doc_id: str, force: bool = False) -> dict[str, Any]:
    """按 GJB 438C 附录 J 验证已解析文档；调用前应先 parse_document。"""
    from app.routes.validate import validate_requirements

    payload = _invoke_json_view(
        validate_requirements,
        f"/api/validate/{doc_id}",
        view_args=(doc_id,),
        query={"force": "1" if force else None},
    )
    results = payload.get("validation_results") or []
    passed = sum(1 for item in results if item.get("result") is True)
    failed = sum(1 for item in results if item.get("result") is False)
    return {
        "success": True,
        "cached": bool(payload.get("cached")),
        "cached_from": payload.get("cached_from"),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "validation_results": results,
    }


@mcp.tool()
def export_json(doc_id: str, portal_project_id: Optional[str] = None) -> dict[str, Any]:
    """将一个已解析文档导出为持久化 JSON，并返回下载地址。"""
    from app.routes.export import export_requirements

    payload = _invoke_json_view(
        export_requirements,
        f"/api/export/{doc_id}",
        view_args=(doc_id,),
        query={"portal_project_id": portal_project_id},
    )
    filename = payload["export_file"]
    return {
        "success": True,
        "doc_id": doc_id,
        "total_requirements": payload.get("total_requirements", 0),
        "export_file": filename,
        "export_path": payload.get("export_path"),
        "download_url": _absolute_url(f"/api/export/files/{quote(filename, safe='')}"),
        "uniportal_export_path": payload.get("uniportal_export_path"),
        "uniportal_export_synced": bool(payload.get("uniportal_export_synced")),
    }


@mcp.tool()
def export_batch_json(batch_id: str, portal_project_id: Optional[str] = None) -> dict[str, Any]:
    """将一个本地批次或 UniPortal 条目导出为持久化 JSON。"""
    from app.routes.export import export_batch_requirements

    payload = _invoke_json_view(
        export_batch_requirements,
        f"/api/export/batch/{batch_id}",
        view_args=(batch_id,),
        query={"portal_project_id": portal_project_id},
    )
    filename = payload["export_file"]
    return {
        "success": True,
        "batch_id": batch_id,
        "batch_name": payload.get("batch_name"),
        "doc_count": payload.get("doc_count", 0),
        "total_requirements": payload.get("total_requirements", 0),
        "missing": payload.get("missing") or [],
        "export_file": filename,
        "export_path": payload.get("export_path"),
        "download_url": _absolute_url(f"/api/export/files/{quote(filename, safe='')}"),
        "uniportal_export_path": payload.get("uniportal_export_path"),
        "uniportal_export_synced": bool(payload.get("uniportal_export_synced")),
    }


@mcp.tool()
def export_word(doc_id: str, portal_project_id: Optional[str] = None) -> dict[str, Any]:
    """返回单文档 Word 验证报告的下载地址。

    下载请求会临时生成 DOCX，传输完成后服务器可删除临时文件。
    """
    from app.routes.export import _load_requirement_tree

    with app.app_context():
        if not _load_requirement_tree(doc_id):
            raise ToolError("Requirement tree not found; call parse_document first")
    query = f"?portal_project_id={quote(portal_project_id, safe='')}" if portal_project_id else ""
    return {
        "success": True,
        "doc_id": doc_id,
        "temporary": True,
        "download_url": _absolute_url(f"/api/export/{quote(doc_id, safe='')}/word{query}"),
    }


@mcp.tool()
def export_batch_word(batch_id: str, portal_project_id: Optional[str] = None) -> dict[str, Any]:
    """返回批次 Word 验证报告的临时生成下载地址。"""
    from app.routes.upload import get_batch

    _invoke_json_view(
        get_batch,
        f"/api/batches/{batch_id}",
        view_args=(batch_id,),
        query={"portal_project_id": portal_project_id},
    )
    query = f"?portal_project_id={quote(portal_project_id, safe='')}" if portal_project_id else ""
    return {
        "success": True,
        "batch_id": batch_id,
        "temporary": True,
        "download_url": _absolute_url(f"/api/export/batch/{quote(batch_id, safe='')}/word{query}"),
    }
