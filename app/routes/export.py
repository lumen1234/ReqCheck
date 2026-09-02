from flask import Blueprint, request, jsonify, send_from_directory
from app import app
from app.models import Document, DocumentBatch, RequirementTree, ValidationResult
from app.services import project_service
from app.services.req_classifier import ensure_tree_classified, tree_needs_classification
from app.services.workspace import export_results_folder, parse_results_folder, validate_results_folder
import os
import json

export_bp = Blueprint('export', __name__)


@export_bp.route('/api/export/files/<path:filename>', methods=['GET'])
def download_export_file(filename):
	"""下载由导出接口持久化的 JSON；拒绝目录穿越和非 JSON 文件。"""
	safe_name = os.path.basename(filename)
	if safe_name != filename or not safe_name.lower().endswith('.json'):
		return jsonify({'error': 'Invalid export filename'}), 400
	export_dir = _export_output_folder()
	if not os.path.isfile(os.path.join(export_dir, safe_name)):
		return jsonify({'error': 'Export file not found'}), 404
	return send_from_directory(
		export_dir,
		safe_name,
		mimetype='application/json',
		as_attachment=True,
		download_name=safe_name,
	)


def _export_output_folder():
	return export_results_folder(app)


def _load_requirement_tree(doc_id):
	parse_json_file = os.path.join(parse_results_folder(app), f'{doc_id}.json')
	if os.path.exists(parse_json_file):
		with open(parse_json_file, 'r', encoding='utf-8') as f:
			return json.load(f)
	requirement_tree = RequirementTree.query.filter_by(doc_id=doc_id).first()
	return requirement_tree.tree_json if requirement_tree else None


def _load_validation_map(doc_id):
	validation_file = os.path.join(validate_results_folder(app), f'validation_{doc_id}.json')
	if not os.path.exists(validation_file):
		return {}
	with open(validation_file, 'r', encoding='utf-8') as f:
		validation_results = json.load(f)
	return {vr.get('id'): vr for vr in validation_results or []}


def _ensure_classified_saved(doc_id, req_tree):
	if tree_needs_classification(req_tree):
		ensure_tree_classified(req_tree)
		parse_json_file = os.path.join(parse_results_folder(app), f'{doc_id}.json')
		with open(parse_json_file, 'w', encoding='utf-8') as f:
			json.dump(req_tree, f, ensure_ascii=False, indent=2)


def _flatten_tree(req_tree, validation_map, doc_number=1, counter_start=1, node_id_prefix=''):
	requirements = []
	req_id_counter = counter_start

	def traverse_tree(node, parent_id):
		nonlocal req_id_counter
		content_blocks = node.get('content_blocks') or []

		if content_blocks:
			# 先导出标题节点自身（作为容器），再导出分块作为其子节点
			heading_req_id = f"req{req_id_counter}"
			req_id_counter += 1
			raw_node_id = node.get('id', '')
			heading_node_id = f'{node_id_prefix}{raw_node_id}' if node_id_prefix else raw_node_id
			validation = validation_map.get(raw_node_id, {})
			heading = {
				'id': heading_req_id,
				'doc': doc_number,
				'node_id': heading_node_id,
				'title': node.get('label', node.get('name', '')),
				'content': node.get('content', ''),
				'content_html': node.get('content_html', ''),
				'tables': node.get('tables') or [],
				'images': node.get('images') or [],
				'level': node.get('level', 0),
				'parent_id': parent_id,
				'is_req': 0,
				'validation_result': validation.get('result') if validation else None,
				'validation_reason': validation.get('reason', '') if validation else '',
				'type': validation.get('type', '') if validation else '',
				'test_difficulty': '',
				'needs_special_env': False,
				'needs_mock': False,
				'test_assessment_reason': '',
			}
			if node.get('is_req') == 1:
				heading['type'] = node.get('type', '')
			requirements.append(heading)

			block_parent_id = heading_req_id
			for block in content_blocks:
				req_id = f"req{req_id_counter}"
				req_id_counter += 1
				block_raw_id = f"{node.get('id', '')}_{block['id']}"
				block_node_id = f'{node_id_prefix}{block_raw_id}' if node_id_prefix else block_raw_id
				validation = validation_map.get(block_raw_id, {})
				requirement = {
					'id': req_id,
					'doc': doc_number,
					'node_id': block_node_id,
					'title': block.get('label', node.get('label', '')),
					'content': block.get('content', ''),
					'tables': block.get('tables') or [],
					'level': node.get('level', 0) + 1,
					'parent_id': block_parent_id,
					'is_req': 1,
					'validation_result': validation.get('result') if validation else None,
					'validation_reason': validation.get('reason', '') if validation else '',
					'type': validation.get('type', '') if validation else '',
					'test_difficulty': node.get('test_difficulty', ''),
					'needs_special_env': node.get('needs_special_env', False),
					'needs_mock': node.get('needs_mock', False),
					'test_assessment_reason': node.get('test_assessment_reason', ''),
				}
				requirements.append(requirement)
			for child in node.get('children') or []:
				traverse_tree(child, heading_req_id)
		else:
			req_id = f"req{req_id_counter}"
			req_id_counter +=1
			raw_node_id = node.get('id', '')
			node_id = f'{node_id_prefix}{raw_node_id}' if node_id_prefix else raw_node_id
			validation = validation_map.get(raw_node_id, {})
			requirement = {
				'id': req_id,
				'doc': doc_number,
				'node_id': node_id,
				'title': node.get('label', node.get('name', '')),
				'content': node.get('content', ''),
				'content_html': node.get('content_html', ''),
				'tables': node.get('tables') or [],
				'images': node.get('images') or [],
				'level': node.get('level',0),
				'parent_id': parent_id,
				'is_req': node.get('is_req',0),
				'validation_result': validation.get('result') if validation else None,
				'validation_reason': validation.get('reason', '') if validation else '',
				'type': validation.get('type', '') if validation else '',
				'test_difficulty': node.get('test_difficulty', ''),
				'needs_special_env': node.get('needs_special_env', False),
				'needs_mock': node.get('needs_mock', False),
				'test_assessment_reason': node.get('test_assessment_reason', ''),
			}
			if node.get('is_req') ==1:
				requirement['type'] = node.get('type', '')
			requirements.append(requirement)
			for child in node.get('children') or []:
				traverse_tree(child, req_id)

	traverse_tree(req_tree, 'root')
	return requirements, req_id_counter


@export_bp.route('/api/export/<doc_id>', methods=['GET'])
def export_requirements(doc_id):
	if not doc_id:
		return jsonify({'error': 'doc_id is required'}),400
	req_tree = _load_requirement_tree(doc_id)
	if not req_tree:
		return jsonify({'error': 'Requirement tree not found'}),404
	_ensure_classified_saved(doc_id, req_tree)
	requirements, _ = _flatten_tree(req_tree, _load_validation_map(doc_id), doc_number=1, counter_start=1)
	export_filename = f'export_{doc_id}.json'
	export_path = os.path.join(_export_output_folder(), export_filename)
	with open(export_path, 'w', encoding='utf-8') as f:
		json.dump(requirements, f, ensure_ascii=False, indent=2)
	portal_project_id = request.args.get('portal_project_id') or None
	uniportal_export_path = project_service.sync_export_to_uniportal(doc_id, requirements, portal_project_id=portal_project_id)
	return jsonify({'export_file': export_filename, 'export_path': export_path, 'uniportal_export_path': uniportal_export_path, 'uniportal_export_synced': uniportal_export_path is not None, 'total_requirements': len(requirements), 'requirements': requirements})


@export_bp.route('/api/export/batch/<batch_id>', methods=['GET'])
def export_batch_requirements(batch_id):
	portal_project_id = request.args.get('portal_project_id') or None
	batch = DocumentBatch.query.filter_by(id=batch_id).first()
	doc_entries = []
	batch_name = None
	if batch:
		batch_name = batch.name
		for document in Document.query.filter_by(batch_id=batch_id).order_by(Document.batch_order.asc()).all():
			doc_entries.append({'doc_id': document.id, 'filename': document.filename, 'batch_order': document.batch_order or 1})
	else:
		uniportal_batch = project_service.get_uniportal_batch_detail(batch_id, portal_project_id=portal_project_id)
		if not uniportal_batch:
			return jsonify({'error': 'Batch not found'}),404
		batch_name = uniportal_batch.get('batch_name') or batch_id
		for doc in uniportal_batch.get('documents') or []:
			doc_entries.append({'doc_id': doc['doc_id'], 'filename': doc['filename'], 'batch_order': doc.get('doc') or 1})

	if not doc_entries:
		return jsonify({'error': 'Batch has no documents'}),404

	requirements = []
	counter =1
	missing = []
	for document in doc_entries:
		req_tree = _load_requirement_tree(document['doc_id'])
		if not req_tree:
			missing.append(document['filename'])
			continue
		_ensure_classified_saved(document['doc_id'], req_tree)
		flattened, counter = _flatten_tree(req_tree, _load_validation_map(document['doc_id']), doc_number=document['batch_order'], counter_start=counter, node_id_prefix=f"{document['doc_id']}:")
		for item in flattened:
			item['doc_id'] = document['doc_id']
			item['source_filename'] = document['filename']
		requirements.extend(flattened)
	if not requirements:
		return jsonify({'error': 'No parsed requirement trees found', 'missing': missing}),404
	export_filename = f'export_batch_{batch_id}.json'
	export_path = os.path.join(_export_output_folder(), export_filename)
	with open(export_path, 'w', encoding='utf-8') as f:
		json.dump(requirements, f, ensure_ascii=False, indent=2)
	uniportal_export_path = None
	if not batch:
		uniportal_export_path = project_service.sync_export_to_uniportal(batch_id, requirements, portal_project_id=portal_project_id)
	return jsonify({'batch_id': batch_id, 'batch_name': batch_name, 'export_file': export_filename, 'export_path': export_path, 'doc_count': len(doc_entries), 'missing': missing, 'total_requirements': len(requirements), 'requirements': requirements, 'uniportal_export_path': uniportal_export_path, 'uniportal_export_synced': uniportal_export_path is not None})
