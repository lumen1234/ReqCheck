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
API_KEY_DEFAULT = "sk-ba7862f60e3e460e88e17dad82e34982"
API_URL_DEFAULT = "https://api.deepseek.com"
API_MODEL_DEFAULT = "deepseek-chat"

API_TIMEOUT = 270
