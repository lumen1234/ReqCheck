import os
import sys
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath('.'))

from app.routes.parse import construct_requirement_tree
from docx import Document

# 测试docx文件解析
def test_docx_parse():
    print("测试docx文件解析...")
    filepath = "MEMS陀螺软件需求规格说明.docx"
    
    if not os.path.exists(filepath):
        print(f"文件不存在: {filepath}")
        return
    
    # 模拟parse_document函数中的docx解析逻辑
    document = Document(filepath)
    content = []
    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        
        # 尝试通过内容格式识别标题
        heading_level = None
        
        # 方法1：通过样式名称识别标题
        if para.style.name.startswith('Heading'):
            try:
                heading_level = int(para.style.name.split(' ')[1])
            except:
                heading_level = 1
        
        # 方法2：通过编号格式识别标题（如 "1. 范围"、"2.1 引用文档"、"1.\t范围"）
        if not heading_level:
            import re
            # 支持空格或制表符分隔的编号格式，确保只有真正的标题编号被识别
            # 匹配完整的标题编号格式，如 "1. "、"2.1 "、"3.1.1\t"
            match = re.match(r'^\d+(\.\d+)*[\s\t]+[\u4e00-\u9fa5]', text)
            if match:
                # 根据编号的层级确定标题级别
                level = len(match.group(0).split(' ')[0].split('.'))
                heading_level = level
        
        # 方法3：通过缩进和字体大小识别标题
        if not heading_level:
            # 检查是否有缩进或特殊格式
            if para.paragraph_format.left_indent is not None:
                # 可以根据缩进量判断级别
                pass
            # 检查字体大小
            for run in para.runs:
                if run.font.size:
                    # 标题通常字体较大
                    if run.font.size.pt >= 12:
                        heading_level = 1
                        break
        
        if heading_level:
            content.append({
                'type': 'heading',
                'level': heading_level,
                'text': text
            })
        else:
            if content and content[-1]['type'] == 'content':
                content[-1]['text'] += ' ' + text
            else:
                content.append({
                    'type': 'content',
                    'text': text
                })
    
    print("解析结果 (前20个条目):")
    for i, item in enumerate(content[:20]):
        print(f"[{i+1}] 类型: {item['type']}, 级别: {item.get('level', 'N/A')}, 内容: {item['text'][:100]}..." if len(item['text']) > 100 else f"[{i+1}] 类型: {item['type']}, 级别: {item.get('level', 'N/A')}, 内容: {item['text']}")
    
    # 测试需求树构造
    print("\n测试需求树构造...")
    req_tree = construct_requirement_tree(content, os.path.basename(filepath))
    
    print("需求树结构:")
    print(json.dumps(req_tree, ensure_ascii=False, indent=2))
    
    # 检查是否有子节点
    if len(req_tree['children']) > 0:
        print(f"\n成功生成需求树，包含 {len(req_tree['children'])} 个一级节点")
        # 打印一级节点名称
        print("一级节点:")
        for i, node in enumerate(req_tree['children']):
            print(f"[{i+1}] {node['name']}")
    else:
        print("\n警告：需求树没有子节点")

if __name__ == "__main__":
    test_docx_parse()
