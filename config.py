import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
APPENDICES_FOLDER = os.path.join(BASE_DIR, 'appendices')
ALLOWED_EXTENSIONS = {'txt', 'docx'}

SECRET_KEY = 'your-secret-key-here'
DEBUG = True

# 数据库配置
SQLALCHEMY_DATABASE_URI = 'sqlite:///req_validator.db'  # SQLite
SQLALCHEMY_TRACK_MODIFICATIONS = False  # 禁用修改跟踪，提高性能

# 大模型API配置
API_KEY_DEFAULT = "76a878dc-4905-44c3-858c-8ef33006250f"
API_URL_DEFAULT = "https://ark.cn-beijing.volces.com/api/v3"
API_MODEL_DEFAULT = "ep-20250914142037-7zmnt"
API_TIMEOUT = 30  # 超时时间（秒）
