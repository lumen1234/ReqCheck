import os
import sys
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath('.'))

from app.routes.parse import parse_document
from flask import Flask, request, jsonify

# 创建一个测试Flask应用
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '.'

# 注册parse蓝图
from app.routes.parse import parse_bp
app.register_blueprint(parse_bp)

# 测试直接调用parse_document函数
def test_direct_parse():
    print("直接测试parse_document函数...")
    
    # 首先，我们需要模拟一个文档上传，生成一个doc_id
    # 这里我们直接使用文件路径作为测试
    filepath = "MEMS陀螺软件需求规格说明.docx"
    
    if not os.path.exists(filepath):
        print(f"文件不存在: {filepath}")
        return
    
    # 为了测试，我们需要创建一个临时的Document记录
    from app.models import db, Document as DocModel
    
    # 初始化数据库
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    with app.app_context():
        # 初始化数据库
        db.init_app(app)
        db.create_all()
        
        # 生成UUID作为文档ID
        import uuid
        doc_id = str(uuid.uuid4())
        
        # 创建一个测试文档记录
        doc = DocModel(
            id=doc_id,
            filename='MEMS陀螺软件需求规格说明.docx',
            file_type='需求规格说明',
            file_path=filepath,
            status='已上传'
        )
        db.session.add(doc)
        db.session.commit()
        
        print(f"创建测试文档记录，ID: {doc_id}")
        
        # 模拟请求数据
        test_request = {
            'doc_id': doc_id
        }
        
        # 使用Flask测试客户端
        client = app.test_client()
        
        # 发送POST请求到/parse端点
        response = client.post('/parse', json=test_request)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应数据: {response.data.decode('utf-8')}")
        
        # 清理测试数据
        db.session.delete(doc)
        db.session.commit()

if __name__ == "__main__":
    test_direct_parse()
