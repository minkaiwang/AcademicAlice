"""Ollama 公共常量、日志与 Qt 信号。"""

from PyQt5.QtCore import QObject, pyqtSignal

from config.ollama_config import OLLAMA
from lib.core.logger import get_logger

logger = get_logger(__name__)

OLLAMA_BASE_URL = OLLAMA.get('base_url', 'http://localhost:11434')
PING_INTERVAL_MS = OLLAMA.get('ping_interval_ms', 5000)
PULL_EMIT_INTERVAL = OLLAMA.get('pull_emit_interval', 2.0)
PULL_READ_TIMEOUT = max(30.0, float(OLLAMA.get('pull_read_timeout', 900.0)))
API_RATE_LIMIT_WINDOW_SECS = 60
API_RATE_LIMIT_MAX_REQUESTS = 10


class _OllamaSignal(QObject):
    """线程安全信号：后台线程通过此对象将结果传回 Qt 主线程"""

    status_ready = pyqtSignal(bool, list)  # (is_running, models)
    chunk_ready  = pyqtSignal(int, str)    # (request_id, accumulated_text) - 流式块
    chat_ready   = pyqtSignal(int, str)    # (request_id, full_response_text) - 完成信号
