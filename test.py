import requests

API_KEY = "sk-2ead6866ebc24ccf990b7c8b4d141628"
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL   = "deepseek-v4-pro"
TIMEOUT = 270

def call_llm_api(prompt, model, api_key, api_url, timeout=TIMEOUT):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    data = {
        'model': model,
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
        'max_tokens': 32
    }

    try:
        session = requests.Session()
        response = session.post(
            api_url.rstrip('/') + '/chat/completions',
            headers=headers,
            json=data,
            timeout=timeout
        )
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"API调用失败: {str(e)}")
        return None


if __name__ == '__main__':
    print(f"测试地址: {API_URL}")
    print(f"测试模型: {MODEL}")
    print(f"超时设置: {TIMEOUT}s")
    print("-" * 40)

    reply = call_llm_api("你好，请用一句话回复我。", MODEL, API_KEY, API_URL)

    if reply:
        print(f"连通成功，模型回复: {reply}")
    else:
        print("连通失败，请检查 API_KEY / API_URL / MODEL 配置。")
