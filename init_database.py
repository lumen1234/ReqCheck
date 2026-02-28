# init_database.py
from app import app, db
from app.models import Document, RequirementTree, ValidationResult

with app.app_context():
    print("开始初始化数据库...")
    try:
        # 创建所有表
        db.create_all()
        print("数据库表结构创建成功！")
        
        # 验证表是否创建
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"创建的表: {tables}")
        
    except Exception as e:
        print(f"初始化失败: {e}")