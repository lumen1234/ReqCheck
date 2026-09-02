import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# UniPortal 集成：私有工作区（上传 + 所有生成物）
LOCAL_WORKSPACES_DIR = os.environ.get(
    "LOCAL_WORKSPACES_DIR",
    os.path.join(BASE_DIR, "local_workspaces"),
)
# UniPortal 共享卷（docker 挂载 /data/uniportal；导出 JSON 需读写权限，勿加 :ro）
UNIPORTAL_STORAGE_PATH = os.environ.get("UNIPORTAL_STORAGE_PATH") or None
# 导出 JSON 写入共享卷时，落在各 item 目录下的子目录名
UNIPORTAL_EXPORT_SUBDIR = os.environ.get("UNIPORTAL_EXPORT_SUBDIR", "document-validator")
# 共享卷导出 JSON 文件名（固定名；本地下载/缓存仍用 export_{doc_id}.json）
UNIPORTAL_EXPORT_FILENAME = os.environ.get("UNIPORTAL_EXPORT_FILENAME", "requirement.json")

UPLOAD_FOLDER = os.path.join(LOCAL_WORKSPACES_DIR, "uploads")
PARSE_RESULTS_FOLDER = os.path.join(LOCAL_WORKSPACES_DIR, "parse_results")
PARSE_ASSETS_FOLDER = os.path.join(LOCAL_WORKSPACES_DIR, "parse_assets")
VALIDATE_RESULTS_FOLDER = os.path.join(LOCAL_WORKSPACES_DIR, "validate_results")
EXPORT_RESULTS_FOLDER = os.path.join(LOCAL_WORKSPACES_DIR, "export_results")

APPENDICES_FOLDER = os.path.join(BASE_DIR, "appendices")
ALLOWED_EXTENSIONS = {"txt", "docx", "md", "markdown"}

SECRET_KEY = "your-secret-key-here"
DEBUG = True

# 数据库配置
SQLALCHEMY_DATABASE_URI = "sqlite:///req_validator.db"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# 大模型API配置
API_KEY_DEFAULT = os.environ.get("API_KEY_DEFAULT", "")
API_URL_DEFAULT = "https://api.deepseek.com"
API_MODEL_DEFAULT = "deepseek-chat"

API_TIMEOUT = 270

# 对外访问地址，用于 MCP 工具返回可由 Agent 下载的文件 URL。
# Docker 默认映射宿主机 8001 -> 容器 5000。
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8001").rstrip("/")

# 本地直接运行默认监听 8001；Docker Compose 会显式覆盖为容器内 5000。
SERVER_PORT = int(os.environ.get("SERVER_PORT", "8001"))

# MCP 的 JSON-RPC 请求需要携带 Base64 文件内容。默认限制原始文件为 20 MiB，
# 避免一次工具调用占用过多内存；可按部署环境调整。
MAX_MCP_UPLOAD_BYTES = int(os.environ.get("MAX_MCP_UPLOAD_BYTES", str(20 * 1024 * 1024)))
