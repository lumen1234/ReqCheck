from flask import Blueprint, request, jsonify
from app import app
from app.models import RequirementTree
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
    
    # 从数据库中获取实际的需求树数据
    requirement_tree = RequirementTree.query.filter_by(doc_id=doc_id).first()
    if not requirement_tree:
        return jsonify({'error': 'Requirement tree not found'}), 404
    
    # 将树形结构转换为导出格式
    req_tree = requirement_tree.tree_json
    requirements = []
    req_id_counter = 1
    
    def traverse_tree(node, parent_id):
        nonlocal req_id_counter
        req_id = f"req{req_id_counter}"
        req_id_counter += 1
        
        # 创建需求对象
        requirement = {
            'id': req_id,
            'title': node['name'],
            'description': node.get('original_text', node['name']),
            'content': node.get('content', ''),
            'parent_id': parent_id
        }
        requirements.append(requirement)
        
        # 递归处理子节点
        for child in node.get('children', []):
            traverse_tree(child, req_id)
    
    # 开始遍历需求树
    traverse_tree(req_tree, 'root')
    
    # 导出为JSON
    export_file = f"{doc_id}_requirements.json"
    export_path = os.path.join(app.config['UPLOAD_FOLDER'], export_file)
    
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(requirements, f, ensure_ascii=False, indent=2)
    
    return jsonify({
        'export_file': export_file,
        'requirements': requirements
    })
