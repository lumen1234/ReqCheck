from flask import Blueprint, request, jsonify, send_file
from app import app
from app.models import db, Document as DocModel, RequirementTree
import os
import re
import json
import requests
import hashlib
from docx import Document

parse_bp = Blueprint('parse', __name__)

PARSE_OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'parse_results')
CACHE_INDEX_FILE = os.path.join(PARSE_OUTPUT_FOLDER, 'cache_index.json')

if not os.path.exists(PARSE_OUTPUT_FOLDER):
    os.makedirs(PARSE_OUTPUT_FOLDER)

def load_cache_index():
    """加载缓存索引"""
    if os.path.exists(CACHE_INDEX_FILE):
        with open(CACHE_INDEX_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache_index(cache_index):
    """保存缓存索引"""
    with open(CACHE_INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache_index, f, ensure_ascii=False, indent=2)

def compute_file_hash(filepath):
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def compute_text_hash(filepath):
    """计算文档文本内容的MD5哈希值（更准确检测相同文档）"""
    text = extract_text_from_docx(filepath)
    hash_md5 = hashlib.md5()
    hash_md5.update(text.encode('utf-8'))
    return hash_md5.hexdigest()

def extract_text_from_docx(filepath):
    doc = Document(filepath)
    text_lines = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            text_lines.append(text)
    return '\n'.join(text_lines)

def compute_text_hash(text):
    """计算文本内容的MD5哈希值"""
    hash_md5 = hashlib.md5()
    hash_md5.update(text.encode('utf-8'))
    return hash_md5.hexdigest()

def call_llm_api(prompt, model, api_key, api_url, retries=3):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    data = {
        'model': model,
        'messages': [
            {
                'role': 'system',
                'content': '你是一个专业的需求文档分析助手，擅长解析软件需求规格说明书。'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'temperature': 0.3,
        'max_tokens': 8000
    }
    
    for attempt in range(retries):
        try:
            session = requests.Session()
            response = session.post(
                api_url + '/chat/completions',
                headers=headers,
                json=data,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"API调用失败 (尝试 {attempt+1}/{retries}): {str(e)}")
            if attempt < retries - 1:
                import time
                time.sleep(2)
    
    return None

def parse_document_with_llm(text):
    prompt = f"""请解析以下软件需求规格说明文档，识别出所有标题和对应的内容。

请严格按照以下JSON格式返回，不要包含任何其他内容：
{{
  "tree": {{
    "id": "root",
    "label": "文档名称",
    "content": null,
    "level": 0,
    "v_status": true,
    "e_status": "pending",
    "children": [
      {{
        "id": "node_编号",
        "label": "标题名称",
        "content": "该标题下的具体内容，如果没有内容则为null",
        "level": 层级数字,
        "v_status": true,
        "e_status": "pass",
        "children": [
          {{
            "id": "node_父编号_子编号",
            "label": "子标题名称",
            "content": "子标题下的内容",
            "level": 层级数字,
            "v_status": true,
            "e_status": "pass",
            "children": null
          }}
        ]
      }}
    ]
  }}
}}

要求：
1. 根据标题编号确定层级关系（如1是一级，1.1是二级，1.1.1是三级）
2. 只在叶子节点（非标题节点）填写content，父标题节点的content为null
3. 返回纯JSON格式，不要有markdown代码块标记
4. 文档内容：

{text}

请返回JSON："""

    model = app.config.get('API_MODEL_DEFAULT', 'deepseek-chat')
    api_key = app.config.get('API_KEY_DEFAULT')
    api_url = app.config.get('API_URL_DEFAULT', 'https://api.deepseek.com')
    
    response = call_llm_api(prompt, model, api_key, api_url)
    
    if response:
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        elif response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()
        
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {str(e)}")
            print(f"尝试修复截断的JSON...")
            
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                try:
                    result = json.loads(match.group(0))
                    print("JSON修复成功!")
                    return result
                except:
                    pass
            
            print(f"原始响应: {response[:500]}")
    
    return None

def save_json_to_file(doc_id, tree):
    output_filename = f"{doc_id}.json"
    output_path = os.path.join(PARSE_OUTPUT_FOLDER, output_filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)
    
    return output_path

@parse_bp.route('/api/parse/<doc_id>', methods=['GET'])
def parse_document(doc_id):
    if not doc_id:
        return jsonify({'error': 'doc_id is required'}), 400
    
    # 检查是否已有解析结果
    existing_json = os.path.join(PARSE_OUTPUT_FOLDER, f"{doc_id}.json")
    if os.path.exists(existing_json):
        with open(existing_json, 'r', encoding='utf-8') as f:
            req_tree = json.load(f)
        return jsonify({
            'requirement_tree': req_tree,
            'output_file': existing_json,
            'cached': True
        })
    
    document = DocModel.query.filter_by(id=doc_id).first()
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    filepath = document.file_path
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found on disk'}), 404
    
    # 计算文档文本内容的哈希
    text_hash = compute_text_hash(filepath)
    print(f"文档内容哈希: {text_hash}")
    
    # 检查缓存
    cache_index = load_cache_index()
    
    # 如果有相同的文档被解析过，直接返回缓存结果
    if text_hash in cache_index:
        cached_doc_id = cache_index[text_hash]
        cached_json = os.path.join(PARSE_OUTPUT_FOLDER, f"{cached_doc_id}.json")
        if os.path.exists(cached_json):
            print(f"发现相同文档，已缓存 doc_id: {cached_doc_id}")
            
            # 复制缓存结果到新的doc_id
            with open(cached_json, 'r', encoding='utf-8') as f:
                req_tree = json.load(f)
            
            # 更新label为当前文档名
            req_tree['label'] = document.filename
            
            output_path = save_json_to_file(doc_id, req_tree)
            
            # 保存到数据库
            tree = RequirementTree(
                doc_id=doc_id,
                tree_json=req_tree
            )
            db.session.add(tree)
            
            if document:
                document.status = '已解析'
            
            db.session.commit()
            
            return jsonify({
                'requirement_tree': req_tree,
                'output_file': output_path,
                'cached': True,
                'cached_from': cached_doc_id
            })
    
    print("正在使用大模型API解析文档...")
    text = extract_text_from_docx(filepath)
    result = parse_document_with_llm(text)
    
    if result and 'tree' in result:
        req_tree = result['tree']
        print("大模型解析成功")
    else:
        return jsonify({'error': '大模型解析失败，请检查API配置或网络连接'}), 500
    
    output_path = save_json_to_file(doc_id, req_tree)
    print(f"JSON已保存到: {output_path}")
    
    # 更新缓存索引
    cache_index[text_hash] = doc_id
    save_cache_index(cache_index)
    
    tree = RequirementTree(
        doc_id=doc_id,
        tree_json=req_tree
    )
    db.session.add(tree)
    
    if document:
        document.status = '已解析'
    
    db.session.commit()
    
    return jsonify({
        'requirement_tree': req_tree,
        'output_file': output_path,
        'cached': False
    })

@parse_bp.route('/api/parse/<doc_id>/download', methods=['GET'])
def download_parse_result(doc_id):
    output_filename = f"{doc_id}.json"
    output_path = os.path.join(PARSE_OUTPUT_FOLDER, output_filename)
    
    if not os.path.exists(output_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(
        output_path,
        mimetype='application/json',
        as_attachment=True,
        download_name=f"parse_result_{doc_id}.json"
    )

@parse_bp.route('/api/parse/results', methods=['GET'])
def list_parse_results():
    files = []
    for filename in os.listdir(PARSE_OUTPUT_FOLDER):
        if filename.endswith('.json') and filename != 'cache_index.json':
            filepath = os.path.join(PARSE_OUTPUT_FOLDER, filename)
            files.append({
                'filename': filename,
                'doc_id': filename.replace('.json', ''),
                'size': os.path.getsize(filepath),
                'created_time': os.path.getctime(filepath)
            })
    return jsonify({'results': files})

@parse_bp.route('/api/parse/cache/clear', methods=['POST'])
def clear_cache():
    """清除解析缓存"""
    cache_index = load_cache_index()
    cache_index.clear()
    save_cache_index(cache_index)
    return jsonify({'success': True, 'message': '缓存已清除'})

@parse_bp.route('/api/parse/cache/stats', methods=['GET'])
def cache_stats():
    """查看缓存统计"""
    cache_index = load_cache_index()
    return jsonify({
        'cached_documents': len(cache_index),
        'cache_index': cache_index
    })
