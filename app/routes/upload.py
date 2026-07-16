from flask import Blueprint, request, jsonify
from app import app
from app.models import db, Document, DocumentBatch, RequirementTree, ValidationResult
from app.services import project_service
from app.services.workspace import export_results_folder, parse_assets_folder, parse_results_folder, validate_results_folder
import os
import hashlib
import uuid

upload_bp = Blueprint('upload', __name__)


def compute_file_hash(filepath):
	hash_md5 = hashlib.md5()
	with open(filepath, 'rb') as f:
		for chunk in iter(lambda: f.read(8192), b''):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()


def allowed_file(filename):
	# 过滤 Word 临时锁定文件（~$ 开头）
	if filename.startswith('~$'):
		return False
	return '.' in filename and filename.rsplit('.',1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def _file_type(filename, default='other'):
	return filename.rsplit('.',1)[1].lower() if '.' in filename else default


def _move_uploaded_file(temp_filepath, final_filepath):
	"""将临时文件落到最终路径。Windows 上目标已存在时 os.rename 会失败，需先删除。"""
	if os.path.exists(final_filepath):
		os.remove(final_filepath)
	os.rename(temp_filepath, final_filepath)


def _batch_document_to_dict(doc):
	return {
		'doc': doc.batch_order,
		'doc_id': doc.id,
		'id': doc.id,
		'filename': doc.filename,
		'relative_path': doc.original_relative_path or doc.filename,
		'file_type': doc.file_type,
		'status': doc.status or '已上传',
		'upload_time': doc.upload_time.isoformat() if doc.upload_time else None,
		'source': 'local',
	}


@upload_bp.route('/api/upload', methods=['POST'])
def upload_file():
	if 'file' not in request.files:
		return jsonify({'error': 'No file part'}),400
	file = request.files['file']
	if file.filename == '':
		return jsonify({'error': 'No selected file'}),400
	if not allowed_file(file.filename):
		return jsonify({'error': 'File type not allowed'}),400

	file_type = request.form.get('file_type', 'other')
	temp_filepath = None
	try:
		os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
		temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{uuid.uuid4()}_{file.filename}')
		file.save(temp_filepath)
		doc_id = compute_file_hash(temp_filepath)

		existing_doc = Document.query.filter_by(id=doc_id).first()
		if existing_doc and os.path.exists(existing_doc.file_path):
			os.remove(temp_filepath)
			return jsonify({'doc_id': existing_doc.id, 'filename': existing_doc.filename, 'file_type': existing_doc.file_type, 'filepath': existing_doc.file_path, 'cached': True, 'source': 'local', 'message': '文件已存在，返回已有文档'})

		if existing_doc:
			db.session.delete(existing_doc)
			db.session.commit()

		final_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f'{doc_id}_{file.filename}')
		_move_uploaded_file(temp_filepath, final_filepath)
		document = Document(id=doc_id, filename=file.filename, file_type=file_type, file_path=final_filepath)
		db.session.add(document)
		db.session.commit()
		return jsonify({'doc_id': doc_id, 'filename': file.filename, 'file_type': file_type, 'filepath': final_filepath, 'cached': False, 'source': 'local'})
	except Exception as e:
		import traceback
		traceback.print_exc()
		if temp_filepath and os.path.exists(temp_filepath):
			os.remove(temp_filepath)
		return jsonify({'error': str(e)}),500


@upload_bp.route('/api/upload/folder', methods=['POST'])
def upload_folder():
	files = request.files.getlist('files')
	if not files:
		return jsonify({'error': 'No files part'}),400

	relative_paths = request.form.getlist('relative_paths')
	folder_name = request.form.get('folder_name') or '文件夹上传'
	file_items = []
	skipped = []
	for index, file in enumerate(files):
		if not file or file.filename == '':
			continue
		relative_path = relative_paths[index] if index < len(relative_paths) else file.filename
		display_name = os.path.basename(relative_path.replace('\\', '/')) or file.filename
		if not allowed_file(display_name):
			skipped.append(display_name)
			continue
		file_items.append((relative_path, display_name, file))

	if not file_items:
		return jsonify({'error': '文件夹中未识别到可解析的需求规格文档', 'skipped': skipped}),400

	file_items.sort(key=lambda item: item[0].lower())
	batch_id = uuid.uuid4().hex
	db.session.add(DocumentBatch(id=batch_id, name=folder_name, status='已上传'))
	uploaded_docs = []
	temp_paths = []
	try:
		os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
		for order, (relative_path, display_name, file) in enumerate(file_items, start=1):
			temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{uuid.uuid4()}_{display_name}')
			temp_paths.append(temp_filepath)
			file.save(temp_filepath)
			doc_id = compute_file_hash(temp_filepath)
			existing_doc = Document.query.filter_by(id=doc_id).first()
			cached = bool(existing_doc and os.path.exists(existing_doc.file_path))
			if cached:
				os.remove(temp_filepath)
				temp_paths.remove(temp_filepath)
				document = existing_doc
				document.filename = display_name
				document.batch_id = batch_id
				document.batch_order = order
				document.original_relative_path = relative_path
			else:
				if existing_doc:
					db.session.delete(existing_doc)
					db.session.flush()
				final_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f'{doc_id}_{display_name}')
				_move_uploaded_file(temp_filepath, final_filepath)
				temp_paths.remove(temp_filepath)
				document = Document(id=doc_id, filename=display_name, file_type=_file_type(display_name), file_path=final_filepath, batch_id=batch_id, batch_order=order, original_relative_path=relative_path)
				db.session.add(document)
			uploaded_docs.append({'doc': order, 'doc_id': doc_id, 'id': doc_id, 'filename': display_name, 'relative_path': relative_path, 'file_type': document.file_type, 'cached': cached, 'source': 'local'})
		db.session.commit()
		return jsonify({'batch_id': batch_id, 'doc_id': batch_id, 'batch_name': folder_name, 'filename': folder_name, 'doc_count': len(uploaded_docs), 'documents': uploaded_docs, 'skipped': skipped, 'source': 'local_batch', 'kind': 'batch'})
	except Exception as e:
		db.session.rollback()
		import traceback
		traceback.print_exc()
		for path in temp_paths:
			if os.path.exists(path):
				os.remove(path)
		return jsonify({'error': str(e)}),500


@upload_bp.route('/api/batches/<batch_id>', methods=['GET'])
def get_batch(batch_id):
	batch = DocumentBatch.query.filter_by(id=batch_id).first()
	if batch:
		documents = Document.query.filter_by(batch_id=batch_id).order_by(Document.batch_order.asc()).all()
		return jsonify({'batch_id': batch.id, 'doc_id': batch.id, 'batch_name': batch.name, 'filename': batch.name, 'status': batch.status or '已上传', 'upload_time': batch.upload_time.isoformat() if batch.upload_time else None, 'doc_count': len(documents), 'documents': [_batch_document_to_dict(doc) for doc in documents], 'source': 'local_batch', 'kind': 'batch'})

	# UniPortal 共享卷项目文件夹：扫描 item 下全部支持文档
	portal_project_id = request.args.get('portal_project_id') or None
	uniportal_batch = project_service.get_uniportal_batch_detail(batch_id, portal_project_id=portal_project_id)
	if uniportal_batch:
		return jsonify(uniportal_batch)
	return jsonify({'error': 'Batch not found'}),404


def _remove_workspace_artifacts(doc_id, deleted_files, errors, *, include_batch_export=False):
	for path in (
		os.path.join(parse_results_folder(app), f'{doc_id}.json'),
		os.path.join(validate_results_folder(app), f'validation_{doc_id}.json'),
		os.path.join(export_results_folder(app), f'export_{doc_id}.json'),
	):
		if os.path.exists(path):
			os.remove(path)
			deleted_files.append(path)
	if include_batch_export:
		batch_export = os.path.join(export_results_folder(app), f'export_batch_{doc_id}.json')
		if os.path.exists(batch_export):
			os.remove(batch_export)
			deleted_files.append(batch_export)
	try:
		from app.parsers.asset_store import AssetStore
		assets_dir = parse_assets_folder(app)
		AssetStore.remove_doc_assets(doc_id, assets_dir)
		deleted_files.append(os.path.join(assets_dir, doc_id))
	except Exception as e:
		errors.append(f'删除解析资源失败: {str(e)}')


def _delete_single_document(document, deleted_files, errors):
	doc_id = document.id
	if document.file_path and os.path.exists(document.file_path):
		try:
			os.remove(document.file_path)
			deleted_files.append(document.file_path)
		except Exception as e:
			errors.append(f'删除原始文件失败: {str(e)}')
	for model in (RequirementTree, ValidationResult):
		record = model.query.filter_by(doc_id=doc_id).first()
		if record:
			db.session.delete(record)
	db.session.delete(document)
	_remove_workspace_artifacts(doc_id, deleted_files, errors)


@upload_bp.route('/api/delete/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
	if not doc_id:
		return jsonify({'error': 'doc_id is required'}),400
	if project_service.is_uniportal_item(doc_id):
		return jsonify({'error': 'UniPortal 来源的项目请到 UniPortal 删除'}),403

	deleted_files = []
	errors = []

	batch = DocumentBatch.query.filter_by(id=doc_id).first()
	if batch:
		try:
			for document in list(Document.query.filter_by(batch_id=batch.id).all()):
				_delete_single_document(document, deleted_files, errors)
			db.session.delete(batch)
			db.session.commit()
		except Exception as e:
			db.session.rollback()
			return jsonify({'error': f'删除文件夹记录失败: {str(e)}'}),500
		_remove_workspace_artifacts(doc_id, deleted_files, errors, include_batch_export=True)
		return jsonify({'success': True, 'doc_id': doc_id, 'kind': 'batch', 'deleted_files': deleted_files, 'errors': errors if errors else None})

	document = Document.query.filter_by(id=doc_id).first()
	if not document:
		return jsonify({'error': 'Document not found'}),404

	try:
		_delete_single_document(document, deleted_files, errors)
		db.session.commit()
	except Exception as e:
		db.session.rollback()
		return jsonify({'error': f'删除数据库记录失败: {str(e)}'}),500

	return jsonify({'success': True, 'doc_id': doc_id, 'deleted_files': deleted_files, 'errors': errors if errors else None})


@upload_bp.route('/api/documents', methods=['GET'])
def list_documents():
	portal_project_id = request.args.get('portal_project_id') or None
	entries = project_service.list_projects(portal_project_id=portal_project_id)
	documents = [project_service.project_entry_to_dict(entry) for entry in entries]
	for batch in DocumentBatch.query.order_by(DocumentBatch.upload_time.desc()).all():
		count = Document.query.filter_by(batch_id=batch.id).count()
		documents.append({'id': batch.id, 'doc_id': batch.id, 'filename': batch.name, 'project_name': batch.name, 'file_count': count, 'status': batch.status or '已上传', 'source': 'local_batch', 'kind': 'batch', 'upload_time': batch.upload_time.isoformat() if batch.upload_time else None, 'file_type': 'folder', 'file_path': None})
	documents.sort(key=lambda item: item.get('upload_time') or '', reverse=True)
	return jsonify({'documents': documents})
