import os
import sys
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath('.'))

from docx import Document

# 简单测试docx文件解析
def test_simple_docx_parse():
    print("简单测试docx文件解析...")
    filepath = "MEMS陀螺软件需求规格说明.docx"
    
    if not os.path.exists(filepath):
        print(f"文件不存在: {filepath}")
        return
    
    # 直接解析docx文件
    document = Document(filepath)
    content = []
    
    import re
    
    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        
        # 尝试通过编号格式识别标题
        heading_level = None
        title_number = None
        
        # 支持各种空白字符分隔的编号格式
        # 使用更灵活的正则表达式，匹配各种类型的空白字符
        import re
        match = re.match(r'^(\d+(\.\d+)*)\s+(.+)$', text)
        if match:
            title_number = match.group(1)
            level = len(title_number.split('.'))
            heading_level = level
        
        if heading_level:
            content.append({
                'type': 'heading',
                'level': heading_level,
                'text': text,
                'title_number': title_number
            })
        else:
            content.append({
                'type': 'content',
                'text': text
            })
    
    # 打印解析结果
    print(f"解析结果共 {len(content)} 条记录")
    print("\n前30条解析结果:")
    for i, item in enumerate(content[:30]):
        if item['type'] == 'heading':
            print(f"[{i+1}] 标题 (级别: {item['level']}, 编号: {item['title_number']}): {item['text']}")
        else:
            print(f"[{i+1}] 内容: {item['text'][:100]}..." if len(item['text']) > 100 else f"[{i+1}] 内容: {item['text']}")
    
    # 过滤出标题
    headings = [item for item in content if item['type'] == 'heading']
    print(f"\n共识别出 {len(headings)} 个标题")
    
    # 打印所有标题
    print("\n识别出的标题:")
    for i, heading in enumerate(headings):
        print(f"[{i+1}] 级别: {heading['level']}, 编号: {heading['title_number']}, 文本: {heading['text']}")

if __name__ == "__main__":
    test_simple_docx_parse()
