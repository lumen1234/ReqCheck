# UniPortal 集成说明（ReqCheck）

ReqCheck 已按 [SUBTOOL_INTEGRATION_GUIDE.md](./SUBTOOL_INTEGRATION_GUIDE.md) 接入双数据源 + 工程隔离。

## 环境变量

| 变量 | 默认值（本地） | Docker |
|------|----------------|--------|
| `UNIPORTAL_STORAGE_PATH` | 未设置（不读共享卷） | `/data/uniportal` |
| `LOCAL_WORKSPACES_DIR` | `./local_workspaces` | `/app/local_workspaces` |

## 私有卷目录

```
local_workspaces/
├── uploads/           # 本地上传
├── parse_results/     # 解析 JSON
├── parse_assets/      # 解析图片等资源
├── validate_results/
└── export_results/
```

## API

- `GET /api/documents?portal_project_id=<UUID>` — 列表（有参数：UniPortal 工程 item + 本地上传；无参数：仅本地上传）
- `GET /api/parse/<doc_id>?portal_project_id=<UUID>` — 解析（支持 UniPortal item_id）
- `DELETE /api/delete/<doc_id>` — UniPortal 来源返回 403

## 启动

```bash
# 1. 先启 UniPortal（创建 uniportal_storage 卷）
# 2. 构建前端并启动
scripts/build-frontend.bat
python run.py

# 或 Docker Compose
docker compose up -d --build
```

## 从 UniPortal 跳转

```
http://<host>:5000/?portal_project_id=<工程UUID>#/documents/<item_id>/parse
```

前端会从 URL 读取 `portal_project_id` 并写入 `sessionStorage`，列表/解析请求自动带上该参数。

## 迁移旧数据（可选）

若之前使用仓库根目录的 `uploads/`、`parse_results/`：

```powershell
mkdir local_workspaces\uploads, local_workspaces\parse_results, local_workspaces\parse_assets -Force
Copy-Item uploads\* local_workspaces\uploads\ -ErrorAction SilentlyContinue
Copy-Item app\parse_results\* local_workspaces\parse_results\ -ErrorAction SilentlyContinue
```
