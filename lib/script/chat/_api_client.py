"""Ollama / OpenAI API 客户端兼容入口。"""

from .api_client_openai import _ApiClientOpenAIMixin
from .api_client_ollama import _ApiClientOllamaMixin


class _ApiClientMixin(_ApiClientOpenAIMixin, _ApiClientOllamaMixin):
    """统一 API 客户端混入，组合 OpenAI 兼容接口与 Ollama。"""
