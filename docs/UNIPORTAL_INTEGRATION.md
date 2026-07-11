# ReqCheck × UniPortal 一体化集成说明

ReqCheck 已按 [SUBTOOL_INTEGRATION_GUIDE.md](./SUBTOOL_INTEGRATION_GUIDE.md) 实现 **双数据源 + 工程隔离**。

## 架构概览

```
UniPortal 上传项目
       ↓
uniportal_storage 卷  (/data/uniportal/{portal_project_id}/{item_id}/)
       ↓ 只读扫描（列表/解析读文档）
ReqCheck 容器
       ↓ 读写
reqcheck_local 卷   (/app/local_workspaces/  解析/校验/导出缓存)
       ↓ 导出同步（ReqCheck 特例）
uniportal_storage   (.../{item_id}/document-validator/requirement.json)
```

## 环境变量

| 变量 | 独立开发 | Docker |
|------|----------|--------|
| `UNIPORTAL_STORAGE_PATH` | 未设置 | `/data/uniportal` |
| `LOCAL_WORKSPACES_DIR` | `./local_workspaces` | `/app/local_workspaces` |
| `UNIPORTAL_EXPORT_SUBDIR` | `document-validator` | `document-validator` |

## 工程隔离行为

| 场景 | 列表 API | 共享卷扫描 |
|------|----------|------------|
| 从 UniPortal 跳转 `?portal_project_id=X` | 当前工程 item + 本地上传 | 仅 `/data/uniportal/X/` |
| 直接访问子工具（无参数） | 仅本地上传 | **不扫描**共享卷 |

## 已实现文件清单

| 层级 | 文件 | 作用 |
|------|------|------|
| 部署 | `docker-compose.yml` | `uniportal_storage` external 卷 + 私有卷 |
| 部署 | `run.sh` | WSL 快速启动（共享卷 + bind mount 私有目录） |
| 后端 | `app/services/project_service.py` | 双源解析、`list_projects(portal_project_id)` |
| 后端 | `app/routes/upload.py` | `GET /api/documents?portal_project_id=` |
| 后端 | `app/routes/parse.py` | `GET /api/parse/<item_id>?portal_project_id=` |
| 后端 | `app/routes/export.py` | 导出 + 同步共享卷 `document-validator/` |
| 前端 | `frontend/src/utils/portal.js` | URL → sessionStorage |
| 前端 | `frontend/src/api/index.js` | GET 请求自动带 `portal_project_id` |
| 前端 | `frontend/src/views/UploadView.vue` | 列表展示 `source: uniportal/local` |
| 验证 | `scripts/verify_uniportal_integration.py` | 集成检查清单 |
| 验证 | `scripts/check_uniportal_item.py` | 按 item_id 检查是否在共享卷 |

## 启动顺序

```bash
# 1. 先启 UniPortal（创建 uniportal_storage 卷）
cd UniPortal && docker compose up -d

# 2. 再启 ReqCheck
cd ReqCheck && docker compose up -d --build

# 3. 验证
docker exec reqcheck python scripts/verify_uniportal_integration.py
docker exec reqcheck python scripts/check_uniportal_item.py --list
```

WSL 本地开发（私有目录与 Windows 同步）：

```bash
cd /mnt/e/ReqCheck
docker volume create uniportal_storage   # 若尚未创建
bash run.sh
```

## 从 UniPortal 跳转

```
http://<host>:5000/?portal_project_id=<工程UUID>#/documents/<item_id>/parse
```

前端启动时读取 `portal_project_id` 写入 `sessionStorage`，后续 parse/validate/export 请求自动携带。

## API 摘要

- `GET /api/documents?portal_project_id=<UUID>` — 工程 item 列表 + 本地上传（含 `source` 字段）
- `GET /api/parse/<item_id>?portal_project_id=<UUID>` — 从共享卷读 docx 并解析
- `GET /api/export/<item_id>?portal_project_id=<UUID>` — 导出并同步至 `document-validator/`
- `DELETE /api/delete/<item_id>` — UniPortal 来源返回 403

## 本地独立开发

不设 `UNIPORTAL_STORAGE_PATH` 时等同独立模式：

```bash
scripts/build-frontend.bat
python run.py
```

模拟共享卷：

```bash
python scripts/check_uniportal_item.py --setup-mock local_workspaces/_mock_uniportal \
  --portal-project-id demo-proj --item-id demo-item
python scripts/check_uniportal_item.py --mock local_workspaces/_mock_uniportal --list
```

## ReqCheck 与通用约定的差异

通用子工具共享卷为 **只读**（`:ro`）。ReqCheck 需将 export JSON **写回** item 目录下的 `document-validator/`（与 `project_name` 同级），因此 compose 中共享卷为 **读写**。中间产物（parse/validate/图片）仍只写私有卷。
