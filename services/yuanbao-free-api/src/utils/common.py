"""通用工具函数模块"""

from typing import Dict

from src.services.browser import browser_manager


class YuanbaoLoginRequiredError(RuntimeError):
    """浏览器会话尚未完成登录，当前请求应作为正常未就绪状态返回。"""


async def generate_headers() -> Dict[str, str]:
    """生成请求头，从浏览器管理器获取最新的认证信息

    Returns:
        Dict[str, str]: 包含认证信息的请求头

    Raises:
        Exception: 无法获取请求头时抛出
    """
    headers = await browser_manager.get_headers()
    if not headers:
        raise YuanbaoLoginRequiredError("元宝浏览器会话尚未登录")

    return dict(headers)
