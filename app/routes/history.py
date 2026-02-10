from flask import Blueprint, request, jsonify
from app.models import Document, RequirementTree, ValidationResult

history_bp = Blueprint('history', __name__)

@history_bp.route('/documents', methods=['GET'])
def get_documents():
    """获取所有文档列表"""
    documents = Document.query.all()
    result = []
    for doc in documents:
        result.append({
            'id': doc.id,
            'filename': doc.filename,
            'file_type': doc.file_type,
            'upload_time': doc.upload_time.isoformat(),
            'status': doc.status
        })
    return jsonify({'documents': result})

@history_bp.route('/document/<doc_id>', methods=['GET'])
def get_document_detail(doc_id):
    """获取单个文档详情"""
    document = Document.query.filter_by(id=doc_id).first()
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    # 获取需求树
    trees = RequirementTree.query.filter_by(doc_id=doc_id).all()
    trees_data = [{'id': t.id, 'parse_time': t.parse_time.isoformat(), 'tree_json': t.tree_json} for t in trees]
    
    # 获取验证结果
    results = ValidationResult.query.filter_by(doc_id=doc_id).all()
    results_data = [{'id': r.id, 'validate_time': r.validate_time.isoformat(), 'result_json': r.result_json} for r in results]
    
    return jsonify({
        'document': {
            'id': document.id,
            'filename': document.filename,
            'file_type': document.file_type,
            'upload_time': document.upload_time.isoformat(),
            'status': document.status
        },
        'requirement_trees': trees_data,
        'validation_results': results_data
    })
