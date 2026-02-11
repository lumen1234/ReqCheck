from flask import Blueprint, request, jsonify
from app import app
from app.models import db, Document as DocModel, RequirementTree
import os
import re
from docx import Document

parse_bp = Blueprint('parse', __name__)

@parse_bp.route('/parse', methods=['POST'])
def parse_document():
    doc_id = request.json.get('doc_id')
    if not doc_id:
        return jsonify({'error': 'doc_id is required'}), 400
    
    # 从数据库中获取文件路径
    document = DocModel.query.filter_by(id=doc_id).first()
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    filepath = document.file_path
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found on disk'}), 404
    
    # 解析文档
    if filepath.endswith('.docx'):
        document = Document(filepath)
        content = []
        
        # 定义文档结构中的关键标题术语
        key_headings = {
            '软件需求规格说明': 1,
            '范围': 1,
            '标识': 2,
            '系统概述': 2,
            '文档概述': 2,
            '引用文档': 1,
            '需求': 1,
            '要求的状态和方式': 2,
            '能力需求': 2,
            '外部接口需求': 2,
            '内部接口需求': 2,
            '系统的内部数据需求': 2,
            '适应性需求': 2,
            '保密性需求': 2,
            '安全性需求': 2,
            '环境适应性需求': 2,
            '其他质量特性': 2,
            '计算机资源需求': 2,
            '设计和实现约束': 2,
            '人员相关需求': 2,
            '训练相关需求': 2,
            '软件保障需求': 2,
            '包装需求': 2,
            '需求的优先顺序和关键程度': 2,
            '其他需求': 2,
            '合格性规定': 1,
            '合格性方法': 2,
            '合格性级别': 2,
            '需求可追踪性': 1,
            '注释': 1
        }
        
        for para in document.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            
            # 尝试通过内容格式识别标题
            heading_level = None
            title_number = None
            
            # 方法1：通过关键术语识别标题
            if text in key_headings:
                heading_level = key_headings[text]
            
            # 方法2：通过编号格式识别标题（如 "1. 范围"、"2.1 引用文档"、"1.\t范围"、"1.    范围    1"）
            if not heading_level:
                import re
                # 支持各种空白字符分隔的编号格式，确保只有真正的标题编号被识别
                # 匹配更宽松的标题格式，允许标题文本包含各种字符，包括标点符号和页码
                # 使用更灵活的正则表达式，匹配各种类型的空白字符
                match = re.match(r'^(\d+(\.\d+)*)\s+(.+)$', text)
                if match:
                    title_number = match.group(1)
                    # 根据编号的层级确定标题级别
                    level = len(title_number.split('.'))
                    heading_level = level
            
            # 方法3：通过样式名称识别标题
            if not heading_level and para.style.name.startswith('Heading'):
                try:
                    heading_level = int(para.style.name.split(' ')[1])
                except:
                    heading_level = 1
            
            # 方法4：通过样式名称识别目录项
            if not heading_level and para.style.name.startswith('toc '):
                # 从样式名称中提取级别（如 "toc 1" -> 1）
                try:
                    heading_level = int(para.style.name.split(' ')[1])
                except:
                    heading_level = 1
            
            if heading_level:
                content.append({
                    'type': 'heading',
                    'level': heading_level,
                    'text': text,
                    'title_number': title_number
                })
            else:
                # 普通内容
                if content and content[-1]['type'] == 'content':
                    content[-1]['text'] += ' ' + text
                else:
                    content.append({
                        'type': 'content',
                        'text': text
                    })
    elif filepath.endswith('.txt'):
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        content = []
        # 简单的txt文件解析，根据缩进或编号识别标题
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 尝试识别标题（根据编号格式）
            match = re.match(r'^(\d+(\.\d+)*)[\s\t]+(.+)$', line)
            if match:
                title_number = match.group(1)
                # 根据标题编号确定级别
                level = len(title_number.split('.'))
                content.append({
                    'type': 'heading',
                    'level': level,
                    'text': line,
                    'title_number': title_number
                })
            else:
                # 普通内容
                if content and content[-1]['type'] == 'content':
                    content[-1]['text'] += ' ' + line
                else:
                    content.append({
                        'type': 'content',
                        'text': line
                    })
    
    # 构造需求树
    req_tree = construct_requirement_tree(content, os.path.basename(filepath))
    
    # 保存到数据库
    tree = RequirementTree(
        doc_id=doc_id,
        tree_json=req_tree
    )
    db.session.add(tree)
    
    # 更新文档状态
    document = DocModel.query.filter_by(id=doc_id).first()
    if document:
        document.status = '已解析'
    
    db.session.commit()
    
    return jsonify({'requirement_tree': req_tree})

def construct_requirement_tree(content, doc_name):
    # 根据附录J的结构构造需求树
    tree = {
        'id': 'root',
        'label': doc_name,
        'name': doc_name,
        'original_text': doc_name,
        'content': None,
        'level': 0,
        'v_status': True,
        'e_status': 'pending',
        'children': []
    }
    
    # 附录J的标准结构映射
    appendix_j_structure = {
        '1': '范围',
        '2': '引用文档',
        '3': '需求',
        '3.1': '要求的状态和方式',
        '3.2': 'CSCI能力需求',
        '3.3': 'CSCI外部接口需求',
        '3.4': 'CSCI内部接口需求',
        '3.5': 'CSCI内部数据需求',
        '3.6': '适应性需求',
        '3.7': '保密性需求',
        '3.8': '安全性需求',
        '3.9': 'CSCI环境适应性需求',
        '3.10': '其他质量特性',
        '3.11': '计算机资源需求',
        '3.12': '设计和实现约束',
        '3.13': '人员相关需求',
        '3.14': '训练相关需求',
        '3.15': '软件保障需求',
        '3.16': '包装需求',
        '3.17': '其他需求',
        '3.18': '需求的优先顺序和关键性',
        '4': '合格性规定',
        '5': '需求可追踪性',
        '6': '注释'
    }
    
    # 构建一个简单的树状结构，只包含真正的标题
    # 首先，过滤出真正的标题
    headings = []
    for item in content:
        if item['type'] == 'heading':
            title_number = item.get('title_number')
            if title_number:
                # 提取标题文本
                import re
                match = re.match(r'^\d+(\.\d+)*[\s\t]+', item['text'])
                if match:
                    title_text = item['text'][len(match.group(0)):].strip()
                    level = len(title_number.split('.'))
                    headings.append({
                        'level': level,
                        'number': title_number,
                        'text': title_text
                    })
            else:
                # 处理没有编号的标题（通过关键术语识别的）
                title_text = item['text']
                level = item['level']
                headings.append({
                    'level': level,
                    'number': None,
                    'text': title_text
                })
    
    # 如果没有找到标题，使用默认结构
    if not headings:
        # 添加默认的需求节点
        default_node = {
            'id': 'default_0',
            'label': '需求',
            'name': '需求',
            'original_text': '需求',
            'content': None,
            'level': 1,
            'v_status': True,
            'e_status': 'pending',
            'children': []
        }
        tree['children'].append(default_node)
        return tree
    
    # 构建树状结构
    current_levels = {}
    for i, heading in enumerate(headings):
        level = heading['level']
        title_number = heading['number']
        title_text = heading['text']
        
        # 使用附录J的标准名称或原始文本
        if title_number:
            node_name = appendix_j_structure.get(title_number, title_text)
            original_text = f"{title_number} {title_text}"
        else:
            node_name = title_text
            original_text = title_text
        
        node = {
            'id': f'node_{i}',
            'label': node_name,
            'name': node_name,
            'original_text': original_text,
            'content': None,
            'level': level,
            'v_status': True,
            'e_status': 'pending',
            'children': []
        }
        
        # 构建树状结构
        if level == 1:
            # 一级标题直接添加到根节点
            tree['children'].append(node)
            current_levels[level] = tree['children']
        else:
            # 查找合适的父节点
            parent_level = level - 1
            if parent_level in current_levels:
                parent_children = current_levels[parent_level]
                if parent_children:
                    # 添加到最近的父级节点
                    parent_children[-1]['children'].append(node)
                    current_levels[level] = parent_children[-1]['children']
            else:
                # 如果没有找到父级节点，添加到根节点
                tree['children'].append(node)
                current_levels[level] = tree['children']
    

    
    return tree
