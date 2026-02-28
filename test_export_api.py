import requests
import json
import os

BASE_URL = "http://127.0.0.1:5000"
TEST_DOC_ID = "bcab12d8-8874-4f8a-aaff-d3ba8e6d214d"

session = requests.Session()
session.trust_env = False

def test_export_api():
    print("=" * 60)
    print("测试 /api/export 接口")
    print("=" * 60)

    print(f"\n1. 检查必需文件是否存在...")

    # 检查parse结果
    parse_file = rf"E:\req_com1\app\parse_results\{TEST_DOC_ID}.json"
    if os.path.exists(parse_file):
        print(f"   ✓ parse结果存在: {parse_file}")
    else:
        print(f"   ✗ parse结果不存在: {parse_file}")
        return

    # 检查validation结果
    validation_file = rf"E:\req_com1\validate_results\validation_{TEST_DOC_ID}.json"
    if os.path.exists(validation_file):
        print(f"   ✓ validation结果存在: {validation_file}")
    else:
        print(f"   ⚠ validation结果不存在，将跳过验证结果合并")

    print(f"\n2. 调用导出接口，doc_id: {TEST_DOC_ID}...")
    try:
        response = session.post(
            f"{BASE_URL}/api/export",
            json={'doc_id': TEST_DOC_ID},
            timeout=60
        )

        print(f"   状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            print(f"\n✓ 导出成功!")
            print(f"   导出文件: {data.get('export_file')}")
            print(f"   总需求数: {data.get('total_requirements')}")

            # 显示导出结果示例
            requirements = data.get('requirements', [])
            print(f"\n3. 导出结果示例 (前5条):")
            print("=" * 60)
            for i, req in enumerate(requirements[:5]):
                validation = "✓ 合规" if req.get('validation_result') == True else "✗ 不合规" if req.get('validation_result') == False else "未验证"
                print(f"\n  [{i+1}] {req.get('title')}")
                print(f"      ID: {req.get('id')}")
                print(f"      Node ID: {req.get('node_id')}")
                print(f"      Level: {req.get('level')}")
                print(f"      验证结果: {validation}")

            pass_count = sum(1 for r in requirements if r.get('validation_result') == True)
            fail_count = sum(1 for r in requirements if r.get('validation_result') == False)
            none_count = sum(1 for r in requirements if r.get('validation_result') is None)

            print(f"\n" + "=" * 60)
            print("统计汇总:")
            print("=" * 60)
            print(f"  ✓ 已验证-合规: {pass_count} 个")
            print(f"  ✗ 已验证-不合规: {fail_count} 个")
            print(f"  - 未验证: {none_count} 个")
            print(f"  总计: {len(requirements)} 个")

            print(f"\n4. 导出文件位置:")
            print(f"   {data.get('export_path')}")

        else:
            print(f"✗ 导出失败: {response.status_code}")
            print(f"响应: {response.text}")

    except Exception as e:
        print(f"✗ 错误: {e}")
        print(f"请确保Flask应用正在运行 (python run.py)")

    print("\n" + "=" * 60)

def test_export_list():
    print("\n测试 /api/export/list 接口...")
    try:
        response = session.get(f"{BASE_URL}/api/export/list", timeout=30)

        if response.status_code == 200:
            data = response.json()
            exports = data.get('exports', [])

            print(f"✓ 共有 {len(exports)} 个导出文件:")
            for exp in exports:
                print(f"   - {exp.get('filename')}")
        else:
            print(f"✗ 获取列表失败: {response.status_code}")

    except Exception as e:
        print(f"✗ 错误: {e}")

def test_export_download():
    print("\n测试 /api/export/<doc_id> 下载接口...")
    try:
        response = session.get(
            f"{BASE_URL}/api/export/{TEST_DOC_ID}",
            timeout=30
        )

        if response.status_code == 200:
            print(f"✓ 下载成功，文件大小: {len(response.content)} bytes")
        else:
            print(f"✗ 下载失败: {response.status_code}")

    except Exception as e:
        print(f"✗ 错误: {e}")

if __name__ == '__main__':
    test_export_api()
    test_export_list()
    test_export_download()
