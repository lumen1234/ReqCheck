from flask import Flask
from app.models import db

app = Flask(__name__)
app.config.from_object('config')

# 初始化数据库
db.init_app(app)
with app.app_context():
    print(app.config['SQLALCHEMY_DATABASE_URI'])
    db.create_all()

from app.routes import upload, parse, validate, export
