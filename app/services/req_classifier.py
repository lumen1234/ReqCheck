"""使用大模型判断需求节点是否需落实到代码实现（is_req）。"""
import json
import re
from typing import Any, Dict, List, Optional

from app import app
from app.models import LLMConfig
from app.routes.validate import call_deepseek_api, format_node_validation_content

BATCH_SIZE = 10

CLASSIFICATION_GUIDELINES = """
## 判断原则（必须遵守）
1. is_req=1：该节点描述的是需要在软件/代码中实现、验证或配置的具体需求，例如功能行为、接口、算法、性能指标、数据结构、状态机、错误处理、约束条件等。
2. is_req=0：该节点属于文档结构性章节、概述/背景/范围/引用文档/合格性规定/可追踪性/注释等，或仅作为分组容器、无实质可编码内容的父级标题。
3. 若节点同时包含概述与子需求，但自身正文仅为引导性描述（如「本章应分为如下小条规定…」），标为 0；具体可编码条目标为 1。
4. 表格、接口图、结构化字段中的具体功能/接口/数据要求，若需开发实现，标为 1。
5. 根节点始终为 0。
"""


def tree_needs_classification(tree: Dict[str, Any]) -> bool:
    """检查需求树是否尚未完成 is_req 标注。"""
    if not tree:
        return False

    def _walk(node: Dict[str, Any]) -> bool:
        if node.get('id') != 'root' and 'is_req' not in node:
            return True
        for child in node.get('children') or []:
            if _walk(child):
                return True
        return False

    return _walk(tree)


def _collect_classifiable_nodes(
    tree: Dict[str, Any],
    nodes: Optional[List[Dict[str, Any]]] = None,
    parent_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if nodes is None:
        nodes = []

    node_id = tree.get('id')
    if node_id != 'root':
        nodes.append({
            'id': node_id,
            'name': tree.get('display_title') or tree.get('label', ''),
            'number': tree.get('number'),
            'level': tree.get('level', 0),
            'original_text': format_node_validation_content(tree),
            'parent_id': parent_id,
        })

    for child in tree.get('children') or []:
        _collect_classifiable_nodes(child, nodes, node_id)

    return nodes


def _build_classification_prompt(nodes: List[Dict[str, Any]]) -> str:
    prompt = (
        '你是软件需求分析专家，熟悉 GJB 438C 软件需求规格说明（SRS）。\n'
        '请判断每个节点是否属于需要落实到代码/软件实现的需求。\n'
        + CLASSIFICATION_GUIDELINES
        + '\n返回 JSON 数组，每个元素包含：\n'
        '- id: 节点ID\n'
        '- is_req: 整数，1=需落实到代码，0=不需要\n'
        '- reason: 简要说明判断依据（一句话）\n'
    )

    for i, node in enumerate(nodes):
        content_text = node.get('original_text') or node.get('name') or ''
        prompt += f'\n## 节点 {i + 1}\n'
        prompt += f"ID: {node['id']}\n"
        prompt += f"名称: {node['name']}\n"
        prompt += f"层级: {node.get('level', '未知')}\n"
        prompt += f"# 节点内容\n{content_text}\n"

    prompt += (
        '\n请严格按照以下格式返回，不要包含其他无关内容：\n'
        '[\n'
        '  {"id": "节点ID", "is_req": 1, "reason": "判断依据"},\n'
        '  ...\n'
        ']\n'
    )
    return prompt


def _parse_classification_response(response: str, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned = (response or '').strip()
    if cleaned.startswith('[') and not cleaned.endswith(']'):
        last_brace = cleaned.rfind('}')
        if last_brace != -1:
            cleaned = cleaned[:last_brace + 1] + ']'

    try:
        results = json.loads(cleaned)
        if not isinstance(results, list):
            results = [results]
        return results
    except json.JSONDecodeError:
        match = re.search(r'\[\s*\{[\s\S]*?\}\s*\]', cleaned)
        if match:
            return json.loads(match.group(0))
    return _default_classification_results(nodes)


def _default_classification_results(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for node in nodes:
        has_content = bool((node.get('original_text') or '').strip())
        is_req = 1 if has_content else 0
        results.append({
            'id': node['id'],
            'is_req': is_req,
            'reason': '大模型暂不可用，按是否有实质内容默认判断。',
        })
    return results


def _normalize_is_req(value: Any) -> int:
    if value is True or value == 1 or str(value).strip() == '1':
        return 1
    return 0


def _apply_results_to_tree(tree: Dict[str, Any], result_map: Dict[str, Dict[str, Any]]) -> None:
    node_id = tree.get('id')
    if node_id == 'root':
        tree['is_req'] = 0
        tree['is_req_reason'] = '根节点，无编码需求。'
    elif node_id in result_map:
        item = result_map[node_id]
        tree['is_req'] = _normalize_is_req(item.get('is_req'))
        reason = (item.get('reason') or '').strip()
        if reason:
            tree['is_req_reason'] = reason
    else:
        tree.setdefault('is_req', 0)

    for child in tree.get('children') or []:
        _apply_results_to_tree(child, result_map)


def classify_requirement_tree(tree: Dict[str, Any]) -> Dict[str, Any]:
    """对需求树各节点调用大模型标注 is_req，原地更新并返回树。"""
    nodes = _collect_classifiable_nodes(tree)
    if not nodes:
        tree['is_req'] = 0
        return tree

    print(f'正在使用大模型判断 is_req，共 {len(nodes)} 个节点...')
    all_results: List[Dict[str, Any]] = []
    total_batches = (len(nodes) + BATCH_SIZE - 1) // BATCH_SIZE

    cfg = LLMConfig.query.first()
    model = cfg.model if cfg else app.config['API_MODEL_DEFAULT']
    api_key = cfg.api_key if cfg else app.config['API_KEY_DEFAULT']
    api_url = cfg.base_url if cfg else app.config['API_URL_DEFAULT']

    for batch_idx in range(total_batches):
        start = batch_idx * BATCH_SIZE
        end = min(start + BATCH_SIZE, len(nodes))
        batch_nodes = nodes[start:end]
        print(f'  is_req 分类第 {batch_idx + 1}/{total_batches} 批 ({start + 1}-{end})...')

        prompt = _build_classification_prompt(batch_nodes)
        response = call_deepseek_api(prompt, model, api_key, api_url)
        batch_results = _parse_classification_response(response, batch_nodes)
        all_results.extend(batch_results)

    result_map = {item['id']: item for item in all_results if item.get('id')}
    _apply_results_to_tree(tree, result_map)

    coded_count = sum(1 for item in all_results if _normalize_is_req(item.get('is_req')) == 1)
    print(f'is_req 分类完成：{coded_count}/{len(nodes)} 个节点需落实到代码')
    return tree


def ensure_tree_classified(tree: Dict[str, Any]) -> Dict[str, Any]:
    """若树尚未标注 is_req，则执行分类。"""
    if tree_needs_classification(tree):
        return classify_requirement_tree(tree)
    if tree.get('id') == 'root' and 'is_req' not in tree:
        tree['is_req'] = 0
    return tree
