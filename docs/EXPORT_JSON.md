# ReqCheck 导出 JSON 输出说明

## 概述

ReqCheck（需求文档验证系统）在完成文档解析与规范验证后，将需求树扁平化为 JSON 列表供下游工具消费。本文档按子工具输出规范提供以下内容：

1. 输出文件名：`export_{doc_id}.json`
2. 字段定义表：对每个字段包含字段路径、类型、是否必填、说明、举例
3. 示例 JSON

文件根结构为 **JSON 数组**，每个元素对应需求树中的一个节点（含根节点、章节标题、具体需求），按深度优先顺序排列。

---

## 输出文件名

`export_{doc_id}.json`

- `{doc_id}` 为文档唯一标识（本地上传为哈希值；UniPortal 来源通常为 item UUID）
- 默认落盘路径：`local_workspaces/export_results/export_{doc_id}.json`
- UniPortal 共享卷同步路径（若已挂载）：`/data/uniportal/{portal_project_id}/{item_id}/document-validator/requirement.json`

---

## 字段定义表

| 字段路径 | 类型 | 必填？ | 说明 | 举例 |
|----------|------|--------|------|------|
| （根） | 数组 | 是 | 扁平化需求条目列表，每个元素为一个需求节点对象 | 见下方 |
| id | 字符串 | 是 | 导出层唯一编号，从 `req1` 递增 | `"req1"` |
| node_id | 字符串 | 是 | 需求树原始节点 ID，与解析结果中的节点一一对应 | `"node_3_2_1"` |
| title | 字符串 | 是 | 节点标题，通常含章节编号 | `"3.2.1 数据采集"` |
| content | 字符串 / null | 是 | 纯文本需求正文（不含表格、图片占位）；章节性节点可为 `null` | `"系统应以不低于 100Hz 的采样率采集陀螺角速度数据。"` |
| content_html | 字符串 | 是 | HTML 格式正文，供富文本展示；无内容时为空字符串 | `"<p style=\"margin:0 0 12px\">系统应…</p>"` |
| level | 整数 | 是 | 节点层级：根节点为 `0`，一级章节为 `1`，依次递增 | `2` |
| parent_id | 字符串 | 是 | 父节点在本列表中的 `id`；根节点的父为 `"root"` | `"req2"` |
| is_req | 整数 | 是 | 是否为功能需求：`1`=是，`0`=否（大模型在解析阶段判断该节点是否需落实到代码） | `1` |
| is_req_reason | 字符串 | 是 | `is_req` 上述判断的依据 | `"描述了具体的数据采集功能与参数，需在软件中实现。"` |
| validation_result | 布尔 / null | 是 | 附录 J 规范验证结果：`true` 合规，`false` 不合规，未验证时为 `null` | `true` |
| validation_reason | 字符串 | 是 | 规范验证说明；未验证时为空字符串 | `"内容符合 3.2 能力需求编写要求。"` |
| tables | 数组 | 是 | 节点关联的表格列表，无表格时为 `[]` | 见下方 |
| tables[].id | 字符串 | 否 | 表格在节点内的序号标识 | `"tbl_001"` |
| tables[].headers | 数组 | 是 | 表头列名列表 | `["参数", "要求"]` |
| tables[].rows | 数组 | 是 | 数据行，每行为字符串数组 | `[["采样率", "≥ 100 Hz"]]` |
| tables[].caption | 字符串 / null | 否 | 表格标题或说明 | `null` |
| images | 数组 | 是 | 节点关联的图片列表，无图片时为 `[]` | 见下方 |
| images[].id | 字符串 | 是 | 图片资源 ID | `"img_001"` |
| images[].path | 字符串 | 是 | 图片访问 API 路径（相对路径） | `"/api/parse/abc123/assets/img_001.png"` |
| images[].alt | 字符串 | 是 | 替代文本 | `"图 1 软件工作主流程图"` |
| images[].caption | 字符串 / null | 否 | 图注 | `"图 1 软件工作主流程图"` |

---

## 示例 JSON

```json
[
  {
    "id": "req1",
    "node_id": "root",
    "title": "MEMS陀螺软件需求规格说明.docx",
    "content": null,
    "content_html": "",
    "level": 0,
    "parent_id": "root",
    "is_req": 0,
    "is_req_reason": "根节点，无编码需求。",
    "validation_result": true,
    "validation_reason": "根节点，无对应规范要求。",
    "tables": [],
    "images": []
  },
  {
    "id": "req2",
    "node_id": "node_3_2_1",
    "title": "3.2.1 工作流程",
    "content": "软件的工作主流程如图 1所示。系统上电后，首先进行时钟配置、USART、SPI、DMA等外设的初始化…",
    "content_html": "<p style=\"margin:0 0 12px;line-height:1.6\">软件的工作主流程如图 1所示…</p>",
    "level": 3,
    "parent_id": "req9",
    "is_req": 1,
    "is_req_reason": "描述了软件工作流程与处理逻辑，属于需在代码中实现的功能需求。",
    "validation_result": true,
    "validation_reason": "正文描述了工作流程，并提供了流程图，符合规范要求。",
    "tables": [],
    "images": [
      {
        "id": "img_001",
        "path": "/api/parse/fe2aaebb29a8f6dd2db3106446bd487a/assets/img_001.png",
        "alt": "图 1 软件工作主流程图",
        "caption": "图 1 软件工作主流程图"
      }
    ]
  },
  {
    "id": "req3",
    "node_id": "node_3_2_2",
    "title": "3.2.2 配置项初始化",
    "content": "配置项初始化功能需求见表2。",
    "content_html": "<p>配置项初始化功能需求见表2。</p><table class=\"req-table\">…</table>",
    "level": 3,
    "parent_id": "req9",
    "is_req": 1,
    "is_req_reason": "表格描述了初始化功能的具体输入输出与参数，需在软件中实现。",
    "validation_result": true,
    "validation_reason": "通过表格详细描述了配置项初始化功能需求，符合规范要求。",
    "tables": [
      {
        "id": "tbl_002",
        "headers": ["名称", "配置项初始化功能需求"],
        "rows": [
          ["标识", "TDG06E_CPU_INIT_CSCI"],
          ["条件", "产品上电，开始工作"],
          ["输出", "硬件外设参数完成配置：系统主频配置为80MHz…"]
        ],
        "caption": null
      }
    ],
    "images": []
  }
]
```
