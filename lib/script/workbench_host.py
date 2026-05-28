"""爱弥斯科研工作台：本机 127.0.0.1 静态服务 + 默认浏览器（便于与 PyQt 桌宠同包分发）。

静态页默认路径：`resc/workbench/research_workbench.html`（兼容旧名 `phd_workbench.html`；
上游博士工作台单页思路来自 AugustUp/phd_master_system，MIT）。上游 readme 致谢摘录见
`resc/workbench/README.txt` 与根目录 `README.md`；完整说明以 https://github.com/AugustUp/phd_master_system 为准。
若无本地文件则回退打开 GitHub 仓库说明页。
"""

from __future__ import annotations

import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from lib.core.logger import get_logger

_logger = get_logger(__name__)

UPSTREAM_REPO_URL = "https://github.com/AugustUp/phd_master_system"

_server: Optional[ThreadingHTTPServer] = None
_server_url: Optional[str] = None
_server_lock = threading.Lock()

# 避免双击、重复 INPUT_HASH、托盘与提示栏连续触发时在短时间内多次 webbrowser.open
_OPEN_DEBOUNCE_SEC = 2.0
_last_open_monotonic: float = 0.0
_last_open_target: Optional[str] = None
_open_debounce_lock = threading.Lock()


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def workbench_html_path() -> Path:
    root = _bundle_root() / "resc" / "workbench"
    preferred = root / "research_workbench.html"
    legacy = root / "phd_workbench.html"
    if preferred.is_file():
        return preferred
    return legacy


def _ensure_local_server_url() -> Optional[str]:
    """若本地 HTML 存在则保证后台线程里有一个只监听 127.0.0.1 的 HTTP 服务，并返回页面 URL。"""
    global _server, _server_url
    html = workbench_html_path()
    if not html.is_file():
        return None
    root = html.parent.resolve()
    root_s = str(root)

    with _server_lock:
        if _server is not None and _server_url is not None:
            return _server_url

        class _Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=root_s, **kwargs)

            def log_message(self, fmt: str, *args) -> None:
                _logger.debug("workbench %s", fmt % args if args else fmt)

        try:
            srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        except OSError as e:
            _logger.warning("爱弥斯科研工作台本机服务无法绑定: %s", e)
            return None

        port = srv.server_address[1]
        url = f"http://127.0.0.1:{port}/{html.name}"
        th = threading.Thread(target=srv.serve_forever, name="deskpet-workbench-http", daemon=True)
        th.start()
        _server = srv
        _server_url = url
        _logger.info("爱弥斯科研工作台本机页: %s", url)
        return url


def open_workbench_in_browser() -> bool:
    """
    在系统默认浏览器中打开爱弥斯科研工作台。

    Returns:
        True  已打开本机托管的 HTML；
        False 已回退为打开上游 GitHub 仓库页（通常因缺少本地 HTML）。
    """
    url = _ensure_local_server_url()
    if url is None:
        target = UPSTREAM_REPO_URL
        is_local = False
    else:
        target = url
        is_local = True

    now = time.monotonic()
    global _last_open_monotonic, _last_open_target
    with _open_debounce_lock:
        if (
            _last_open_target == target
            and (now - _last_open_monotonic) < _OPEN_DEBOUNCE_SEC
        ):
            _logger.debug(
                "跳过重复打开工作台（%.1fs 内已为同一 URL 触发）",
                _OPEN_DEBOUNCE_SEC,
            )
            return is_local

    try:
        webbrowser.open(target)
    except Exception as e:
        _logger.warning("打开浏览器失败: %s", e)
        return False

    with _open_debounce_lock:
        _last_open_monotonic = time.monotonic()
        _last_open_target = target
    return is_local
