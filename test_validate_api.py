import requests
import json
import os

BASE_URL = "http://127.0.0.1:5000"
TEST_DOC_ID = "bcab12d8-8874-4f8a-aaff-d3ba8e6d214d"

VALIDATE_OUTPUT_FOLDER = r"E:\req_com1\validate_results"

if not os.path.exists(VALIDATE_OUTPUT_FOLDER):
    os.makedirs(VALIDATE_OUTPUT_FOLDER)

session = requests.Session()
session.trust_env = False

def test_validate_api():
    print("=" * 60)
    print("测试 /api/validate 接口 - 全文验证")
    print("=" * 60)

    print(f"\n1. 验证JSON文件是否存在...")
    json_file = rf"E:\req_com1\app\parse_results\{TEST_DOC_ID}.json"
    if os.path.exists(json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        def count_nodes(node):
            count = 1
            children = node.get('children') or []
            for child in children:
                count += count_nodes(child)
            return count
        
        total = count_nodes(data)
        print(f"   ✓ JSON文件存在，共 {total} 个节点")
    else:
        print(f"   ✗ JSON文件不存在: {json_file}")
        return

    print(f"\n2. 调用验证接口，doc_id: {TEST_DOC_ID}...")
    print("   正在调用大模型API进行验证，请稍候...")
    try:
        response = session.post(
            f"{BASE_URL}/api/validate",
            json={'doc_id': TEST_DOC_ID},
            timeout=600
        )

        print(f"   状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            results = data.get('validation_results', [])

            print(f"\n✓ 验证成功!")
            print(f"共验证 {len(results)} 个节点")

            output_file = os.path.join(VALIDATE_OUTPUT_FOLDER, f"validation_{TEST_DOC_ID}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"✓ 完整验证结果已保存到: {output_file}")

            print(f"\n" + "=" * 60)
            print("验证结果详情 (所有节点):")
            print("=" * 60)

            for i, result in enumerate(results):
                status = "✓ 合规" if result.get('result') else "✗ 不合规"
                print(f"\n[{i+1}] {result.get('name')}")
                print(f"    ID: {result.get('id')}")
                print(f"    状态: {status}")
                reason = result.get('reason', '无')
                if reason and len(reason) > 150:
                    reason = reason[:150] + "..."
                print(f"    原因: {reason}")

            pass_count = sum(1 for r in results if r.get('result') == True)
            fail_count = sum(1 for r in results if r.get('result') == False)

            print(f"\n" + "=" * 60)
            print("统计汇总:")
            print("=" * 60)
            print(f"  ✓ 合规: {pass_count} 个")
            print(f"  ✗ 不合规: {fail_count} 个")
            print(f"  总计: {len(results)} 个")

        else:
            print(f"✗ 验证失败: {response.status_code}")
            print(f"响应: {response.text}")

    except Exception as e:
        print(f"✗ 错误: {e}")
        print(f"请确保Flask应用正在运行 (python run.py)")

    print("\n" + "=" * 60)

if __name__ == '__main__':
    test_validate_api()
