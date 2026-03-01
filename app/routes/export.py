from flask import Blueprint, request, jsonify, send_file
from app import app
from app.models import RequirementTree, ValidationResult
import os
import json

export_bp = Blueprint('export', __name__)

EXPORT_OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'export_results')

if not os.path.exists(EXPORT_OUTPUT_FOLDER):
    os.makedirs(EXPORT_OUTPUT_FOLDER)

@export_bp.route('/api/export/<doc_id>', methods=['GET'])
def export_requirements(doc_id):
    if not doc_id:
        return jsonify({'error': 'doc_id is required'}), 400
    
    req_tree = None
    
    parse_json_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'parse_results', 
        f'{doc_id}.json'
    )
    
    if os.path.exists(parse_json_file):
        with open(parse_json_file, 'r', encoding='utf-8') as f:
            req_tree = json.load(f)
    
    if not req_tree:
        requirement_tree = RequirementTree.query.filter_by(doc_id=doc_id).first()
        if not requirement_tree:
            return jsonify({'error': 'Requirement tree not found'}), 404
        req_tree = requirement_tree.tree_json
    
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
    
    validation_map = {}
    if validation_results:
        for vr in validation_results:
            validation_map[vr.get('id')] = vr
    
    requirements = []
    req_id_counter = 1
    
    def traverse_tree(node, parent_id):
        nonlocal req_id_counter
        req_id = f"req{req_id_counter}"
        req_id_counter += 1
        
        node_id = node.get('id', '')
        
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
        
        children = node.get('children') or []
        for child in children:
            traverse_tree(child, req_id)
    
    traverse_tree(req_tree, 'root')
    
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
    