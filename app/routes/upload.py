from flask import Blueprint, request, jsonify
from app import app
from app.models import db, Document, RequirementTree, ValidationResult
from app.services import project_service
from app.services.workspace import (
    export_results_folder,
    parse_assets_folder,
    parse_results_folder,
    validate_results_folder,
)
import os
import hashlib

upload_bp = Blueprint('upload', __name__)


def compute_file_hash(filepath):
    hash_md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


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
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
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
                'source': 'local',
                'message': '文件已存在，返回已有文档',
            })

        if existing_doc:
            try:
                db.session.delete(existing_doc)
                db.session.commit()
            except Exception:
                import traceback
                traceback.print_exc()

        filename = f"{doc_id}_{file.filename}"
        final_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.rename(temp_filepath, final_filepath)

        document = Document(
            id=doc_id,
            filename=file.filename,
            file_type=file_type,
            file_path=final_filepath,
        )
        db.session.add(document)
        db.session.commit()

        return jsonify({
            'doc_id': doc_id,
            'filename': file.filename,
            'file_type': file_type,
            'filepath': final_filepath,
            'cached': False,
            'source': 'local',
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        return jsonify({'error': str(e)}), 500


@upload_bp.route('/api/delete/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    if not doc_id:
        return jsonify({'error': 'doc_id is required'}), 400

    if project_service.is_uniportal_item(doc_id):
        return jsonify({
            'error': 'UniPortal 来源的项目请到 UniPortal 删除',
        }), 403

    document = Document.query.filter_by(id=doc_id).first()
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    deleted_files = []
    errors = []

    if document.file_path and os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
            deleted_files.append(document.file_path)
        except Exception as e:
            errors.append(f"删除原始文件失败: {str(e)}")

    try:
        req_tree = RequirementTree.query.filter_by(doc_id=doc_id).first()
        if req_tree:
            db.session.delete(req_tree)

        validation_result = ValidationResult.query.filter_by(doc_id=doc_id).first()
        if validation_result:
            db.session.delete(validation_result)

        db.session.delete(document)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'删除数据库记录失败: {str(e)}'}), 500

    parse_file = os.path.join(parse_results_folder(app), f'{doc_id}.json')
    if os.path.exists(parse_file):
        try:
            os.remove(parse_file)
            deleted_files.append(parse_file)
        except Exception as e:
            errors.append(f"删除parse结果失败: {str(e)}")

    validation_file = os.path.join(validate_results_folder(app), f'validation_{doc_id}.json')
    if os.path.exists(validation_file):
        try:
            os.remove(validation_file)
            deleted_files.append(validation_file)
        except Exception as e:
            errors.append(f"删除validation结果失败: {str(e)}")

    export_file = os.path.join(export_results_folder(app), f'export_{doc_id}.json')
    if os.path.exists(export_file):
        try:
            os.remove(export_file)
            deleted_files.append(export_file)
        except Exception as e:
            errors.append(f"删除export结果失败: {str(e)}")

    try:
        from app.parsers.asset_store import AssetStore
        assets_dir = parse_assets_folder(app)
        AssetStore.remove_doc_assets(doc_id, assets_dir)
        deleted_files.append(os.path.join(assets_dir, doc_id))
    except Exception as e:
        errors.append(f"删除解析资源失败: {str(e)}")

    return jsonify({
        'success': True,
        'doc_id': doc_id,
        'deleted_files': deleted_files,
        'errors': errors if errors else None,
    })


@upload_bp.route('/api/documents', methods=['GET'])
def list_documents():
    portal_project_id = request.args.get('portal_project_id') or None
    entries = project_service.list_projects(portal_project_id=portal_project_id)
    return jsonify({
        'documents': [
            project_service.project_entry_to_dict(entry)
            for entry in entries
        ],
    })
