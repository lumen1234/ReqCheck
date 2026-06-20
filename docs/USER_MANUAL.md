# ReqCheck 文档审查工具 — 用户使用手册

> 版本：dev 分支 | 适用对象：测试人员、需求工程师、质量管理人员  
> 访问地址（部署后）：`http://<服务器IP>:8001`（Docker）或 `http://localhost:5000`（本地开发）

---

## 1. 工具简介

**ReqCheck（文档审查 / document-validator）** 是装备软件智能测试一体化方案中的子工具，面向 **GJB 438C** 体系下的 **软件需求规格说明（附录 J）** 等 Word/文本文档，提供：

| 阶段 | 功能 |
|------|------|
| 文档上传 | 本地上传或从 UniPortal 共享卷读取项目 |
| 文档分析 | 自动解析章节结构，生成需求树 |
| 需求验证 | 基于标准与 AI 大模型审查完整性与合规性 |
| 文档导出 | 导出结构化 JSON，并同步至 UniPortal 共享卷 |

---

## 2. 核心技术（简要）

### 2.1 整体架构

```
浏览器 (Vue 3 + Vite)
        ↓ HTTP API
Flask 后端 (Python 3.10)
        ↓
┌───────────────────┬────────────────────┐
│ 文档解析引擎       │ 大模型验证服务      │
│ docx/txt/md       │ DeepSeek 等 API     │
│ 章节树 + 表格图片  │ 需求分类 + 合规判定 │
│ 公式 KaTeX 展示   │                    │
└───────────────────┴────────────────────┘
        ↓
本地工作区 / UniPortal 共享卷 (document-validator/)
```

### 2.2 前端

| 技术 | 用途 |
|------|------|
| Vue 3 + Vite | 单页应用、构建 |
| Vue Router | 四步流程路由（上传→分析→验证→导出） |
| Tailwind CSS | 界面样式 |
| KaTeX | 文档内公式渲染 |
| Axios | 与后端 API 通信 |

### 2.3 后端

| 技术 | 用途 |
|------|------|
| Flask | Web 服务与 REST API |
| python-docx | Word 文档解析（章节、表格、图片、OMML 公式） |
| LibreOffice（Docker 内） | EMF 等图片格式转 PNG |
| markdown-it | Markdown/文本解析 |
| DeepSeek API（可配置） | 需求验证、需求类型与 is_req 分类 |
| SQLite | 文档与验证结果元数据 |

### 2.4 UniPortal 集成

- **共享卷只读/读写**：读取门户上传的项目文档  
- **导出路径**：`{portal_project_id}/{item_id}/<主文档同目录>/document-validator/requirement.json`  
- **工程隔离**：URL 携带 `portal_project_id`，仅展示当前工程下的项目  

### 2.5 部署方式

- **Docker 镜像**（推荐生产）：多阶段构建（Node 编译前端 + Python 运行后端）  
- **本地开发**：`python run.py` + 可选 `UNIPORTAL_STORAGE_PATH` 虚拟共享卷  

---

## 3. 使用前准备

### 3.1 访问方式

**方式 A — 独立使用**

直接打开：`http://<host>:8001/`

**方式 B — 从 UniPortal 跳转（推荐）**

```
http://<host>:8001/?portal_project_id=<工程UUID>
```

门户会带入工程 ID，项目列表显示该工程共享卷中的条目 + 本地上传记录。

### 3.2 支持的文档格式

| 格式 | 解析支持 |
|------|----------|
| `.docx` | ✅ 完整支持（章节、表格、图片、Word 公式） |
| `.txt` / `.md` | ✅ 支持 |
| `.pdf` | 界面可上传，解析能力有限（规划中） |

### 3.3 文档结构要求

- 文档应包含 **GB/T 8567 风格编号** 或 **Markdown 标题**（如 `1`、`1.1`、`# 标题`）  
- 否则解析阶段会提示「未识别到符合格式的章节」  

---

## 4. 核心操作步骤

整体流程为四步，顶部导航栏会显示当前进度：

```
文档上传 → 文档分析 → 需求验证 → 文档导出
```

### 步骤 1：文档上传

1. 打开首页「文档上传」  
2. **本地上传**：拖拽或点击选择 `.docx` / `.txt` 等文件，填写文档名称，点击「确认上传并开始审查」  
3. **UniPortal 项目**：在下方「项目列表」中选择来源为 `uniportal` 的条目，点击「开始审查」  
4. 上传成功后自动进入 **文档分析** 页  

> **【截图 1】文档上传页**  
> 建议截取：欢迎标题、拖拽上传区域、历史/项目列表。  
> 保存路径建议：`docs/images/user-manual/01-upload.png`

---

### 步骤 2：文档分析

1. 左侧为 **需求结构树**（章节层级）  
2. 右侧为选中节点的 **需求内容**（正文、表格、图片、公式）  
3. 点击树节点切换查看；确认结构无误后，点击底部 **「进入需求验证」**  

**常用操作：**

- 若结构或图片异常：删除文档重新上传，或访问  
  `GET /api/parse/<doc_id>?force=1` 强制重新解析  
- 含 Word 公式的文档：解析后以 KaTeX 形式展示  

> **【截图 2】文档分析页**  
> 建议截取：左侧需求树 + 右侧含表格/图片/公式的节点详情。  
> 保存路径：`docs/images/user-manual/02-parse.png`

---

### 步骤 3：需求验证

1. 系统自动（或手动触发）调用大模型，按 GJB 438C / 附录 J 相关规则逐条验证  
2. 页面展示：**总需求数、通过数、失败数、通过率**  
3. 列表中绿色为通过，红色为失败；可展开查看 **验证说明（reason）**  
4. 验证完成后，点击 **「进入文档导出」**  

**可选操作：**

- 「重新加载」：读取已有验证缓存  
- 「强制重新验证」：忽略缓存，重新调用大模型  

> **【截图 3】需求验证页**  
> 建议截取：顶部统计卡片 + 一条通过项与一条失败项（含说明）。  
> 保存路径：`docs/images/user-manual/03-validate.png`

---

### 步骤 4：文档导出

1. 查看验证汇总与需求明细  
2. 点击 **「导出 JSON」** 下载结构化需求文件  
3. 若已接入 UniPortal，导出同时写入共享卷：  

```
.../<item_id>/<主文档目录>/document-validator/requirement.json
```

4. 可点击「开始新分析」返回上传页处理下一文档  

> **【截图 4】文档导出页**  
> 建议截取：统计信息、导出按钮、某条需求的验证状态。  
> 保存路径：`docs/images/user-manual/04-export.png`

---

## 5. UniPortal 模式说明

| 场景 | 行为 |
|------|------|
| 从门户带 `portal_project_id` 进入 | 列表含该工程共享卷项目 + 本地上传 |
| 直接访问工具 URL | 仅显示本地上传（不暴露其他工程） |
| 导出 | 自动同步到共享卷 `document-validator/requirement.json` |
| 删除 | UniPortal 来源项目 **不可删除**（返回 403） |

> **【截图 5】UniPortal 项目列表**  
> 建议截取：URL 含 `portal_project_id`、列表中 `source: uniportal` 条目。  
> 保存路径：`docs/images/user-manual/05-uniportal-list.png`

---

## 6. 关键界面一览（截图清单）

| 编号 | 文件名建议 | 页面 | 要点 |
|------|------------|------|------|
| 1 | `01-upload.png` | 文档上传 | 上传区 + 项目列表 |
| 2 | `02-parse.png` | 文档分析 | 需求树 + 内容详情 |
| 3 | `03-validate.png` | 需求验证 | 通过率 + 失败说明 |
| 4 | `04-export.png` | 文档导出 | 导出 JSON 按钮 |
| 5 | `05-uniportal-list.png` | 上传页（门户模式） | portal 参数 + uniportal 来源 |
| 6 | `06-nav-steps.png` | 任意内页 | 顶部四步导航条 |

将截图放入 `docs/images/user-manual/` 后，可在本手册中把占位说明替换为：

```markdown
![文档上传页](images/user-manual/01-upload.png)
```

---

## 7. 常见问题

| 现象 | 处理 |
|------|------|
| 解析失败「未识别到章节」 | 检查文档是否有 1 / 1.1 / # 标题 等结构 |
| 图片不显示 | Docker 部署需含 LibreOffice；强制重解析 `?force=1` |
| 公式不显示 | 重新解析；Word 内置公式支持较好，MathType 暂不支持 |
| 验证一直 loading | 检查 LLM API 配置（设置页 / 环境变量） |
| 导出未写入共享卷 | 确认 `UNIPORTAL_STORAGE_PATH` 已配置且 item 在共享卷中存在 |
| 导出目录层级不对 | 使用最新版本；导出目录与主文档同层，见 `check_uniportal_item.py` |

---

## 8. 本地快速体验（可选）

```powershell
cd E:\ReqCheck
.\venv\Scripts\Activate.ps1
python run.py
# 浏览器 http://localhost:5000
```

虚拟 UniPortal 共享卷测试：

```powershell
python scripts/setup_mock_shared_volume.py
$env:UNIPORTAL_STORAGE_PATH = "E:\ReqCheck\local_workspaces\_mock_uniportal"
python run.py
# http://localhost:5000/?portal_project_id=demo-portal-uuid
```

---

## 9. 相关文档

| 文档 | 内容 |
|------|------|
| [DOCKER_OPERATIONS.md](./DOCKER_OPERATIONS.md) | Docker 构建与部署 |
| [UNIPORTAL_INTEGRATION.md](./UNIPORTAL_INTEGRATION.md) | 门户集成说明 |
| [EXPORT_JSON.md](./EXPORT_JSON.md) | 导出 JSON 字段说明 |
| [SUBTOOL_INTEGRATION_GUIDE.md](./SUBTOOL_INTEGRATION_GUIDE.md) | 共享卷目录约定 |

---

*文档维护：请在发版或界面变更后同步更新截图与端口号（当前 Docker 对外端口 **8001**）。*
