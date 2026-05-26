import os

from flask import Flask, send_from_directory
from app.models import db

# 前端构建产物目录（frontend/npm run build 生成，不纳入 Git）
FRONTEND_DIST = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "frontend",
    "dist",
)

app = Flask(
    __name__,
    static_folder=FRONTEND_DIST,
    static_url_path="",
)
app.config.from_object('config')

from app.services.workspace import init_workspace_dirs

init_workspace_dirs(app)

# 初始化数据库
db.init_app(app)
with app.app_context():
    print(app.config['SQLALCHEMY_DATABASE_URI'])
    db.create_all()

from app.routes import upload, parse, validate, export

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_vue(path):
    dist_dir = app.static_folder
    # 去掉查询参数，避免 ?v= 等导致静态文件路径匹配失败
    if path and "?" in path:
        path = path.split("?", 1)[0]
    requested_path = os.path.join(dist_dir, path)

    # 文件存在 -> 返回对应静态文件
    if path and os.path.exists(requested_path):
        return send_from_directory(dist_dir, path)

    # 否则返回 Vue SPA 首页
    return send_from_directory(dist_dir, "index.html")