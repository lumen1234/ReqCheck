import os
import json

from flask import Blueprint, request, jsonify, send_file, make_response

from app import app
from app.models import db, Document as DocModel, DocumentBatch, RequirementTree
from app.parsers import parse_document_to_tree, compute_document_text_hash
from app.parsers.content_render import enrich_tree_display
from app.parsers.image_convert import load_browser_image_file, sniff_image_format
from app.services import project_service
from app.services.req_classifier import classify_requirement_tree, ensure_tree_classified, tree_needs_classification
from app.services.workspace import parse_assets_folder, parse_results_folder

_PARSER_VERSION =2
parse_bp = Blueprint('parse', __name__)


def _parse_output_folder():
	return parse_results_folder(app)


def _assets_folder():
	return parse_assets_folder(app)


def _cache_index_file():
	return os.path.join(_parse_output_folder(), 'cache_index.json')


def load_cache_index():
	path = _cache_index_file()
	if os.path.exists(path):
		with open(path, 'r', encoding='utf-8') as f:
			return json.load(f)
	return {}


def save_cache_index(cache_index):
	with open(_cache_index_file(), 'w', encoding='utf-8') as f:
		json.dump(cache_index, f, ensure_ascii=False, indent=2)


def _prepare_tree_for_response(req_tree, doc_id: str, classify: bool = True):
	if not req_tree:
		return req_tree
	enrich_tree_display(req_tree, doc_id)
	if classify and tree_needs_classification(req_tree):
		ensure_tree_classified(req_tree)
	return req_tree


def save_json_to_file(doc_id, tree):
	output_path = os.path.join(_parse_output_folder(), f'{doc_id}.json')
	tree['_parser_version'] = _PARSER_VERSION
	with open(output_path, 'w', encoding='utf-8') as f:
		json.dump(tree, f, ensure_ascii=False, indent=2)
	return output_path


def _persist_parse_result(doc_id, document, req_tree, text_hash, cache_index):
	output_path = save_json_to_file(doc_id, req_tree)
	cache_index[text_hash] = doc_id
	save_cache_index(cache_index)
	existing_tree = RequirementTree.query.filter_by(doc_id=doc_id).first()
	if existing_tree:
		existing_tree.tree_json = req_tree
	else:
		db.session.add(RequirementTree(doc_id=doc_id, tree_json=req_tree))
	if document:
		document.status = '已解析'
		if document.batch_id:
			batch = DocumentBatch.query.filter_by(id=document.batch_id).first()
			if batch:
				batch.status = '已解析'
	db.session.commit()
	return output_path


def _resolve_doc_for_parse(doc_id, portal_project_id=None):
	resolved = project_service.resolve_document(doc_id, portal_project_id=portal_project_id)
	if resolved:
		document = DocModel.query.filter_by(id=doc_id).first()
		return resolved.filepath, resolved.filename, document
	document = DocModel.query.filter_by(id=doc_id).first()
	if not document:
		return None, None, None
	if not os.path.exists(document.file_path):
		return None, None, document
	return document.file_path, document.filename, document


def parse_document_payload(doc_id, force=False, portal_project_id=None):
	parse_dir = _parse_output_folder()
	existing_json = os.path.join(parse_dir, f'{doc_id}.json')
	if not force and os.path.exists(existing_json):
		with open(existing_json, 'r', encoding='utf-8') as f:
			req_tree = json.load(f)
		if req_tree.get('_parser_version') == _PARSER_VERSION:
			needs_save = tree_needs_classification(req_tree)
			req_tree = _prepare_tree_for_response(req_tree, doc_id)
			if needs_save:
				save_json_to_file(doc_id, req_tree)
			return {'requirement_tree': req_tree, 'output_file': existing_json, 'cached': True}
		force = True

	filepath, filename, document = _resolve_doc_for_parse(doc_id, portal_project_id=portal_project_id)
	if not filepath:
		raise FileNotFoundError('Document not found')
	text_hash = compute_document_text_hash(filepath)
	cache_index = load_cache_index()
	if force:
		from app.parsers.asset_store import AssetStore
		AssetStore.remove_doc_assets(doc_id, _assets_folder())
	if not force and text_hash in cache_index:
		cached_doc_id = cache_index[text_hash]
		cached_json = os.path.join(parse_dir, f'{cached_doc_id}.json')
		if os.path.exists(cached_json):
			with open(cached_json, 'r', encoding='utf-8') as f:
				req_tree = json.load(f)
			if req_tree.get('_parser_version') == _PARSER_VERSION:
				req_tree['label'] = filename
				req_tree = _prepare_tree_for_response(req_tree, doc_id)
				output_path = _persist_parse_result(doc_id, document, req_tree, text_hash, cache_index)
				return {'requirement_tree': req_tree, 'output_file': output_path, 'cached': True, 'cached_from': cached_doc_id}
	req_tree = parse_document_to_tree(filepath=filepath, filename=filename, doc_id=doc_id, assets_base_folder=_assets_folder())
	classify_requirement_tree(req_tree)
	output_path = _persist_parse_result(doc_id, document, req_tree, text_hash, cache_index)
	return {'requirement_tree': req_tree, 'output_file': output_path, 'cached': False}


@parse_bp.route('/api/parse/<doc_id>', methods=['GET'])
def parse_document(doc_id):
	if not doc_id:
		return jsonify({'error': 'doc_id is required'}),400
	force = request.args.get('force', '').lower() in ('1', 'true', 'yes')
	portal_project_id = request.args.get('portal_project_id') or None
	try:
		return jsonify(parse_document_payload(doc_id, force=force, portal_project_id=portal_project_id))
	except FileNotFoundError:
		return jsonify({'error': 'Document not found'}),404
	except ValueError as e:
		return jsonify({'error': str(e)}),422
	except Exception as e:
		import traceback
		traceback.print_exc()
		msg = str(e)
		# 去掉外层「解析失败」重复包装，便于前端直接展示
		if msg.startswith('解析失败:'):
			msg = msg[len('解析失败:'):].strip()
		status = 401 if ('API Key' in msg or '401' in msg or 'Authorization' in msg) else 500
		return jsonify({'error': f'解析失败: {msg}'}), status


@parse_bp.route('/api/parse/batch/<batch_id>', methods=['GET'])
def parse_batch(batch_id):
	force = request.args.get('force', '').lower() in ('1', 'true', 'yes')
	portal_project_id = request.args.get('portal_project_id') or None
	batch = DocumentBatch.query.filter_by(id=batch_id).first()
	doc_entries = []
	batch_name = None
	if batch:
		batch_name = batch.name
		for document in DocModel.query.filter_by(batch_id=batch_id).order_by(DocModel.batch_order.asc()).all():
			doc_entries.append({'doc': document.batch_order, 'doc_id': document.id, 'filename': document.filename})
	else:
		uniportal_batch = project_service.get_uniportal_batch_detail(batch_id, portal_project_id=portal_project_id)
		if not uniportal_batch:
			return jsonify({'error': 'Batch not found'}),404
		batch_name = uniportal_batch.get('batch_name') or batch_id
		for doc in uniportal_batch.get('documents') or []:
			doc_entries.append({'doc': doc.get('doc'), 'doc_id': doc['doc_id'], 'filename': doc['filename']})

	results = []
	errors = []
	for document in doc_entries:
		try:
			payload = parse_document_payload(document['doc_id'], force=force, portal_project_id=portal_project_id)
			results.append({**document, **payload})
		except Exception as e:
			errors.append({**document, 'error': str(e)})
	return jsonify({'batch_id': batch_id, 'batch_name': batch_name, 'doc_count': len(doc_entries), 'parsed_count': len(results), 'failed_count': len(errors), 'documents': results, 'errors': errors})


@parse_bp.route('/api/parse/<doc_id>/assets/<filename>', methods=['GET'])
def get_parse_asset(doc_id, filename):
	safe_name = os.path.basename(filename)
	asset_path = os.path.join(_assets_folder(), doc_id, 'assets', safe_name)
	if not os.path.isfile(asset_path):
		return jsonify({'error': 'Asset not found'}),404
	try:
		data, out_ext = load_browser_image_file(asset_path)
	except OSError:
		return jsonify({'error': 'Asset not readable'}),500
	if sniff_image_format(data) not in ('png', 'jpeg', 'gif'):
		return jsonify({'error': 'Image format not supported in browser; re-parse with force=1'}),415
	ext = out_ext.lower() if out_ext.startswith('.') else f'.{out_ext.lower()}'
	mimetype = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp', '.svg': 'image/svg+xml'}.get(ext, 'image/png')
	resp = make_response(data)
	resp.headers['Content-Type'] = mimetype
	resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
	resp.headers['Pragma'] = 'no-cache'
	resp.headers['Content-Length'] = str(len(data))
	return resp


@parse_bp.route('/api/parse/<doc_id>/download', methods=['GET'])
def download_parse_result(doc_id):
	output_path = os.path.join(_parse_output_folder(), f'{doc_id}.json')
	if not os.path.exists(output_path):
		return jsonify({'error': 'File not found'}),404
	return send_file(output_path, mimetype='application/json', as_attachment=True, download_name=f'parse_result_{doc_id}.json')


@parse_bp.route('/api/parse/results', methods=['GET'])
def list_parse_results():
	parse_dir = _parse_output_folder()
	files = []
	if not os.path.isdir(parse_dir):
		return jsonify({'results': files})
	for filename in os.listdir(parse_dir):
		if filename.endswith('.json') and filename != 'cache_index.json':
			filepath = os.path.join(parse_dir, filename)
			files.append({'filename': filename, 'doc_id': filename.replace('.json', ''), 'size': os.path.getsize(filepath), 'created_time': os.path.getctime(filepath)})
	return jsonify({'results': files})
