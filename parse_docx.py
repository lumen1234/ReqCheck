import os
import re
import json
import sys
from docx import Document
import requests

API_KEY = "sk-ba7862f60e3e460e88e17dad82e34982"
API_URL = "https://api.deepseek.com"
API_MODEL = "deepseek-chat"

def extract_text_from_docx(filepath):
    doc = Document(filepath)
    text_lines = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            text_lines.append(text)
    return '\n'.join(text_lines)

def call_llm_api(prompt, retries=3):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    }
    
    data = {
        'model': API_MODEL,
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
                API_URL + '/chat/completions',
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

    response = call_llm_api(prompt)
    
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
            
            import re
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

def main():
    if len(sys.argv) < 2:
        input_file = r"e:\req_com1\MEMS陀螺软件需求规格说明.docx"
    else:
        input_file = sys.argv[1]

    output_file = input_file.replace('.docx', '.json')

    print(f"正在解析文档: {input_file}")
    print("正在使用大模型API智能解析...")

    text = extract_text_from_docx(input_file)
    result = parse_document_with_llm(text)
    
    if result and 'tree' in result:
        tree = result['tree']
        print("大模型解析成功!")
    else:
        print("大模型解析失败，请检查API配置或网络连接")
        return

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    print(f"解析完成，已保存到: {output_file}")

    def count_nodes(node):
        count = 1
        if node.get('children'):
            for child in node['children']:
                count += count_nodes(child)
        return count

    def count_with_content(node):
        count = 1 if node.get('content') else 0
        if node.get('children'):
            for child in node['children']:
                count += count_with_content(child)
        return count

    total = count_nodes(tree)
    with_content = count_with_content(tree)
    print(f"共解析出 {total} 个节点，其中 {with_content} 个节点包含内容")

if __name__ == '__main__':
    main()
