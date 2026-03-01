from flask import Blueprint, request, jsonify
from app import app
from app.models import db, Document, RequirementTree, ValidationResult
import os
import hashlib

upload_bp = Blueprint('upload', __name__)


def compute_file_hash(filepath):
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


@upload_bp.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    file_type = request.form.get('file_type', 'other')
    
    temp_filepath = None
    try:
        import uuid
        temp_filename = f"temp_{uuid.uuid4()}_{file.filename}"
        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        file.save(temp_filepath)
        
        file_hash = compute_file_hash(temp_filepath)
        doc_id = file_hash
        
        existing_doc = Document.query.filter_by(id=doc_id).first()
        
        if existing_doc and os.path.exists(existing_doc.file_path):
            os.remove(temp_filepath)
            
            return jsonify({
                'doc_id': existing_doc.id,
                'filename': existing_doc.filename,
                'file_type': existing_doc.file_type,
                'filepath': existing_doc.file_path,
                'cached': True,
                'message': '文件已存在，返回已有文档'
            })
        
        if existing_doc:
            db.session.delete(existing_doc)
            db.session.commit()
        
        filename = f"{doc_id}_{file.filename}"
        final_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        os.rename(temp_filepath, final_filepath)
        
        document = Document(
            id=doc_id,
            filename=file.filename,
            file_type=file_type,
            file_path=final_filepath
        )
        db.session.add(document)
        db.session.commit()
        
        return jsonify({
            'doc_id': doc_id,
            'filename': file.filename,
            'file_type': file_type,
            'filepath': final_filepath,
            'cached': False
        })
        
    except Exception as e:
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        return jsonify({'error': str(e)}), 500

@upload_bp.route('/api/delete/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    if not doc_id:
        return jsonify({'error': 'doc_id is required'}), 400
    
    # 查找文档
    document = Document.query.filter_by(id=doc_id).first()
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    deleted_files = []
    errors = []
    
    # 1. 删除上传的原始文件
    if document.file_path and os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
            deleted_files.append(document.file_path)
        except Exception as e:
            errors.append(f"删除原始文件失败: {str(e)}")
    
    # 2. 删除数据库记录
    try:
        db.session.delete(document)
        
        # 3. 删除相关的需求树记录
        req_tree = RequirementTree.query.filter_by(doc_id=doc_id).first()
        if req_tree:
            db.session.delete(req_tree)
        
        # 4. 删除相关的验证结果记录
        validation_result = ValidationResult.query.filter_by(doc_id=doc_id).first()
        if validation_result:
            db.session.delete(validation_result)
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'删除数据库记录失败: {str(e)}'}), 500
    
    # 5. 删除相关的JSON文件（可选）
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    # 删除parse结果
    parse_file = os.path.join(base_dir, 'parse_results', f'{doc_id}.json')
    if os.path.exists(parse_file):
        try:
            os.remove(parse_file)
            deleted_files.append(parse_file)
        except Exception as e:
            errors.append(f"删除parse结果失败: {str(e)}")
    
    # 删除validation结果
    validation_file = os.path.join(base_dir, '..', 'validate_results', f'validation_{doc_id}.json')
    if os.path.exists(validation_file):
        try:
            os.remove(validation_file)
            deleted_files.append(validation_file)
        except Exception as e:
            errors.append(f"删除validation结果失败: {str(e)}")
    
    # 删除export结果
    export_file = os.path.join(base_dir, 'export_results', f'export_{doc_id}.json')
    if os.path.exists(export_file):
        try:
            os.remove(export_file)
            deleted_files.append(export_file)
        except Exception as e:
            errors.append(f"删除export结果失败: {str(e)}")
    
    return jsonify({
        'success': True,
        'doc_id': doc_id,
        'deleted_files': deleted_files,
        'errors': errors if errors else None
    })

@upload_bp.route('/api/documents', methods=['GET'])
def list_documents():
    documents = Document.query.all()
    return jsonify({
        'documents': [
            {
                'id': doc.id,
                'filename': doc.filename,
                'file_type': doc.file_type,
                'file_path': doc.file_path,
                'upload_time': doc.upload_time.isoformat() if doc.upload_time else None,
                'status': doc.status
            }
            for doc in documents
        ]
    })

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
