import requests
import json
import os

BASE_URL = "http://127.0.0.1:5000"
TEST_FILE = r"E:\req_com1\MEMS陀螺软件需求规格说明.docx"
OUTPUT_FILE = r"E:\req_com1\test_output.json"

session = requests.Session()
session.trust_env = False

def test_parse_api_with_llm():
    print("=" * 60)
    print("测试 /api/parse 接口 (使用大模型)")
    print("=" * 60)

    print("\n1. 上传测试文件...")
    try:
        with open(TEST_FILE, 'rb') as f:
            files = {
                'file': (
                    os.path.basename(TEST_FILE),
                    f,
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
            }
            response = session.post(f"{BASE_URL}/api/upload", files=files, timeout=60)

        if response.status_code == 200:
            data = response.json()
            doc_id = data.get('doc_id')
            print(f"   ✓ 文件上传成功, doc_id: {doc_id}")
        else:
            print(f"   ✗ 上传失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return
    except Exception as e:
        print(f"   ✗ 错误: {e}")
        return

    print("\n2. 调用 /api/parse 接口 (use_llm=true)...")
    try:
        response = session.post(
            f"{BASE_URL}/api/parse",
            json={'doc_id': doc_id, 'use_llm': True},
            timeout=300
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ 解析成功, 状态码: {response.status_code}")

            tree = data.get('requirement_tree', {})

            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(tree, f, ensure_ascii=False, indent=2)
            print(f"   ✓ JSON已保存到: {OUTPUT_FILE}")

            print(f"\n3. 验证JSON结构...")
            validate_json_structure(tree)

        else:
            print(f"   ✗ 解析失败: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    print("\n" + "=" * 60)

def validate_json_structure(tree):
    required_fields = ['id', 'label', 'content', 'level', 'v_status', 'e_status', 'children']

    def check_node(node, path="root"):
        for field in required_fields:
            if field not in node:
                print(f"   ✗ 节点 {path} 缺少字段: {field}")
                return False

        if not isinstance(node['children'], list) and node['children'] is not None:
            print(f"   ✗ 节点 {path} 的 children 不是数组或null")
            return False

        if node['children']:
            for i, child in enumerate(node['children']):
                child_path = f"{path}/children[{i}]"
                if not check_node(child, child_path):
                    return False

        return True

    if check_node(tree):
        print(f"   ✓ JSON结构验证通过")

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
    print(f"   ✓ 节点总数: {total}")
    print(f"   ✓ 包含内容的节点数: {with_content}")

def test_parse_api_without_llm():
    print("\n")
    print("=" * 60)
    print("测试 /api/parse 接口 (不使用大模型)")
    print("=" * 60)

    print("\n1. 上传测试文件...")
    try:
        with open(TEST_FILE, 'rb') as f:
            files = {
                'file': (
                    os.path.basename(TEST_FILE),
                    f,
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
            }
            response = session.post(f"{BASE_URL}/api/upload", files=files, timeout=60)

        if response.status_code == 200:
            data = response.json()
            doc_id = data.get('doc_id')
            print(f"   ✓ 文件上传成功, doc_id: {doc_id}")
        else:
            print(f"   ✗ 上传失败: {response.status_code}")
            return
    except Exception as e:
        print(f"   ✗ 错误: {e}")
        return

    print("\n2. 调用 /api/parse 接口 (use_llm=false)...")
    try:
        response = session.post(
            f"{BASE_URL}/api/parse",
            json={'doc_id': doc_id, 'use_llm': False},
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ 解析成功, 状态码: {response.status_code}")

            tree = data.get('requirement_tree', {})

            output_file_no_llm = r"E:\req_com1\test_output_no_llm.json"
            with open(output_file_no_llm, 'w', encoding='utf-8') as f:
                json.dump(tree, f, ensure_ascii=False, indent=2)
            print(f"   ✓ JSON已保存到: {output_file_no_llm}")

        else:
            print(f"   ✗ 解析失败: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    print("\n" + "=" * 60)

if __name__ == '__main__':
    try:
        test_parse_api_with_llm()
        test_parse_api_without_llm()
    except KeyboardInterrupt:
        print("\n测试已取消")
