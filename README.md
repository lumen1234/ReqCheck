# ReqCheck - 需求文档验证系统

基于Flask的Web应用，用于需求文档验证和分析。支持上传需求规格说明文档，使用大模型验证需求是否符合GB/T 8567-2006附录J规范。

## 功能特性

- **文档上传**: 支持 .docx 和 .txt 格式的需求文档
- **智能解析**: 自动提取文档标题和内容，构建需求树结构
- **AI验证**: 使用DeepSeek大模型验证需求是否符合规范
- **JSON导出**: 将需求树导出为JSON格式，便于后续处理
- **历史管理**: 查看和管理已上传的文档

## 技术栈

- **后端**: Flask + Flask-SQLAlchemy
- **数据库**: SQLite
- **文档处理**: python-docx
- **AI验证**: DeepSeek API

## 项目结构

```
req_com1/
├── app/
│   ├── __init__.py          # Flask应用初始化
│   ├── models.py            # 数据库模型
│   └── routes/
│       ├── __init__.py      # 路由注册
│       ├── upload.py        # 文件上传
│       ├── parse.py         # 文档解析
│       ├── validate.py      # 需求验证
│       ├── export.py        # JSON导出
│       └── history.py       # 历史记录
├── appendices/
│   └── 438C-2021附录J.txt   # 规范附录
├── uploads/                 # 上传文件目录
├── config.py                # 配置文件
├── run.py                   # 启动文件
└── requirements.txt         # 依赖列表
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动应用

```bash
python run.py
```

应用将在 http://127.0.0.1:5000 启动

### 3. 使用API

#### 上传文档
```bash
curl -X POST -F "file=@your_requirements.docx" http://127.0.0.1:5000/upload
```

#### 解析文档
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"doc_id": "your_doc_id"}' \
  http://127.0.0.1:5000/parse
```

#### 验证需求
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"doc_id": "your_doc_id"}' \
  http://127.0.0.1:5000/validate
```

#### 导出JSON
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"doc_id": "your_doc_id"}' \
  http://127.0.0.1:5000/export
```

#### 获取文档列表
```bash
curl http://127.0.0.1:5000/documents
```

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/upload` | POST | 上传文档 |  
| `/parse` | POST | 解析文档 | // 解析文档后，返回需求树
| `/validate` | POST | 验证需求 |
| `/export` | POST | 导出JSON |
| `/documents` | GET | 获取文档列表 |
| `/document/<doc_id>` | GET | 获取文档详情 |

## 配置

在 `config.py` 中可以配置:

- `UPLOAD_FOLDER`: 上传文件存储目录
- `ALLOWED_EXTENSIONS`: 允许的文件类型
- `API_KEY_DEFAULT`: DeepSeek API密钥
- `API_URL_DEFAULT`: DeepSeek API地址
- `SQLALCHEMY_DATABASE_URI`: 数据库连接串

## 测试

运行接口测试:
```bash
python test_api.py
```

## 许可证

MIT License
