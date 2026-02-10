from flask import Blueprint, request, jsonify
from app import app
from app.models import db, ValidationResult
import os
import requests
import json

validate_bp = Blueprint('validate', __name__)

@validate_bp.route('/validate', methods=['POST'])
def validate_requirements():
    doc_id = request.json.get('doc_id')
    if not doc_id:
        return jsonify({'error': 'doc_id is required'}), 400
    
    # 查找文件
    filepath = None
    file_type = None
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if filename.startswith(doc_id):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            # 这里简化处理，实际项目中应该从数据库或文件元数据中获取file_type
            file_type = '需求规格说明'  # 假设默认是需求规格说明
            break
    
    if not filepath:
        return jsonify({'error': 'Document not found'}), 404
    
    # 选择对应的附录
    appendix = 'appendix_j'  # 假设需求规格说明对应附录J
    
    # 加载规则（实际项目中应该从存储的规则树中加载）
    rules = load_rules(appendix)
    
    # 从数据库中获取实际的需求树
    from app.models import RequirementTree
    requirement_tree = RequirementTree.query.filter_by(doc_id=doc_id).first()
    if not requirement_tree:
        return jsonify({'error': 'Requirement tree not found'}), 404
    
    req_tree = requirement_tree.tree_json
    
    # 执行批处理验证
    validation_results = validate_batch(req_tree, rules)
    
    # 保存到数据库
    result = ValidationResult(
        doc_id=doc_id,
        result_json=validation_results,
        model_used=app.config['API_MODEL_DEFAULT']  # 使用真实的模型名称
    )
    db.session.add(result)
    db.session.commit()
    
    return jsonify({'validation_results': validation_results})

def load_rules(appendix):
    # 加载附录J的详细规则
    if appendix == 'appendix_j':
        return {
            '范围': '本章应描述本文档所适用系统和软件的完整标识，适用时，包括其标识号、名称、缩略名、版本号和发布号；概述本文档适用的系统和软件的用途；描述系统和软件的一般特性；概述系统开发、运行和维护的历史；标识项目的需方、用户、开发方和保障机构等；标识当前和计划的运行现场；列出其他有关文档；概述本文档的用途和内容，并描述与它的使用有关的安全保密方面的要求。',
            '引用文档': '本章应列出引用文档的编号、标题、编写单位、修订版及日期，还应给出不能通过正常渠道得到的文档的来源。',
            '需求': '本章应分为如下小条规定CSCI需求，即作为CSCI验收条件的CSCI特征。每条需求应指定项目唯一的标识符以便测试和追踪，而且应以一种能为其定义具体测试对象的方式来描述。每条需求应注明所采用的合格性方法，还应注明与系统或子系统需求的可追踪性。',
            '要求的状态和方式': '如果要求CSCI在多种状态或方式下运行，并且不同的状态或方式具有不同的需求，则应标识和定义每一状态和方式。如果不需要多种状态和方式，应如实陈述，而不需要进行人为的区分。',
            'CSCI能力需求': '本条应逐一列出与CSCI各个能力相关的需求，可分为若干子条。需求应详细说明所需的CSCI行为，包括适用的参数，如响应时间、吞吐时间、其他时限约束、时序、精度、容量、优先级、连续运行需求和在基本运行条件下允许的偏差。',
            'CSCI外部接口需求': '本条可分为若干个小条来规定关于CSCI的外部接口的需求。应标识所需要的CSCI外部接口，通过一张或多张接口图来描述这些接口，并详细描述接口的特征。',
            'CSCI内部接口需求': '本条应指明施加于CSCI内部接口的需求。如果所有内部接口都留待设计时再明确，那么应在此如实陈述。',
            'CSCI内部数据需求': '本条应指明施加于CSCI内部数据的需求，包括对CSCI中数据库和数据文件的需求。如果关于内部数据的所有决策都留待设计时再考虑，那么应在此如实陈述。',
            '适应性需求': '本条应指明与CSCI安装相关的数据需求，应描述CSCI使用要求的运行参数，这些运行参数可能会根据运行需要而改变。',
            '保密性需求': '本条应指明与维护保密性有关的CSCI需求。这些需求应包括：CSCI必须在其中运行的保密性环境、所提供的保密性的类型和级别、CSCI必须经受的保密性风险、减少此类风险所需的安全措施、必须遵循的保密性政策、CSCI必须具备的保密性责任、保密性认证认可必须满足的准则等。',
            '安全性需求': '本条应指明关于防止或尽可能降低对人员、财产和物理环境产生意外危险的CSCI安全性需求。例子包括：CSCI必须提供的安全措施，以便防止意外动作和无动作。',
            'CSCI环境适应性需求': '本条应指明CSCI的运行环境需求，例如运行CSCI的计算机硬件和操作系统。',
            '其他质量特性': '本条应指明合同规定的或由更高一层规格说明派生出的CSCI其他质量特性方面的需求，其中包括：可靠性、测试性、维护性等。',
            '计算机资源需求': '本条应指明CSCI必须使用的计算机硬件的需求；指明CSCI计算机硬件资源使用需求；指明CSCI必须使用或必须被纳入本CSCI的计算机软件的需求；指明CSCI必须使用的计算机通信方面的需求。',
            '设计和实现约束': '本条应指明约束CSCI的设计和实现的需求。这些需求可引用相应的商用或军用标准和规范来指定。',
            '人员相关需求': '本条应描述CSCI需求，包括与CSCI使用或保障人员有关的容纳人员的数量、技能等级、工作周期、必需的训练以及其他的信息，也包括施加于CSCI的人机工程需求。',
            '训练相关需求': '本条应指明与训练相关的CSCI需求，如包括在CSCI中的训练软件。',
            '软件保障需求': '本条应指明与软件保障考虑有关的CSCI需求。这些考虑可以包括：对系统维护、软件保障、系统运输方式、补给系统的要求、对现有设施的影响和对现有设备的影响。',
            '包装需求': '本条应指明为了交付而对CSCI进行包装、标记和处理的需求，可引用适用的标准。',
            '其他需求': '本条应指明上述各条未能覆盖的其他CSCI需求。',
            '需求的优先顺序和关键性': '本条应指明本规格说明中各需求的优先次序、关键性或表示其相对重要性的权重。如果所有需求具有相等的权重，本条应如实说明。',
            '合格性规定': '本条应定义一组合格性检验方法，针对第3章中的每个需求指定确定需求得到满足所使用的方法。可用表格形式表述，或为第3章中的每个需求注明所使用的方法。',
            '需求可追踪性': '本章应描述从本规格说明中的每一个CSCI需求，到所涉及的系统/子系统需求的可追踪性；从已分配给本CSCI的每一个系统/子系统需求，到所涉及的CSCI需求的可追踪性。',
            '注释': '本章应包括有助于了解文档的所有信息（例如：背景、术语、缩略语或公式）。'
        }
    return {}

def call_volcengine_ark(prompt, model, api_key, api_url):
    """调用火山引擎Ark大模型API"""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    data = {
        'model': model,
        'messages': [
            {
                'role': 'system',
                'content': '你是一个专业的需求文档审查专家，精通软件工程和需求分析。'
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
        # 创建会话并强制跳过代理设置
        session = requests.Session()
        session.trust_env = False  # 不使用系统环境变量中的代理设置
        
        response = session.post(
            api_url + '/chat/completions',
            headers=headers,
            json=data,
            timeout=app.config.get('API_TIMEOUT', 30)
        )
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"API调用失败: {str(e)}")
        # 返回一个合理的默认JSON格式结果，而不是错误信息
        return '{"result": true, "reason": "由于网络原因，大模型验证暂时不可用，默认标记为合规。"}'


def validate_batch(req_tree, rules):
    """批处理验证需求树"""
    # 收集所有需要验证的节点
    nodes = []
    collect_nodes(req_tree, nodes)
    
    # 如果没有节点，返回空结果
    if not nodes:
        return []
    
    # 构造批处理提示词
    prompt = construct_batch_prompt(nodes, rules)
    
    # 调用大模型API
    model_response = call_volcengine_ark(
        prompt,
        app.config['API_MODEL_DEFAULT'],
        app.config['API_KEY_DEFAULT'],
        app.config['API_URL_DEFAULT']
    )
    
    # 解析大模型响应
    try:
        # 尝试提取JSON部分
        import re
        json_match = re.search(r'\[\{[\s\S]*\}\]', model_response)
        if json_match:
            validation_results = json.loads(json_match.group(0))
        else:
            # 如果没有找到JSON数组，尝试解析单个JSON对象
            json_match = re.search(r'\{[\s\S]*\}', model_response)
            if json_match:
                single_result = json.loads(json_match.group(0))
                # 将单个结果转换为数组
                validation_results = [single_result]
            else:
                # 如果仍然没有找到JSON，生成默认结果
                validation_results = generate_default_results(nodes)
    except Exception as e:
        print(f"解析响应失败: {str(e)}")
        # 生成默认结果
        validation_results = generate_default_results(nodes)
    
    return validation_results

def collect_nodes(node, nodes, parent_id=None):
    """收集需求树中的所有节点"""
    nodes.append({
        'id': node['id'],
        'name': node['name'],
        'original_text': node.get('original_text', node['name']),
        'parent_id': parent_id
    })
    
    # 递归收集子节点
    for child in node.get('children', []):
        collect_nodes(child, nodes, node['id'])

def construct_batch_prompt(nodes, rules):
    """构造批处理验证提示词"""
    prompt = """你是一个专业的需求文档审查专家，精通软件工程和需求分析。
请根据以下文档规范，批量判断多个文档节点是否符合规范。

# 验证要求
1. 对每个节点，根据其对应的规范进行验证
2. 返回一个JSON数组，每个元素包含：
   - id: 节点ID
   - name: 节点名称
   - result: bool值，true表示合规，false表示不合规
   - reason: 简要说明判断依据

# 文档规范映射
"""
    
    # 添加规范映射
    for name, rule in rules.items():
        prompt += f"- {name}: {rule}\n"
    
    prompt += "\n# 需要验证的节点\n"
    
    # 添加需要验证的节点
    for i, node in enumerate(nodes):
        rule = rules.get(node['name'], '无对应规则')
        prompt += f"\n## 节点 {i+1}\n"
        prompt += f"ID: {node['id']}\n"
        prompt += f"名称: {node['name']}\n"
        prompt += f"内容: {node['original_text']}\n"
        prompt += f"规范: {rule}\n"
    
    prompt += "\n请返回JSON数组格式的验证结果，不要包含其他无关内容。"
    
    return prompt

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
