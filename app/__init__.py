import os

from flask import Flask, send_from_directory
from app.models import db

app = Flask(
    __name__,
    static_folder="dist",
    static_url_path=""
)
app.config.from_object('config')

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
    requested_path = os.path.join(dist_dir, path)

    # 文件存在 -> 返回对应静态文件
    if path and os.path.exists(requested_path):
        return send_from_directory(dist_dir, path)

    # 否则返回 Vue SPA 首页
    return send_from_directory(dist_dir, "index.html")