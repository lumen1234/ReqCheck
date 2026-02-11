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
API_KEY_DEFAULT = "sk-ba7862f60e3e460e88e17dad82e34982"
API_URL_DEFAULT = "https://api.deepseek.com"
API_MODEL_DEFAULT = "deepseek-chat"

API_TIMEOUT = 60  # 超时时间（秒）
