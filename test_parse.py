import os
import sys
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath('.'))

from app.routes.parse import construct_requirement_tree

# 测试txt文件解析
def test_txt_parse():
    print("测试txt文件解析...")
    filepath = "test_requirments.txt"
    
    if not os.path.exists(filepath):
        print(f"文件不存在: {filepath}")
        return
    
    # 模拟parse_document函数中的txt解析逻辑
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    import re
    content = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 尝试识别标题（根据编号格式）
        if re.match(r'^\d+(\.\d+)*\s', line):
            # 提取标题编号和内容
            parts = line.split(' ', 1)
            if len(parts) > 1:
                title_number = parts[0]
                title_text = parts[1]
                # 根据标题编号确定级别
                level = len(title_number.split('.'))
                content.append({
                    'type': 'heading',
                    'level': level,
                    'text': line
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
    
    print("解析结果:")
    for item in content:
        print(f"类型: {item['type']}, 级别: {item.get('level', 'N/A')}, 内容: {item['text']}")
    
    # 测试需求树构造
    print("\n测试需求树构造...")
    req_tree = construct_requirement_tree(content, os.path.basename(filepath))
    
    print("需求树结构:")
    print(json.dumps(req_tree, ensure_ascii=False, indent=2))
    
    # 检查是否有子节点
    if len(req_tree['children']) > 0:
        print(f"\n成功生成需求树，包含 {len(req_tree['children'])} 个一级节点")
    else:
        print("\n警告：需求树没有子节点")

if __name__ == "__main__":
    test_txt_parse()
