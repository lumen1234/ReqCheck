import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_connectivity():
    print("=" * 50)
    print("Flask 接口连通性测试")
    print("=" * 50)

    # 测试1: 检查应用是否运行
    print("\n[测试1] 检查根路由...")
    try:
        response = requests.get(BASE_URL + "/", timeout=5)
        print(f"  状态码: {response.status_code}")
        print("  ✓ 应用正常运行")
    except requests.exceptions.ConnectionError:
        print("  ✗ 无法连接到应用，请确保Flask应用已启动")
        print("  提示: 运行 'python run.py' 启动应用")
        return False
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return False

    # 测试2: 检查上传接口
    print("\n[测试2] /upload 接口...")
    try:
        response = requests.post(f"{BASE_URL}/api/pload", json={}, timeout=5)
        print(f"  状态码: {response.status_code}")
        if response.status_code in [200, 400]:
            data = response.json()
            print(f"  响应: {data}")
            print("  ✓ /upload 接口正常")
    except Exception as e:
        print(f"  ✗ 错误: {e}")

    # 测试3: 检查文档列表接口
    print("\n[测试3] /documents 接口...")
    try:
        response = requests.get(f"{BASE_URL}/api/documents", timeout=5)
        print(f"  状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  文档数量: {len(data)}")
            print("  ✓ /documents 接口正常")
    except Exception as e:
        print(f"  ✗ 错误: {e}")

    # 测试4: 检查解析接口（缺少参数）
    print("\n[测试4] /parse 接口...")
    try:
        response = requests.post(f"{BASE_URL}/api/parse", json={}, timeout=5)
        print(f"  状态码: {response.status_code}")
        if response.status_code in [200, 400, 404]:
            data = response.json()
            print(f"  响应: {data}")
            print("  ✓ /parse 接口正常")
    except Exception as e:
        print(f"  ✗ 错误: {e}")

    # 测试5: 检查导出接口（缺少参数）
    print("\n[测试5] /export 接口...")
    try:
        response = requests.post(f"{BASE_URL}/api/export", json={}, timeout=5)
        print(f"  状态码: {response.status_code}")
        if response.status_code in [200, 400, 404]:
            data = response.json()
            print(f"  响应: {data}")
            print("  ✓ /export 接口正常")
    except Exception as e:
        print(f"  ✗ 错误: {e}")

    # 测试6: 检查验证接口（缺少参数）
    print("\n[测试6] /validate 接口...")
    try:
        response = requests.post(f"{BASE_URL}/api/validate", json={}, timeout=5)
        print(f"  状态码: {response.status_code}")
        if response.status_code in [200, 400, 404]:
            data = response.json()
            print(f"  响应: {data}")
            print("  ✓ /validate 接口正常")
    except Exception as e:
        print(f"  ✗ 错误: {e}")

    print("\n" + "=" * 50)
    print("接口连通性测试完成!")
    print("=" * 50)
    return True

if __name__ == '__main__':
    try:
        test_connectivity()
    except KeyboardInterrupt:
        print("\n测试已取消")
