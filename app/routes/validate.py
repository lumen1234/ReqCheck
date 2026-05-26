from typing import List

from flask import Blueprint, request, jsonify
from app import app
from app.models import db, ValidationResult, LLMConfig
from app.services.workspace import parse_results_folder, validate_results_folder
import os
import requests
import json
import hashlib

validate_bp = Blueprint('validate', __name__)


def _validate_output_folder():
    return validate_results_folder(app)


def _cache_index_file():
    return os.path.join(_validate_output_folder(), 'cache_index.json')

def load_cache_index():
    """加载验证缓存索引"""
    cache_path = _cache_index_file()
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_cache_index(cache_index):
    """保存验证缓存索引"""
    with open(_cache_index_file(), 'w', encoding='utf-8') as f:
        json.dump(cache_index, f, ensure_ascii=False, indent=2)

def compute_content_hash(req_tree):
    """计算需求树内容的哈希值"""
    content_str = json.dumps(req_tree, sort_keys=True, ensure_ascii=False)
    hash_md5 = hashlib.md5()
    hash_md5.update(content_str.encode('utf-8'))
    return hash_md5.hexdigest()

@validate_bp.route('/api/validate/<doc_id>', methods=['GET'])
def validate_requirements(doc_id):
    if not doc_id:
        return jsonify({'error': 'doc_id is required'}), 400

    force = request.args.get('force', '').lower() in ('1', 'true', 'yes')

    # 1. 检查是否已有验证结果文件
    validation_file = os.path.join(_validate_output_folder(), f"validation_{doc_id}.json")
    if not force and os.path.exists(validation_file):
        with open(validation_file, 'r', encoding='utf-8') as f:
            validation_results = json.load(f)
        return jsonify({
            'validation_results': validation_results,
            'cached': True
        })
    
    # 2. 从parse结果读取需求树
    json_file = os.path.join(parse_results_folder(app), f"{doc_id}.json")
    
    if os.path.exists(json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            req_tree = json.load(f)
    else:
        # 从数据库读取
        from app.models import RequirementTree
        requirement_tree = RequirementTree.query.filter_by(doc_id=doc_id).first()
        if not requirement_tree:
            return jsonify({'error': 'Requirement tree not found'}), 404
        req_tree = requirement_tree.tree_json
    
    # 3. 检查验证缓存
    content_hash = compute_content_hash(req_tree)
    cache_index = load_cache_index()

    if not force and content_hash in cache_index:
        cached_doc_id = cache_index[content_hash]
        cached_validation_file = os.path.join(_validate_output_folder(), f"validation_{cached_doc_id}.json")
        if os.path.exists(cached_validation_file):
            print(f"发现相同需求树，已缓存验证结果 doc_id: {cached_doc_id}")
            
            with open(cached_validation_file, 'r', encoding='utf-8') as f:
                validation_results = json.load(f)
            
            # 保存当前doc_id的验证结果
            with open(validation_file, 'w', encoding='utf-8') as f:
                json.dump(validation_results, f, ensure_ascii=False, indent=2)
            
            # 保存到数据库
            _cfg = LLMConfig.query.first()
            _model_name = _cfg.model if _cfg else app.config['API_MODEL_DEFAULT']
            existing_result = ValidationResult.query.filter_by(doc_id=doc_id).first()
            if existing_result:
                # 更新现有记录
                existing_result.result_json = validation_results
                existing_result.model_used = _model_name
            else:
                # 创建新记录
                result = ValidationResult(
                    doc_id=doc_id,
                    result_json=validation_results,
                    model_used=_model_name
                )
                db.session.add(result)
            db.session.commit()
            
            return jsonify({
                'validation_results': validation_results,
                'cached': True,
                'cached_from': cached_doc_id
            })
    
    # 4. 执行验证
    rules = load_rules('appendix_j')
    validation_results = validate_batch(req_tree, rules)
    
    # 5. 保存验证结果
    with open(validation_file, 'w', encoding='utf-8') as f:
        json.dump(validation_results, f, ensure_ascii=False, indent=2)
    
    # 更新缓存索引
    cache_index[content_hash] = doc_id
    save_cache_index(cache_index)
    
    # 保存到数据库
    _cfg = LLMConfig.query.first()
    result = ValidationResult(
        doc_id=doc_id,
        result_json=validation_results,
        model_used=_cfg.model if _cfg else app.config['API_MODEL_DEFAULT']
    )
    db.session.add(result)
    db.session.commit()
    
    return jsonify({
        'validation_results': validation_results,
        'cached': False
    })

def load_rules(appendix):
    """加载附录规则，构建规则树"""
    if appendix == 'appendix_j':
        appendix_file = os.path.join(app.config['APPENDICES_FOLDER'], '438C-2021附录J.txt')
        if os.path.exists(appendix_file):
            return build_rule_tree_from_file(appendix_file)
        else:
            return get_default_appendix_j_rules()
    return {}

def build_rule_tree_from_file(file_path):
    """从附录 J 文本构建规则树，模板行（3.2.X）不覆盖父章节。"""
    import re

    rules = dict(get_default_appendix_j_rules())

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.read().strip().split('\n')
    except Exception as e:
        print(f"加载附录文件失败: {str(e)}")
        return rules

    current_section = ''
    current_content: list[str] = []

    def flush():
        nonlocal current_section, current_content
        if not current_section:
            return
        text = ' '.join(current_content).strip()
        if text and (current_section not in rules or len(text) > len(rules.get(current_section, ''))):
            rules[current_section] = text
        current_section = ''
        current_content = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith('附录') or line.startswith('（规范性附录') or line.startswith('《'):
            continue

        m = re.match(r'^(\d+(?:\.\d+)*)(.*)$', line)
        if m:
            num = m.group(1)
            rest = m.group(2).strip()

            # 模板占位：3.2.X / 3.3.X — 作为独立规则键，不覆盖 3.2 / 3.3
            if re.match(r'^\.X', rest):
                flush()
                template_key = f'{num}.X'
                current_section = template_key
                title = rest[2:].strip('（） ') if rest.startswith('.X') else rest
                current_content = [title] if title else []
                continue

            flush()
            current_section = num
            current_content = [rest] if rest else []
        elif current_section:
            current_content.append(line)

    flush()
    return rules


def extract_section_number(node: dict):
    """从节点的 number / 标题 提取章节号，不从正文 content 提取。"""
    import re

    if node.get('number'):
        return str(node['number']).strip()

    for field in ('display_title', 'label', 'name'):
        text = (node.get(field) or '').strip()
        if not text:
            continue
        m = re.match(r'^(\d+(?:\.\d+)*)', text)
        if m:
            return m.group(1)
    return None


def resolve_rule_for_node(node: dict, rules: dict) -> str:
    """按章节号匹配附录规则，支持父章节与 3.x.X 模板回退。"""
    title_number = extract_section_number(node)

    if title_number:
        if title_number in rules:
            return rules[title_number]

        parts = title_number.split('.')
        for j in range(len(parts) - 1, 0, -1):
            parent = '.'.join(parts[:j])
            if parent in rules:
                return rules[parent]

        if len(parts) >= 2:
            template_key = f'{parts[0]}.{parts[1]}.X'
            if template_key in rules:
                return rules[template_key]

        if parts[0] in rules:
            return rules[parts[0]]

    return '无对应规则'

def get_default_appendix_j_rules():
    """获取默认的附录J规则"""
    return {
        '1': '范围：本章应描述本文档所适用系统和软件的完整标识，适用时，包括其标识号、名称、缩略名、版本号和发布号；概述本文档适用的系统和软件的用途；描述系统和软件的一般特性；概述系统开发、运行和维护的历史；标识项目的需方、用户、开发方和保障机构等；标识当前和计划的运行现场；列出其他有关文档；概述本文档的用途和内容，并描述与它的使用有关的安全保密方面的要求。',
        '1.1': '标识：本条应描述本文档所适用系统和软件的完整标识，适用时，包括其标识号、名称、缩略名、版本号和发布号。',
        '1.2': '系统概述：本条应概述本文档适用的系统和软件的用途；描述系统和软件的一般特性（如规模、安全性、可靠性、实时性、技术风险等特性）；概述系统开发、运行和维护的历史；标识项目的需方、用户、开发方和保障机构等；标识当前和计划的运行现场；列出其他有关文档。',
        '1.3': '文档概述：本条应概述本文档的用途和内容，并描述与它的使用有关的安全保密方面的要求。',
        '2': '引用文档：本章应列出引用文档的编号、标题、编写单位、修订版及日期，还应给出不能通过正常渠道得到的文档的来源。',
        '3': '需求：本章应分为如下小条规定CSCI需求，即作为CSCI验收条件的CSCI特征。CSCI需求是为满足分配给该CSCI的系统需求而形成的软件需求。每条需求应指定项目唯一的标识符以便测试和追踪，而且应以一种能为其定义具体测试对象的方式来描述。每条需求应注明所采用的合格性方法（见第4章），还应注明与系统或子系统需求的可追踪性（或在第5章给出）。',
        '3.1': '要求的状态和方式：如果要求CSCI在多种状态或方式下运行，并且不同的状态或方式具有不同的需求，则应标识和定义每一状态和方式。状态和方式的例子包括：空闲、就绪、活动、事后分析、训练、降级、紧急情况、后备、战时和平时等。可以仅用状态描述CSCI，也可以仅用方式、用方式中的状态、状态中的方式、或其他有效的方案描述CSCI。如果不需要多种状态和方式，应如实陈述，而不需要进行人为的区分；如果需要多种状态和/或方式，应使本规格说明中的每个需求或每组需求与这些状态和方式相对应，对应关系可以在本条或本条所引用的附录中，通过表格或其他方式加以指明，也可以在该需求出现的章条中加以说明。',
        '3.2': 'CSCI能力需求：本条应逐一列出与CSCI各个能力相关的需求，可分为若干子条。"CSCI能力需求"中的"能力"为一组相关需求，可用"功能"、"主题"、"目标"、或其他适合表示需求的词替代。',
        '3.3': 'CSCI外部接口需求：本条可分为若干个小条来规定关于CSCI的外部接口的需求（若有）。本条可引用一个或多个接口需求规格说明（IRS）或包含这些需求的其他文档。',
        '3.4': 'CSCI内部接口需求：本条应指明施加于CSCI内部接口的需求（若有）。如果所有内部接口都留待设计时再明确，那么应在此如实陈述。如果施加了这样的需求，应按3.3要求描述。',
        '3.5': 'CSCI内部数据需求：本条应指明施加于CSCI内部数据的需求（若有），包括对CSCI中数据库和数据文件的需求（若有）。如果关于内部数据的所有决策都留待设计时再考虑，那么应在此如实陈述。如果施加了这样的需求，应按3.3.Xc）和3.3.Xd）要求描述。',
        '3.6': '适应性需求：（若有）本条应指明与CSCI安装相关的数据需求（如场地的经纬度或位置编码），应描述CSCI使用要求的运行参数（如与使用相关的目标设置或数据记录等方面参数），这些运行参数可能会根据运行需要而改变。',
        '3.7': '保密性（Security）需求：（若有）本条应指明与维护保密性有关的CSCI需求。（若适用）这些需求应包括：CSCI必须在其中运行的保密性环境、所提供的保密性的类型和级别、CSCI必须经受的保密性风险、减少此类风险所需的安全措施、必须遵循的保密性政策、CSCI必须具备的保密性责任、保密性认证认可必须满足的准则等。',
        '3.8': '安全性（Safety）需求：（若有）本条应指明关于防止或尽可能降低对人员、财产和物理环境产生意外危险的CSCI安全性需求。例子包括：CSCI必须提供的安全措施，以便防止意外动作（例如意外地发出一个"自动导航关闭"命令）和无动作（例如发出"自动导航关闭"命令失败）。本条还应包括关于系统核部件的CSCI需求（若有），若适用应包括预防意外爆炸以及与核安全规则保持一致等方面的需求。',
        '3.9': 'CSCI环境适应性需求：（若有）本条应指明CSCI的运行环境需求，例如运行CSCI的计算机硬件和操作系统（对计算机资源的其他需求见3.11）。',
        '3.10': '其他质量特性：本条应指明合同规定的或由更高一层规格说明派生出的CSCI其他质量特性方面的需求，其中包括：可靠性、测试性，维护性等。',
        '3.11': '计算机资源需求：本条应指明CSCI必须使用的计算机硬件的需求、计算机硬件资源使用需求、计算机软件需求和计算机通信需求。',
        '3.12': '设计和实现约束：本条应指明约束CSCI的设计和实现的需求（若有）。这些需求可引用相应的商用或军用标准和规范来指定。',
        '3.13': '人员相关需求：（若有）本条应描述CSCI需求，包括与CSCI使用或保障人员有关的容纳人员的数量、技能等级、工作周期、必需的训练以及其他的信息，例如要求允许多少用户同时工作，以及内置的帮助和培训短片等方面的需求：也包括施加于CSCI的人机工程需求（若有）。',
        '3.14': '训练相关需求：（若有）本条应指明与训练相关的CSCI需求，如包括在CSCI中的训练软件。',
        '3.15': '软件保障需求：本条应指明与软件保障考虑有关的CSCI需求（若有）。这些考虑可以包括：对系统维护、软件保障、系统运输方式、补给系统的要求、对现有设施的影响和对现有设备的影响。',
        '3.16': '包装需求：本条应指明为了交付而对CSCI进行包装、标记和处理（例如用光盘提交，并按规定要求对光盘标记和包装）的需求（若有），可引用适用的标准。',
        '3.17': '其他需求：本条应指明上述各条未能覆盖的其他CSCI需求（若有）。',
        '3.18': '需求的优先顺序和关键性：（若适用）本条应指明本规格说明中各需求的优先次序、关键性或表示其相对重要性的权重。例如标识出对安全性和保密性关键的需求，以便进行特殊处理。如果所有需求具有相等的权重，本条应如实说明。',
        '4': '合格性规定：本条应定义一组合格性检验方法，针对第3章中的每个需求指定确定需求得到满足所使用的方法。可用表格形式表述，或为第3章中的每个需求注明所使用的方法。',
        '5': '需求可追踪性：本章应描述从本规格说明中的每一个CSCI需求，到所涉及的系统/子系统需求的可追踪性；从已分配给本CSCI的每一个系统/子系统需求，到所涉及的CSCI需求的可追踪性。',
        '6': '注释：本章应包括有助于了解文档的所有信息（例如：背景、术语、缩略语或公式）。'
    }

BATCH_SIZE = 10

VALIDATION_GUIDELINES = """
## 审查原则（必须遵守）
1. 附录 J 中「可引用」「若有」「适用时」表示该要求为可选，不得将可选项当作强制项。
2. 表格、图注、接口图及其结构化字段（标识、类型、输入、输出等）均视为有效需求内容，与叙述性正文同等对待。
3. 不得仅因缺少独立叙述段落、未出现「IRS」「接口需求规格说明」等字样而判定不合规；若表格/图已完整描述接口或需求，应视为符合规范。
4. 仅当节点既无实质正文、也无表格/图片等结构化内容时，才可因「内容缺失」判定不合规。
5. 对 3.3 外部接口、3.4 内部接口等章节：规范允许通过接口图+表格描述接口，引用 IRS 为可选方式之一，非唯一合规路径。
"""


def format_table_for_validation(table: dict, index: int) -> str:
    headers = table.get('headers') or []
    rows = table.get('rows') or []
    if not headers and not rows:
        return ''
    lines = [f'【表格{index}】']
    if headers:
        lines.append('表头: ' + ' | '.join(str(h) for h in headers))
    for row in rows:
        lines.append('行: ' + ' | '.join(str(c) for c in row))
    return '\n'.join(lines)


def format_node_validation_content(node: dict) -> str:
    """合并正文、表格、图片说明，供大模型审查。"""
    parts: List[str] = []
    text = (node.get('content') or '').strip()
    if text:
        parts.append('【正文】\n' + text)

    tables = node.get('tables') or []
    if tables:
        tbl_parts = []
        for i, tbl in enumerate(tables, 1):
            block = format_table_for_validation(tbl, i)
            if block:
                tbl_parts.append(block)
        if tbl_parts:
            parts.append('【表格内容】\n' + '\n\n'.join(tbl_parts))

    images = node.get('images') or []
    if images:
        img_lines = []
        for i, img in enumerate(images, 1):
            cap = img.get('caption') or img.get('alt') or f'图片{i}'
            img_lines.append(f'- {cap}')
        parts.append('【图片/接口图】\n' + '\n'.join(img_lines))

    if not parts:
        label = node.get('display_title') or node.get('label') or ''
        return label or '（无正文、表格或图片）'
    return '\n\n'.join(parts)

def validate_batch(req_tree, rules):
    """批处理验证需求树"""
    nodes = []
    collect_nodes(req_tree, nodes)
    
    print(f"收集到 {len(nodes)} 个节点进行验证")
    
    if not nodes:
        return []
    
    if nodes and nodes[0].get('id') == 'root':
        nodes = nodes[1:]
    
    all_results = []
    total_batches = (len(nodes) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, len(nodes))
        batch_nodes = nodes[start_idx:end_idx]
        
        print(f"验证第 {batch_idx + 1}/{total_batches} 批 ({start_idx + 1}-{end_idx} 个节点)...")
        
        prompt = construct_validation_prompt(batch_nodes, rules)
        
        _cfg = LLMConfig.query.first()
        _model = _cfg.model if _cfg else app.config['API_MODEL_DEFAULT']
        _api_key = _cfg.api_key if _cfg else app.config['API_KEY_DEFAULT']
        _api_url = _cfg.base_url if _cfg else app.config['API_URL_DEFAULT']
        model_response = call_deepseek_api(
            prompt,
            _model,
            _api_key,
            _api_url
        )
        
        try:
            print(f"API响应: {model_response[:200]}...")
            
            cleaned_response = model_response.strip()
            
            if cleaned_response.startswith('[') and not cleaned_response.endswith(']'):
                import re
                last_brace = cleaned_response.rfind('}')
                if last_brace != -1:
                    cleaned_response = cleaned_response[:last_brace+1] + ']'
            
            try:
                batch_results = json.loads(cleaned_response)
                if not isinstance(batch_results, list):
                    batch_results = [batch_results]
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\[\s*\{[\s\S]*?\}\s*\]', cleaned_response)
                if json_match:
                    batch_results = json.loads(json_match.group(0))
                else:
                    batch_results = generate_default_results(batch_nodes)
            
            all_results.extend(batch_results)
            print(f"  本批验证完成，获得 {len(batch_results)} 个结果")
            
        except Exception as e:
            print(f"解析响应失败: {str(e)}")
            all_results.extend(generate_default_results(batch_nodes))
    
    root_result = {
        'id': 'root',
        'name': req_tree.get('label', 'root'),
        'result': True,
        'reason': '根节点，无对应规范要求。',
        'parent_id': None
    }
    
    return [root_result] + all_results

def collect_nodes(node, nodes, parent_id=None):
    """收集需求树中的所有节点（含表格、图片等结构化内容）。"""
    nodes.append({
        'id': node['id'],
        'name': node.get('display_title') or node.get('label', node.get('name', '')),
        'number': node.get('number'),
        'label': node.get('label'),
        'display_title': node.get('display_title'),
        'original_text': format_node_validation_content(node),
        'parent_id': parent_id,
    })

    children = node.get('children')
    if children is None:
        children = []

    for child in children:
        collect_nodes(child, nodes, node['id'])

def construct_validation_prompt(nodes, rules):
    """构造验证提示词，按照标题号逐条验证"""
    prompt = """你是一个文档审查专家，熟悉 GJB 438C 附录 J（软件需求规格说明）编写要求。
请根据规范判断文档内容是否合规。注意：规范中的「可引用」「若有」为可选要求，表格与接口图属于有效内容。

""" + VALIDATION_GUIDELINES + """

返回 JSON 数组，每个元素包含：
- id: 节点ID
- name: 节点名称
- result: bool，true=合规，false=不合规
- reason: 简要说明判断依据
- parent_id: 父节点ID

"""
    
    for i, node in enumerate(nodes):
        title_number = extract_section_number(node)
        rule = resolve_rule_for_node(node, rules)

        prompt += f"\n## 节点 {i+1}\n"
        prompt += f"ID: {node['id']}\n"
        prompt += f"名称: {node['name']}\n"
        prompt += f"标题号: {title_number or '无'}\n"
        prompt += f"# 文档规范\n{rule}\n"
        content_text = node.get('original_text') or node.get('name') or ''
        prompt += f"# 文档内容（含正文、表格、图片说明）\n{content_text}\n"
    
    prompt += "\n请严格按照以下格式返回验证结果，不要包含其他无关内容：\n"
    prompt += "[\n"
    prompt += "  {\"id\": \"节点ID\", \"name\": \"节点名称\", \"result\": true/false, \"reason\": \"判断依据\", \"parent_id\": \"父节点ID\"},\n"
    prompt += "  ...\n"
    prompt += "]"
    
    return prompt

def call_deepseek_api(prompt, model, api_key, api_url):
    """调用DeepSeek大模型API"""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    data = {
        'model': model,
        'messages': [
            {
                'role': 'system',
                'content': (
                    '你是专业的软件需求规格说明（SRS）审查专家，精通 GJB 438C 附录 J。'
                    '审查时：表格、接口图、结构化字段与叙述正文同等有效；'
                    '「可引用 IRS」等为可选表述，不得仅因未写 IRS 或缺少叙述段而判不合规；'
                    '仅当既无正文也无表格/图等实质内容时才可判缺失。'
                )
            },
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'temperature': 0.3,
        'max_tokens': 1000
    }
    
    try:
        session = requests.Session()
        session.trust_env = False
        
        response = session.post(
            api_url + '/chat/completions',
            headers=headers,
            json=data,
            timeout=app.config.get('API_TIMEOUT', 270)
        )
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"API调用失败: {str(e)}")
        return '{"result": true, "reason": "由于网络原因，大模型验证暂时不可用，默认标记为合规。"}'

def generate_default_results(nodes):
    """生成默认验证结果"""
    results = []
    for node in nodes:
        results.append({
            'id': node['id'],
            'name': node['name'],
            'result': True,
            'reason': '由于大模型验证暂时不可用，默认标记为合规。',
            'parent_id': node.get('parent_id')
        })
    return results
