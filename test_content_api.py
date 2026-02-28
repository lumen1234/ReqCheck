import requests
import json
import os

BASE_URL = "http://127.0.0.1:5000"
TEST_FILE = r"E:\req_com1\MEMS陀螺软件需求规格说明.docx"

def test_content_field():
    print("=" * 60)
    print("测试 content 字段是否正确填充")
    print("=" * 60)

    # 测试1: 检查应用是否运行
    print("\n[测试1] 检查Flask应用是否运行...")
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"  状态码: {response.status_code}")
        print("  ✓ Flask应用正常运行")
    except requests.exceptions.ConnectionError:
        print("  ✗ 无法连接到Flask应用")
        print("  请先启动Flask应用: python run.py")
        return False
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return False

    # 测试2: 检查待测试文件是否存在
    print(f"\n[测试2] 检查测试文件...")
    if not os.path.exists(TEST_FILE):
        print(f"  ✗ 文件不存在: {TEST_FILE}")
        return False
    print(f"  ✓ 文件存在: {TEST_FILE}")

    # 测试3: 上传文档
    print(f"\n[测试3] 上传文档...")
    try:
        with open(TEST_FILE, 'rb') as f:
            files = {'file': (os.path.basename(TEST_FILE), f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            response = requests.post(f"{BASE_URL}/upload", files=files, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            doc_id = data.get('doc_id')
            print(f"  ✓ 文档上传成功")
            print(f"    doc_id: {doc_id}")
        else:
            print(f"  ✗ 上传失败: {response.status_code}")
            print(f"  响应: {response.text}")
            return False
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return False

    # 测试4: 解析文档
    print(f"\n[测试4] 解析文档...")
    try:
        response = requests.post(f"{BASE_URL}/parse", json={'doc_id': doc_id}, timeout=60)
        if response.status_code == 200:
            print(f"  ✓ 文档解析成功")
        else:
            print(f"  ✗ 解析失败: {response.status_code}")
            print(f"  响应: {response.json()}")
            return False
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return False

    # 测试5: 导出JSON并检查content字段
    print(f"\n[测试5] 导出并检查content字段...")
    try:
        response = requests.post(f"{BASE_URL}/export", json={'doc_id': doc_id}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            requirements = data.get('requirements', [])
            print(f"  导出需求数量: {len(requirements)}")
            
            # 检查content字段
            print("\n  检查content字段:")
            has_content = False
            content_count = 0
            empty_count = 0
            
            for req in requirements:
                req_id = req.get('id')
                title = req.get('title')
                content = req.get('content', '')
                parent_id = req.get('parent_id')
                
                if content and len(content) > 0:
                    content_count += 1
                else:
                    empty_count += 1
            
            print(f"  有content的节点: {content_count}")
            print(f"  空content的节点: {empty_count}")
            
            # 显示几个有内容的例子
            print("\n  示例（有内容的节点）:")
            count = 0
            for req in requirements:
                content = req.get('content', '')
                if content and len(content) > 0:
                    print(f"    {req.get('id')} - {req.get('title')}")
                    print(f"      content: {content[:100]}...")
                    count += 1
                    if count >= 3:
                        break
            
            if content_count > 0:
                print("\n  ✓ content字段已正确填充，问题已解决!")
            else:
                print("\n  ✗ content字段仍然为空，问题未解决")
            
            return content_count > 0
            
        else:
            print(f"  ✗ 导出失败: {response.status_code}")
            print(f"  响应: {response.json()}")
            return False
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return False

    print("\n" + "=" * 60)
    return True

if __name__ == '__main__':
    try:
        test_content_field()
    except KeyboardInterrupt:
        print("\n测试已取消")
