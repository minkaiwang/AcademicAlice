"""认证依赖模块"""

import logging
import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config import validate_api_key
from src.services.browser import browser_manager
from src.utils.common import YuanbaoLoginRequiredError, generate_headers

logger = logging.getLogger(__name__)
_last_login_required_log_at = 0.0
_LOGIN_REQUIRED_LOG_INTERVAL_SECONDS = 60.0

bearer_scheme = HTTPBearer(auto_error=False)


def require_api_key(
    authorization: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    """校验本地服务 Bearer 密钥，但不要求元宝已登录。"""
    if not authorization or not authorization.credentials:
        raise HTTPException(status_code=401, detail="need token")

    token = authorization.credentials

    if not validate_api_key(token):
        raise HTTPException(status_code=403, detail="invalid api_key")
    return token


async def get_authorized_headers(
    _token: str = Depends(require_api_key),
):
    """校验服务密钥与元宝登录态，并生成上游请求头。"""
    status = browser_manager.status()
    if not bool(status.get("logged_in", False)):
        _raise_login_required()
    try:
        headers = await generate_headers()
    except YuanbaoLoginRequiredError:
        _raise_login_required()

    return headers


def _raise_login_required() -> None:
    global _last_login_required_log_at
    now = time.monotonic()
    if now - _last_login_required_log_at >= _LOGIN_REQUIRED_LOG_INTERVAL_SECONDS:
        logger.info("Yuanbao session is not logged in; returning 503 without traceback")
        _last_login_required_log_at = now
    raise HTTPException(
        status_code=503,
        detail={
            "code": "yuanbao_login_required",
            "message": "请先在爱弥斯控制面板完成元宝扫码登录",
        },
        headers={"Retry-After": "30"},
    )
