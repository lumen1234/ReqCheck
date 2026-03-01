import requests
import json
import os
import time

BASE_URL = "http://127.0.0.1:5000"
TEST_FILE = r"E:\req_com1\MEMS陀螺软件需求规格说明.docx"
OUTPUT_FOLDER = r"E:\req_com1\integration_test_results"

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

session = requests.Session()
session.trust_env = False


def count_nodes(node):
    """递归计算节点数量"""
    count = 1
    children = node.get('children') or []
    for child in children:
        count += count_nodes(child)
    return count


def test_workflow():
    print("=" * 70)
    print("集成测试: 完整工作流测试")
    print("=" * 70)

    print("\n" + "=" * 70)
    print("工作流1: 上传新文件 -> 大模型分析验证 -> 导出")
    print("=" * 70)

    print("\n[步骤1] 上传文件...")
    upload_start = time.time()
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
            upload_cached = data.get('cached', False)
            upload_duration = time.time() - upload_start

            print(f"   ✓ 上传成功, doc_id: {doc_id}")
            print(f"   ✓ 上传耗时: {upload_duration:.2f}秒")
            print(f"   ✓ 缓存命中: {upload_cached}")

            if upload_cached:
                print("   ⚠ 文件已存在，跳过工作流1，直接进入工作流2测试")
                test_workflow2_cached(doc_id)
                return
        else:
            print(f"   ✗ 上传失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return
    except Exception as e:
        print(f"   ✗ 错误: {e}")
        return

    print("\n[步骤2] 解析文档 (调用大模型)...")
    parse_start = time.time()
    try:
        response = session.get(f"{BASE_URL}/api/parse/{doc_id}", timeout=300)
        parse_duration = time.time() - parse_start

        if response.status_code == 200:
            data = response.json()
            cached = data.get('cached', False)

            print(f"   ✓ 解析成功, 耗时: {parse_duration:.2f}秒")
            print(f"   ✓ 缓存命中: {cached}")

            req_tree = data.get('requirement_tree', {})
            node_count = count_nodes(req_tree)
            print(f"   ✓ 节点总数: {node_count}")

            output_file = os.path.join(OUTPUT_FOLDER, f"parse_{doc_id}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(req_tree, f, ensure_ascii=False, indent=2)
            print(f"   ✓ 结果已保存: {output_file}")
        else:
            print(f"   ✗ 解析失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return
    except Exception as e:
        print(f"   ✗ 错误: {e}")
        return

    print("\n[步骤3] 验证需求 (调用大模型)...")
    validate_start = time.time()
    try:
        response = session.get(f"{BASE_URL}/api/validate/{doc_id}", timeout=600)
        validate_duration = time.time() - validate_start

        if response.status_code == 200:
            data = response.json()
            cached = data.get('cached', False)

            print(f"   ✓ 验证成功, 耗时: {validate_duration:.2f}秒")
            print(f"   ✓ 缓存命中: {cached}")

            validation_results = data.get('validation_results', [])
            pass_count = sum(1 for r in validation_results if r.get('result') == True)
            fail_count = sum(1 for r in validation_results if r.get('result') == False)
            print(f"   ✓ 合规: {pass_count}个, 不合规: {fail_count}个")

            output_file = os.path.join(OUTPUT_FOLDER, f"validation_{doc_id}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(validation_results, f, ensure_ascii=False, indent=2)
            print(f"   ✓ 结果已保存: {output_file}")
        else:
            print(f"   ✗ 验证失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return
    except Exception as e:
        print(f"   ✗ 错误: {e}")
        return

    print("\n[步骤4] 导出结果...")
    try:
        response = session.post(
            f"{BASE_URL}/api/export",
            json={'doc_id': doc_id},
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ 导出成功")
            print(f"   ✓ 总需求数: {data.get('total_requirements')}")

            requirements = data.get('requirements', [])
            output_file = os.path.join(OUTPUT_FOLDER, f"export_{doc_id}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(requirements, f, ensure_ascii=False, indent=2)
            print(f"   ✓ 结果已保存: {output_file}")
        else:
            print(f"   ✗ 导出失败: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    print("\n" + "=" * 70)
    print("工作流1 完成!")
    print(f"   上传耗时: {upload_duration:.2f}秒")
    print(f"   解析耗时: {parse_duration:.2f}秒")
    print(f"   验证耗时: {validate_duration:.2f}秒")
    print(f"   总耗时: {upload_duration + parse_duration + validate_duration:.2f}秒")
    print("=" * 70)

    test_workflow2_cached(doc_id, parse_duration, validate_duration)


def test_workflow2_cached(first_doc_id, first_parse_duration=0, first_validate_duration=0):
    print("\n" + "=" * 70)
    print("工作流2: 上传相同文件 -> 命中缓存 -> 直接返回 -> 导出")
    print("=" * 70)

    print("\n[步骤1] 再次上传相同文件...")
    upload_start = time.time()
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
            upload_cached = data.get('cached', False)
            upload_duration = time.time() - upload_start

            print(f"   ✓ 上传成功, doc_id: {doc_id}")
            print(f"   ✓ 上传耗时: {upload_duration:.2f}秒")
            print(f"   ✓ 缓存命中: {upload_cached}")

            if doc_id == first_doc_id:
                print("   ✓✓✓ 上传缓存命中! 返回相同doc_id")
            else:
                print(f"   ✗ doc_id不同! 期望: {first_doc_id}, 实际: {doc_id}")

            if upload_cached:
                print(f"   ✓ 消息: {data.get('message', '')}")
        else:
            print(f"   ✗ 上传失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return
    except Exception as e:
        print(f"   ✗ 错误: {e}")
        return

    print("\n[步骤2] 解析文档 (应命中缓存)...")
    parse_start = time.time()
    try:
        response = session.get(f"{BASE_URL}/api/parse/{doc_id}", timeout=300)
        parse_duration = time.time() - parse_start

        if response.status_code == 200:
            data = response.json()
            cached = data.get('cached', False)

            print(f"   ✓ 解析成功, 耗时: {parse_duration:.2f}秒")
            print(f"   ✓ 缓存命中: {cached}")

            if cached:
                print("   ✓✓✓ 解析缓存命中! 无需调用大模型")

            if first_parse_duration > 0 and parse_duration > 0:
                speedup = first_parse_duration / parse_duration
                print(f"   ✓ 加速比: {speedup:.2f}x")
        else:
            print(f"   ✗ 解析失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return
    except Exception as e:
        print(f"   ✗ 错误: {e}")
        return

    print("\n[步骤3] 验证需求 (应命中缓存)...")
    validate_start = time.time()
    try:
        response = session.get(f"{BASE_URL}/api/validate/{doc_id}", timeout=600)
        validate_duration = time.time() - validate_start

        if response.status_code == 200:
            data = response.json()
            cached = data.get('cached', False)

            print(f"   ✓ 验证成功, 耗时: {validate_duration:.2f}秒")
            print(f"   ✓ 缓存命中: {cached}")

            if cached:
                print("   ✓✓✓ 验证缓存命中! 无需调用大模型")

            if first_validate_duration > 0 and validate_duration > 0:
                speedup = first_validate_duration / validate_duration
                print(f"   ✓ 加速比: {speedup:.2f}x")
        else:
            print(f"   ✗ 验证失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return
    except Exception as e:
        print(f"   ✗ 错误: {e}")
        return

    print("\n[步骤4] 导出结果...")
    try:
        response = session.post(
            f"{BASE_URL}/api/export",
            json={'doc_id': doc_id},
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ 导出成功")
            print(f"   ✓ 总需求数: {data.get('total_requirements')}")
        else:
            print(f"   ✗ 导出失败: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    print("\n" + "=" * 70)
    print("工作流2 完成!")
    print(f"   上传耗时: {upload_duration:.2f}秒")
    print(f"   解析耗时: {parse_duration:.2f}秒")
    print(f"   验证耗时: {validate_duration:.2f}秒")
    print(f"   总耗时: {upload_duration + parse_duration + validate_duration:.2f}秒")
    print("=" * 70)

    print("\n" + "=" * 70)
    print("测试汇总")
    print("=" * 70)
    print(f"\n   工作流1 (新文件):")
    print(f"     doc_id: {first_doc_id}")
    if first_parse_duration > 0:
        print(f"     解析耗时: {first_parse_duration:.2f}秒")
        print(f"     验证耗时: {first_validate_duration:.2f}秒")

    print(f"\n   工作流2 (缓存命中):")
    print(f"     doc_id: {doc_id}")
    print(f"     解析耗时: {parse_duration:.2f}秒")
    print(f"     验证耗时: {validate_duration:.2f}秒")

    if first_parse_duration > 0 and parse_duration > 0:
        print(f"\n   性能对比:")
        print(f"     解析加速: {first_parse_duration / parse_duration:.2f}x")
        print(f"     验证加速: {first_validate_duration / validate_duration:.2f}x")

    print(f"\n   结果文件目录: {OUTPUT_FOLDER}")

    print("\n" + "=" * 70)
    print("集成测试完成!")
    print("=" * 70)


if __name__ == '__main__':
    try:
        test_workflow()
    except KeyboardInterrupt:
        print("\n测试已取消")
