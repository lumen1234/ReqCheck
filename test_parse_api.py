import requests
import json
import os

BASE_URL = "http://127.0.0.1:5000"
TEST_FILE = r"E:\req_com1\MEMS陀螺软件需求规格说明.docx"

def test_parse_api():
    print("=" * 60)
    print("测试 /api/parse 接口")
    print("=" * 60)

    # 上传文件获取doc_id
    print("\n1. 上传测试文件...")
    try:
        with open(TEST_FILE, 'rb') as f:
            files = {'file': (os.path.basename(TEST_FILE), f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            response = requests.post(f"{BASE_URL}/api/upload", files=files, timeout=60)
        
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

    # 调用parse接口
    print("\n2. 调用 /api/parse 接口...")
    try:
        response = requests.post(f"{BASE_URL}/api/parse", json={'doc_id': doc_id}, timeout=60)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ 解析成功, 状态码: {response.status_code}")
            
            # 导出原始响应到文件
            output_file = 'parse_response.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"   ✓ 原始响应已导出到: {output_file}")
            print(f"   文件大小: {os.path.getsize(output_file)} 字节")
        else:
            print(f"   ✗ 解析失败: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

if __name__ == '__main__':
    try:
        test_parse_api()
    except KeyboardInterrupt:
        print("\n测试已取消")
