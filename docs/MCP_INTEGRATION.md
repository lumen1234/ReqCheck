# ReqCheck MCP 接入与验收

ReqCheck 在原 Web/API 端口上提供 Streamable HTTP MCP 服务。Docker 默认地址：

```text
http://localhost:8001/mcp/
```

本地执行 `python run.py` 同样默认监听 8001。容器内通过 `SERVER_PORT=5000`
监听 5000，再由 Docker 映射到宿主机 8001。

`/mcp/` 是协议端点，不是网页。浏览器人工检查请访问：

```text
http://localhost:8001/mcp/health
```

部署到其他主机时设置对外地址：

```text
PUBLIC_BASE_URL=http://prefix_url:8001
```

如果反向代理传入的 `Host` 与 `PUBLIC_BASE_URL` 不同，用逗号分隔补充：

```text
MCP_ALLOWED_HOSTS=prefix_url:8001,internal-host:5000
MCP_ALLOWED_ORIGINS=http://prefix_url:8001
```

## 工具

- `upload_document`：通过文件名和 Base64 内容上传并持久化新文档，返回 `doc_id`。
- `list_documents`：列出本地已有文档、批次和 UniPortal 文档。
- `parse_document` / `parse_batch`：解析文档并生成需求树。
- `validate_document`：按附录 J 验证已解析文档。
- `export_json` / `export_batch_json`：持久化 JSON 并返回下载地址。
- `export_word` / `export_batch_word`：返回 Word 报告下载地址；下载时临时生成 DOCX。

UniPortal 操作应传入 `portal_project_id`。新附件的完整调用顺序为：上传、解析、验证、导出。

`upload_document` 支持 `docx`、`txt`、`md` 和 `markdown`，默认最大原始文件为
20 MiB，可通过 `MAX_MCP_UPLOAD_BYTES` 调整。HTTP MCP 不能读取客户端本地路径，
因此工具接收 Base64 内容；同内容再次上传时会按文件哈希返回已有 `doc_id`。

## Codex 配置

在 Codex 的 `config.toml` 或受信任项目的 `.codex/config.toml` 中添加：

```toml
[mcp_servers.reqcheck]
url = "http://prefix_url:8001/mcp/"
tool_timeout_sec = 300
```

重启客户端后运行 `codex mcp list`，或在客户端输入 `/mcp` 检查连接。

## 自动化验收

基础握手和工具发现：

```powershell
python scripts/verify_mcp.py --url http://prefix_url:8001/mcp/
```

通过 MCP 上传附件，并继续执行单文档全流程：

```powershell
python scripts/verify_mcp.py --url http://prefix_url:8001/mcp/ --upload-file "C:\path\requirements.docx" --download
```

单文档全流程并下载校验 JSON/DOCX：

```powershell
python scripts/verify_mcp.py --url http://prefix_url:8001/mcp/ --doc-id <doc_id> --download
```

批次解析和导出：

```powershell
python scripts/verify_mcp.py --url http://prefix_url:8001/mcp/ --batch-id <batch_id> --download
```

UniPortal 文档增加：

```text
--portal-project-id <portal_project_id>
```

脚本会验证 MCP 握手、工具清单、JSON 格式以及 DOCX ZIP 文件结构。验证过程可能调用已配置的大模型并产生相应费用。
