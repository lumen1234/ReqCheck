from flask import Blueprint, request, jsonify
from app import app
import os
import json

export_bp = Blueprint('export', __name__)

@export_bp.route('/export', methods=['POST'])
def export_requirements():
    doc_id = request.json.get('doc_id')
    if not doc_id:
        return jsonify({'error': 'doc_id is required'}), 400
    
    # 查找文件
    filepath = None
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if filename.startswith(doc_id):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            break
    
    if not filepath:
        return jsonify({'error': 'Document not found'}), 404
    
    # 模拟需求数据（实际项目中应该从解析结果中获取）
    requirements = [
        {
            'id': 'req1',
            'title': '总体需求',
            'description': '项目的总体目标和要求',
            'parent_id': 'root'
        },
        {
            'id': 'req2',
            'title': '范围',
            'description': '项目的边界和包含内容',
            'parent_id': 'root'
        },
        {
            'id': 'req3',
            'title': '引用文档',
            'description': '相关的标准和规范',
            'parent_id': 'root'
        },
        {
            'id': 'req4',
            'title': '要求的状态和方式',
            'description': '需求的状态和验证方式',
            'parent_id': 'req5'
        },
        {
            'id': 'req5',
            'title': '需求',
            'description': '详细的功能和非功能需求',
            'parent_id': 'root'
        },
        {
            'id': 'req6',
            'title': '能力需求',
            'description': '系统需要具备的功能',
            'parent_id': 'req5'
        },
        {
            'id': 'req7',
            'title': '工作流程',
            'description': '系统的操作流程',
            'parent_id': 'req6'
        }
    ]
    
    # 导出为JSON
    export_file = f"{doc_id}_requirements.json"
    export_path = os.path.join(app.config['UPLOAD_FOLDER'], export_file)
    
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(requirements, f, ensure_ascii=False, indent=2)
    
    return jsonify({
        'export_file': export_file,
        'requirements': requirements
    })
