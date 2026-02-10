import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath('.'))

from app.routes.validate import call_volcengine_ark
from config import API_KEY_DEFAULT, API_URL_DEFAULT, API_MODEL_DEFAULT

def test_model_api():
    print("测试大模型API调用...")
    print(f"API URL: {API_URL_DEFAULT}")
    print(f"Model: {API_MODEL_DEFAULT}")
    print(f"API Key: {API_KEY_DEFAULT[:4]}...{API_KEY_DEFAULT[-4:]}")  # 只显示部分API Key，保护隐私
    
    # 构造一个简单的测试提示词
    prompt = "你好，请简要介绍一下自己。"
    
    try:
        # 调用大模型API
        result = call_volcengine_ark(prompt, API_MODEL_DEFAULT, API_KEY_DEFAULT, API_URL_DEFAULT)
        print("\nAPI调用成功！")
        print(f"响应内容: {result}")
        return True
    except Exception as e:
        print(f"\nAPI调用失败: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_model_api()
    if success:
        print("\n大模型API集成正常，可以使用。")
    else:
        print("\n大模型API集成存在问题，需要检查网络连接或API配置。")
