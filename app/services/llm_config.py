"""LLM 接入配置：Base URL 规范化与 chat/completions 地址构建。"""

from __future__ import annotations

from urllib.parse import urlparse


def normalize_llm_base_url(base_url: str) -> str:
    """规范化 OpenAI 兼容 API 的 Base URL。"""
    url = (base_url or '').strip().rstrip('/')
    if not url:
        return url

    # DeepSeek 控制台地址常被误填为 API 地址
    if 'platform.deepseek.com' in url:
        return 'https://api.deepseek.com/v1'

    parsed = urlparse(url if '://' in url else f'https://{url}')
    host = (parsed.netloc or parsed.path.split('/')[0]).lower()
    path = parsed.path.rstrip('/')

    if host == 'api.deepseek.com' and not path.endswith('/v1'):
        return f'{parsed.scheme}://{host}/v1'

    return url


def build_chat_completions_url(base_url: str) -> str:
    """由 Base URL 构建 /chat/completions 完整请求地址。"""
    url = normalize_llm_base_url(base_url).rstrip('/')
    if url.endswith('/chat/completions'):
        return url
    return f'{url}/chat/completions'


def format_llm_request_error(error: Exception, base_url: str) -> str:
    """将底层 HTTP 异常转为更易理解的提示。"""
    msg = str(error)
    normalized = normalize_llm_base_url(base_url)
    raw = (base_url or '').strip().rstrip('/')

    if 'platform.deepseek.com' in raw:
        return (
            'Base URL 填写有误：platform.deepseek.com 是 DeepSeek 控制台页面，'
            'API 地址应为 https://api.deepseek.com/v1'
        )

    if '429' in msg:
        hint = ''
        if raw and raw != normalized:
            hint = f' 已检测到可能的错误地址，建议改为 {normalized}。'
        return f'请求过于频繁 (429)，请稍后重试或检查 API Key 配额。{hint}'.strip()

    if '401' in msg or 'Unauthorized' in msg:
        return 'API Key 无效或已过期，请检查后重试。'

    if '404' in msg:
        return (
            f'接口地址不存在 (404)：请确认 Base URL 是否正确（当前请求 {normalized}/chat/completions）。'
        )

    return msg
