import requests
import json
from config import API_KEY_DEFAULT, API_URL_DEFAULT, API_MODEL_DEFAULT, API_TIMEOUT

def test_model_api_direct():
    print("直接测试大模型API调用...")
    print(f"API URL: {API_URL_DEFAULT}")
    print(f"Model: {API_MODEL_DEFAULT}")
    print(f"API Key: {API_KEY_DEFAULT[:4]}...{API_KEY_DEFAULT[-4:]}")  # 只显示部分API Key，保护隐私
    print(f"Timeout: {API_TIMEOUT} seconds")
    
    # 构造请求头
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY_DEFAULT}'
    }
    
    # 构造请求数据
    data = {
        'model': API_MODEL_DEFAULT,
        'messages': [
            {
                'role': 'system',
                'content': '你是一个专业的需求文档审查专家，精通软件工程和需求分析。'
            },
            {
                'role': 'user',
                'content': '你好，请简要介绍一下自己。'
            }
        ],
        'temperature': 0.3,
        'max_tokens': 1000
    }
    
    try:
        # 创建会话并强制跳过代理设置
        session = requests.Session()
        session.trust_env = False  # 不使用系统环境变量中的代理设置
        
        # 直接发送请求
        print("\n正在发送API请求...")
        response = session.post(
            API_URL_DEFAULT + '/chat/completions',
            headers=headers,
            json=data,
            timeout=API_TIMEOUT
        )
        
        # 检查响应状态码
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            # 解析响应内容
            result = response.json()
            print("\nAPI调用成功！")
            print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            # 提取模型回复
            if 'choices' in result and len(result['choices']) > 0:
                model_reply = result['choices'][0]['message']['content']
                print(f"\n模型回复: {model_reply}")
            return True
        else:
            # 打印错误信息
            print(f"\nAPI调用失败: {response.text}")
            return False
    except Exception as e:
        print(f"\nAPI调用失败: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_model_api_direct()
    if success:
        print("\n大模型API集成正常，可以使用。")
    else:
        print("\n大模型API集成存在问题，需要检查网络连接或API配置。")
