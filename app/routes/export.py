from flask import Blueprint, request, jsonify, send_file
from app import app
from app.models import RequirementTree, ValidationResult
import os
import json

export_bp = Blueprint('export', __name__)

EXPORT_OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'export_results')

if not os.path.exists(EXPORT_OUTPUT_FOLDER):
    os.makedirs(EXPORT_OUTPUT_FOLDER)

@export_bp.route('/api/export', methods=['POST'])
def export_requirements():
    doc_id = request.json.get('doc_id')
    if not doc_id:
        return jsonify({'error': 'doc_id is required'}), 400
    
    req_tree = None
    
    # 1. 优先从JSON文件读取需求树
    parse_json_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'parse_results', 
        f'{doc_id}.json'
    )
    
    if os.path.exists(parse_json_file):
        with open(parse_json_file, 'r', encoding='utf-8') as f:
            req_tree = json.load(f)
    
    # 2. 如果JSON文件不存在，从数据库读取
    if not req_tree:
        requirement_tree = RequirementTree.query.filter_by(doc_id=doc_id).first()
        if not requirement_tree:
            return jsonify({'error': 'Requirement tree not found'}), 404
        req_tree = requirement_tree.tree_json
    
    # 3. 读取验证结果
    validation_results = None
    validation_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        '..', 
        'validate_results', 
        f'validation_{doc_id}.json'
    )
    
    if os.path.exists(validation_file):
        with open(validation_file, 'r', encoding='utf-8') as f:
            validation_results = json.load(f)
    
    # 4. 构建验证结果字典，方便匹配
    validation_map = {}
    if validation_results:
        for vr in validation_results:
            validation_map[vr.get('id')] = vr
    
    # 5. 将树形结构转换为导出格式，并合并验证结果
    requirements = []
    req_id_counter = 1
    
    def traverse_tree(node, parent_id):
        nonlocal req_id_counter
        req_id = f"req{req_id_counter}"
        req_id_counter += 1
        
        node_id = node.get('id', '')
        
        # 获取验证结果
        validation = validation_map.get(node_id, {})
        
        requirement = {
            'id': req_id,
            'node_id': node_id,
            'title': node.get('label', node.get('name', '')),
            'content': node.get('content', ''),
            'level': node.get('level', 0),
            'parent_id': parent_id,
            'validation_result': validation.get('result') if validation else None,
            'validation_reason': validation.get('reason', '') if validation else ''
        }
        requirements.append(requirement)
        
        # 递归处理子节点
        children = node.get('children') or []
        for child in children:
            traverse_tree(child, req_id)
    
    traverse_tree(req_tree, 'root')
    
    # 6. 导出为JSON
    export_filename = f"export_{doc_id}.json"
    export_path = os.path.join(EXPORT_OUTPUT_FOLDER, export_filename)
    
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(requirements, f, ensure_ascii=False, indent=2)
    
    return jsonify({
        'export_file': export_filename,
        'export_path': export_path,
        'total_requirements': len(requirements),
        'requirements': requirements
    })

@export_bp.route('/api/export/<doc_id>', methods=['GET'])
def export_requirements_get(doc_id):
    if not doc_id:
        return jsonify({'error': 'doc_id is required'}), 400
    
    # 读取已导出的文件
    export_filename = f"export_{doc_id}.json"
    export_path = os.path.join(EXPORT_OUTPUT_FOLDER, export_filename)
    
    if not os.path.exists(export_path):
        return jsonify({'error': 'Export file not found'}), 404
    
    return send_file(
        export_path,
        mimetype='application/json',
        as_attachment=True,
        download_name=f"requirements_{doc_id}.json"
    )

@export_bp.route('/api/export/list', methods=['GET'])
def list_exports():
    files = []
    for filename in os.listdir(EXPORT_OUTPUT_FOLDER):
        if filename.endswith('.json'):
            filepath = os.path.join(EXPORT_OUTPUT_FOLDER, filename)
            files.append({
                'filename': filename,
                'doc_id': filename.replace('export_', '').replace('.json', ''),
                'size': os.path.getsize(filepath),
                'created_time': os.path.getctime(filepath)
            })
    return jsonify({'exports': files})
