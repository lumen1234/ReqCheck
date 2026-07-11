"""使用大模型判断需求节点 is_req 与需求类型 type（单轮合并分类）。"""
import json
import re
from typing import Any, Dict, List, Optional

from app import app
from app.models import LLMConfig
from app.routes.validate import call_deepseek_api, format_node_validation_content
from app.services.llm_config import format_llm_request_error

BATCH_SIZE = 10

REQUIREMENT_TYPES = [
    "功能需求",
    "接口需求",
    "强度需求",
    "数据处理需求",
    "安全性需求",
    "可靠性需求",
    "性能需求",
    "容量需求",
    "余量需求",
    "边界需求",
]

DEFAULT_REQUIREMENT_TYPE = "功能需求"

CLASSIFICATION_GUIDELINES = """
## is_req 判断原则（必须遵守）
1. is_req=1：该节点描述的是需要在软件/代码中实现、验证或配置的具体需求，例如功能行为、接口、算法、性能指标、数据结构、状态机、错误处理、约束条件等。
2. is_req=0：该节点属于文档结构性章节、概述/背景/范围/引用文档/合格性规定/可追踪性/注释等，或仅作为分组容器、无实质可编码内容的父级标题。
3. 若节点同时包含概述与子需求，但自身正文仅为引导性描述（如「本章应分为如下小条规定…」），标为 0；具体可编码条目标为 1。
4. 表格、接口图、结构化字段中的具体功能/接口/数据要求，若需开发实现，标为 1。
5. 根节点始终为 0。
"""

TYPE_CLASSIFICATION_GUIDELINES = """
## type 类型原则（is_req=1 时必须填写）
1. type 必须从下列 10 种中精确选取一种：
   - 功能需求：描述软件应做什么、业务流程、状态转换、控制逻辑、算法行为等。
   - 接口需求：描述与外部系统/硬件/软件/用户的接口、协议、报文、引脚、API 等。
   - 强度需求：描述结构强度、负载、压力、耐久等（嵌入式/硬件相关文档中常见）。
   - 数据处理需求：描述数据采集、存储、转换、计算、格式、精度、滤波等数据处理要求。
   - 安全性需求：描述认证、授权、加密、防篡改、故障安全、访问控制等。
   - 可靠性需求：描述容错、冗余、恢复、MTBF、故障检测与处理等。
   - 性能需求：描述响应时间、吞吐量、实时性、采样率、延迟、帧率等时间/速度指标。
   - 容量需求：描述存储容量、并发数、连接数、队列深度等资源上限。
   - 余量需求：描述设计余量、扩展预留、升级空间等。
   - 边界需求：描述输入输出范围、阈值、极限条件、适用范围、约束边界等。
2. 若节点内容跨类，选最核心、最主要的一类。
3. is_req=0 时不返回 type 字段。
4. 表格/接口描述优先判为「接口需求」；纯性能指标优先判为「性能需求」。
"""


def _node_needs_classification(node: Dict[str, Any]) -> bool:
    if node.get('id') == 'root':
        return False
    if 'is_req' not in node:
        return True
    if node.get('is_req') == 1 and 'type' not in node:
        return True
    return False


def tree_needs_classification(tree: Dict[str, Any]) -> bool:
    """检查需求树是否尚未完成 is_req / type 标注。"""
    if not tree:
        return False

    def _walk(node: Dict[str, Any]) -> bool:
        if _node_needs_classification(node):
            return True
        for child in node.get('children') or []:
            if _walk(child):
                return True
        return False

    return _walk(tree)


def tree_needs_type_classification(tree: Dict[str, Any]) -> bool:
    """兼容旧调用：等价于 tree_needs_classification。"""
    return tree_needs_classification(tree)


def _collect_classifiable_nodes(
    tree: Dict[str, Any],
    nodes: Optional[List[Dict[str, Any]]] = None,
    parent_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if nodes is None:
        nodes = []

    node_id = tree.get('id')
    if _node_needs_classification(tree):
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
    type_list = '、'.join(f'「{t}」' for t in REQUIREMENT_TYPES)
    prompt = (
        '你是软件需求分析专家，熟悉 GJB 438C 软件需求规格说明（SRS）。\n'
        '请对每个节点同时判断：① 是否需落实到代码（is_req）；② 若为需求则推断类型（type）。\n'
        + CLASSIFICATION_GUIDELINES
        + TYPE_CLASSIFICATION_GUIDELINES
        + f'\n允许的类型取值（必须完全一致）：{type_list}\n'
        + '\n返回 JSON 数组，每个元素包含：\n'
        '- id: 节点ID\n'
        '- is_req: 整数，1=需落实到代码，0=不需要\n'
        '- type: 仅 is_req=1 时填写，为上述 10 种类型之一；is_req=0 时不含此字段\n'
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
        '  {"id": "节点ID", "is_req": 1, "type": "功能需求"},\n'
        '  {"id": "节点ID", "is_req": 0},\n'
        '  ...\n'
        ']\n'
    )
    return prompt


def _parse_json_array_response(response: str) -> Optional[List[Dict[str, Any]]]:
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
    return None


def _parse_classification_response(response: str, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = _parse_json_array_response(response)
    if results is not None:
        return results
    return _default_classification_results(nodes)


def _default_classification_results(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for node in nodes:
        has_content = bool((node.get('original_text') or '').strip())
        is_req = 1 if has_content else 0
        item: Dict[str, Any] = {'id': node['id'], 'is_req': is_req}
        if is_req == 1:
            item['type'] = DEFAULT_REQUIREMENT_TYPE
        results.append(item)
    return results


def _normalize_is_req(value: Any) -> int:
    if value is True or value == 1 or str(value).strip() == '1':
        return 1
    return 0


def _normalize_requirement_type(value: Any) -> str:
    text = (str(value).strip() if value is not None else '')
    if text in REQUIREMENT_TYPES:
        return text
    for candidate in REQUIREMENT_TYPES:
        if candidate in text:
            return candidate
    return DEFAULT_REQUIREMENT_TYPE


def _apply_results_to_tree(tree: Dict[str, Any], result_map: Dict[str, Dict[str, Any]]) -> None:
    node_id = tree.get('id')
    if node_id == 'root':
        tree['is_req'] = 0
        tree.pop('is_req_reason', None)
        tree.pop('type', None)
        tree.pop('type_reason', None)
    elif node_id in result_map:
        item = result_map[node_id]
        tree['is_req'] = _normalize_is_req(item.get('is_req'))
        tree.pop('is_req_reason', None)
        if tree['is_req'] == 1:
            tree['type'] = _normalize_requirement_type(item.get('type'))
            tree.pop('type_reason', None)
        else:
            tree.pop('type', None)
            tree.pop('type_reason', None)
    else:
        tree.setdefault('is_req', 0)
        tree.pop('is_req_reason', None)

    for child in tree.get('children') or []:
        _apply_results_to_tree(child, result_map)


def _get_llm_credentials() -> tuple[str, str, str]:
    cfg = LLMConfig.query.first()
    model = cfg.model if cfg else app.config['API_MODEL_DEFAULT']
    api_key = cfg.api_key if cfg else app.config['API_KEY_DEFAULT']
    api_url = cfg.base_url if cfg else app.config['API_URL_DEFAULT']
    return model, api_key, api_url


def classify_requirement_tree(tree: Dict[str, Any]) -> Dict[str, Any]:
    """对需求树各节点单轮调用大模型，同时标注 is_req 与 type。"""
    nodes = _collect_classifiable_nodes(tree)
    if not nodes:
        if tree.get('id') == 'root' and 'is_req' not in tree:
            tree['is_req'] = 0
        return tree

    print(f'正在使用大模型分类 is_req + type，共 {len(nodes)} 个节点...')
    all_results: List[Dict[str, Any]] = []
    total_batches = (len(nodes) + BATCH_SIZE - 1) // BATCH_SIZE
    model, api_key, api_url = _get_llm_credentials()

    for batch_idx in range(total_batches):
        start = batch_idx * BATCH_SIZE
        end = min(start + BATCH_SIZE, len(nodes))
        batch_nodes = nodes[start:end]
        print(f'  分类第 {batch_idx + 1}/{total_batches} 批 ({start + 1}-{end})...')

        prompt = _build_classification_prompt(batch_nodes)
        try:
            response = call_deepseek_api(prompt, model, api_key, api_url)
        except Exception as e:
            hint = format_llm_request_error(e, api_url)
            raise RuntimeError(
                f'需求分类失败：{hint} 请在右上角「模型设置」中配置有效的 API Key 后重试。'
            ) from e
        batch_results = _parse_classification_response(response, batch_nodes)
        all_results.extend(batch_results)

    result_map = {item['id']: item for item in all_results if item.get('id')}
    _apply_results_to_tree(tree, result_map)

    coded_count = sum(1 for item in all_results if _normalize_is_req(item.get('is_req')) == 1)
    type_counts: Dict[str, int] = {}
    for item in all_results:
        if _normalize_is_req(item.get('is_req')) == 1:
            req_type = _normalize_requirement_type(item.get('type'))
            type_counts[req_type] = type_counts.get(req_type, 0) + 1
    summary = '，'.join(f'{k}:{v}' for k, v in sorted(type_counts.items()))
    print(f'分类完成：{coded_count}/{len(nodes)} 个节点为需求' + (f'；类型分布：{summary}' if summary else ''))
    return tree


def classify_requirement_types(tree: Dict[str, Any]) -> Dict[str, Any]:
    """兼容旧调用：合并分类后等价于 classify_requirement_tree。"""
    return classify_requirement_tree(tree)


def ensure_tree_classified(tree: Dict[str, Any]) -> Dict[str, Any]:
    """若树尚未标注 is_req 或 type，则执行分类。"""
    if tree_needs_classification(tree):
        return classify_requirement_tree(tree)
    if tree.get('id') == 'root' and 'is_req' not in tree:
        tree['is_req'] = 0
    return tree
