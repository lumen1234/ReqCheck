from flask import Blueprint, request, jsonify
from app import app
from app.models import db, LLMConfig
import requests

config_bp = Blueprint('config', __name__)


def get_llm_config():
    """读取 LLM 配置，优先取数据库记录，否则 fallback 到 config.py 默认值"""
    record = LLMConfig.query.first()
    if record:
        return {
            'api_key': record.api_key,
            'base_url': record.base_url,
            'model': record.model,
        }
    return {
        'api_key': app.config['API_KEY_DEFAULT'],
        'base_url': app.config['API_URL_DEFAULT'],
        'model': app.config['API_MODEL_DEFAULT'],
    }


@config_bp.route('/api/config/llm', methods=['GET'])
def get_llm_config_route():
    return jsonify(get_llm_config())


@config_bp.route('/api/config/llm', methods=['PUT'])
def save_llm_config():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'error': 'Invalid JSON body'}), 400

    api_key = data.get('api_key', '').strip()
    base_url = data.get('base_url', '').strip()
    model = data.get('model', '').strip()

    if not api_key or not base_url or not model:
        return jsonify({'success': False, 'error': 'api_key, base_url, model are all required'}), 400

    record = LLMConfig.query.first()
    if record:
        record.api_key = api_key
        record.base_url = base_url
        record.model = model
    else:
        record = LLMConfig(api_key=api_key, base_url=base_url, model=model)
        db.session.add(record)

    db.session.commit()
    return jsonify({'success': True})


@config_bp.route('/api/config/llm/test', methods=['POST'])
def test_llm_config():
    cfg = get_llm_config()

    url = cfg['base_url'].rstrip('/') + '/chat/completions'
    headers = {
        'Authorization': f"Bearer {cfg['api_key']}",
        'Content-Type': 'application/json',
    }
    payload = {
        'model': cfg['model'],
        'messages': [{'role': 'user', 'content': 'Hello'}],
        'max_tokens': 16,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload,
                             timeout=app.config.get('API_TIMEOUT', 60))
        resp.raise_for_status()
        reply = resp.json()['choices'][0]['message']['content']
        return jsonify({'ok': True, 'model': cfg['model'], 'reply': reply})
    except requests.exceptions.RequestException as e:
        return jsonify({'ok': False, 'error': str(e)})
