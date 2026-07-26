"""爱弥斯科研工作台：本机 127.0.0.1 静态服务 + 默认浏览器（便于与 PyQt 桌宠同包分发）。

静态页默认路径：`resc/workbench/research_workbench.html`（兼容旧名 `phd_workbench.html`；
上游博士工作台单页思路来自 AugustUp/phd_master_system，MIT）。上游 readme 致谢摘录见
`resc/workbench/README.txt` 与根目录 `README.md`；完整说明以 https://github.com/AugustUp/phd_master_system 为准。
若无本地文件则回退打开 GitHub 仓库说明页。
"""

from __future__ import annotations

import json
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse

from lib.core.logger import get_logger
from lib.script.workbench_storage import (
    MAX_STATE_BYTES,
    WorkbenchStorageError,
    clear_workbench_state,
    load_workbench_state,
    save_workbench_state,
)

_logger = get_logger(__name__)

UPSTREAM_REPO_URL = "https://github.com/AugustUp/phd_master_system"
PREFERRED_PORT = 38473
PORT_FALLBACK_COUNT = 8
STATE_API_PATH = "/api/workbench/state"
HEALTH_API_PATH = "/api/workbench/health"
_STATIC_SUFFIXES = {".html", ".css", ".js", ".woff2", ".txt", ".md"}

_server: Optional[ThreadingHTTPServer] = None
_server_url: Optional[str] = None
_server_thread: Optional[threading.Thread] = None
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


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _handler_class(root: Path, *, state_path: Path | None = None):
    resolved_root = root.resolve()
    root_s = str(resolved_root)
    entry_name = next(
        (
            name
            for name in ("research_workbench.html", "index.html")
            if (resolved_root / name).is_file()
        ),
        "",
    )

    class _Handler(SimpleHTTPRequestHandler):
        server_version = "AemeathWorkbench/1.0"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=root_s, **kwargs)

        def log_message(self, fmt: str, *args) -> None:
            _logger.debug("workbench %s", fmt % args if args else fmt)

        def end_headers(self) -> None:
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
            )
            super().end_headers()

        def _send_json(self, status: int, payload: dict) -> None:
            body = _json_bytes(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _valid_host_header(self) -> bool:
            expected = f"127.0.0.1:{self.server.server_address[1]}"
            return str(self.headers.get("Host") or "").strip() == expected

        def _static_path_allowed(self, request_path: str) -> bool:
            decoded = unquote(request_path)
            parts = PurePosixPath(decoded.lstrip("/")).parts
            if (
                not parts
                or any(
                    part in ("", ".", "..")
                    or part.startswith(".")
                    or part.casefold().endswith(".bak")
                    for part in parts
                )
            ):
                return False
            relative = Path(*parts)
            if relative.suffix.casefold() not in _STATIC_SUFFIXES:
                return False
            target = resolved_root / relative
            try:
                target.resolve(strict=False).relative_to(resolved_root)
            except ValueError:
                return False
            return target.is_file() and not target.is_symlink()

        def _redirect_to_entry(self) -> None:
            if not entry_name:
                self.send_error(404, "Not Found")
                return
            self.send_response(302)
            self.send_header("Location", f"/{entry_name}")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def list_directory(self, path):
            del path
            self.send_error(404, "Directory listing disabled")
            return None

        def _same_origin_write_allowed(self) -> bool:
            if not self._valid_host_header():
                return False
            if self.headers.get("X-Aemeath-Workbench", "") != "1":
                return False
            origin = str(self.headers.get("Origin") or "").strip()
            if not origin:
                return True
            parsed = urlparse(origin)
            return (
                parsed.scheme == "http"
                and parsed.hostname == "127.0.0.1"
                and parsed.netloc == self.headers.get("Host", "")
            )

        def _read_json_body(self) -> dict:
            try:
                content_length = int(self.headers.get("Content-Length") or "0")
            except ValueError as exc:
                raise WorkbenchStorageError("Content-Length 无效") from exc
            if content_length <= 0:
                raise WorkbenchStorageError("请求体为空")
            if content_length > MAX_STATE_BYTES:
                raise WorkbenchStorageError("请求体超过工作台状态大小限制")
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise WorkbenchStorageError(f"请求 JSON 无效: {exc}") from exc
            if not isinstance(payload, dict):
                raise WorkbenchStorageError("工作台状态必须是 JSON 对象")
            return payload

        def do_GET(self) -> None:
            request_path = urlparse(self.path).path
            if not self._valid_host_header():
                self._send_json(421, {"ok": False, "error": "invalid_host"})
                return
            if request_path == HEALTH_API_PATH:
                self._send_json(200, {"ok": True, "storage": "file"})
                return
            if request_path == STATE_API_PATH:
                try:
                    result = load_workbench_state(state_path=state_path)
                except WorkbenchStorageError as exc:
                    _logger.error("读取工作台状态失败: %s", exc)
                    self._send_json(500, {"ok": False, "error": str(exc)})
                    return
                self._send_json(200, {"ok": True, **result})
                return
            if request_path == "/":
                self._redirect_to_entry()
                return
            if not self._static_path_allowed(request_path):
                self.send_error(404, "Not Found")
                return
            super().do_GET()

        def do_HEAD(self) -> None:
            request_path = urlparse(self.path).path
            if not self._valid_host_header():
                self._send_json(421, {"ok": False, "error": "invalid_host"})
                return
            if request_path == "/":
                self._redirect_to_entry()
                return
            if request_path in (HEALTH_API_PATH, STATE_API_PATH):
                self._send_json(405, {"ok": False, "error": "method_not_allowed"})
                return
            if not self._static_path_allowed(request_path):
                self.send_error(404, "Not Found")
                return
            super().do_HEAD()

        def do_PUT(self) -> None:
            parsed_url = urlparse(self.path)
            request_path = parsed_url.path
            if request_path != STATE_API_PATH:
                self._send_json(404, {"ok": False, "error": "not_found"})
                return
            if not self._same_origin_write_allowed():
                self._send_json(403, {"ok": False, "error": "forbidden"})
                return
            try:
                payload = self._read_json_body()
                force_backup = (
                    parse_qs(parsed_url.query).get("force_backup", ["0"])[0]
                    == "1"
                )
                result = save_workbench_state(
                    payload,
                    state_path=state_path,
                    force_backup=force_backup,
                )
            except WorkbenchStorageError as exc:
                self._send_json(400, {"ok": False, "error": str(exc)})
                return
            except OSError as exc:
                _logger.error("写入工作台状态失败: %s", exc)
                self._send_json(500, {"ok": False, "error": "write_failed"})
                return
            self._send_json(200, {"ok": True, **result})

        def do_DELETE(self) -> None:
            request_path = urlparse(self.path).path
            if request_path != STATE_API_PATH:
                self._send_json(404, {"ok": False, "error": "not_found"})
                return
            if not self._same_origin_write_allowed():
                self._send_json(403, {"ok": False, "error": "forbidden"})
                return
            try:
                result = clear_workbench_state(state_path=state_path)
            except OSError as exc:
                _logger.error("清空工作台状态失败: %s", exc)
                self._send_json(500, {"ok": False, "error": "clear_failed"})
                return
            self._send_json(200, {"ok": True, **result})

        def do_OPTIONS(self) -> None:
            self._send_json(405, {"ok": False, "error": "method_not_allowed"})

    return _Handler


def create_workbench_server(
    root: Path,
    *,
    preferred_port: int = PREFERRED_PORT,
    state_path: Path | None = None,
    allow_fallback: bool = True,
) -> ThreadingHTTPServer:
    handler = _handler_class(root, state_path=state_path)
    ports = [preferred_port]
    if allow_fallback:
        ports = [
            preferred_port + offset
            for offset in range(max(1, PORT_FALLBACK_COUNT))
        ]
        ports.append(0)
    last_error: OSError | None = None
    for port in ports:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), handler)
            server.daemon_threads = True
            return server
        except OSError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise OSError("无法创建工作台本机服务")


def _ensure_local_server_url() -> Optional[str]:
    """保证本机工作台服务已启动，并返回稳定优先的页面 URL。"""
    global _server, _server_url, _server_thread
    html = workbench_html_path()
    if not html.is_file():
        return None
    root = html.parent.resolve()

    with _server_lock:
        if _server is not None and _server_url is not None:
            return _server_url

        try:
            srv = create_workbench_server(root)
        except OSError as e:
            _logger.warning("爱弥斯科研工作台本机服务无法绑定: %s", e)
            return None

        port = srv.server_address[1]
        url = f"http://127.0.0.1:{port}/{html.name}"
        th = threading.Thread(target=srv.serve_forever, name="deskpet-workbench-http", daemon=True)
        th.start()
        _server = srv
        _server_url = url
        _server_thread = th
        if port != PREFERRED_PORT:
            _logger.warning(
                "工作台首选端口 %s 被占用，已使用 %s；主数据仍保存在稳定文件中",
                PREFERRED_PORT,
                port,
            )
        _logger.info("爱弥斯科研工作台本机页: %s", url)
        return url


def cleanup_workbench_host() -> None:
    """停止本机工作台 HTTP 服务。"""
    global _server, _server_url, _server_thread
    with _server_lock:
        server = _server
        thread = _server_thread
        _server = None
        _server_url = None
        _server_thread = None
    if server is None:
        return
    try:
        server.shutdown()
    except Exception as exc:
        _logger.debug("停止工作台服务失败: %s", exc)
    try:
        server.server_close()
    except Exception as exc:
        _logger.debug("关闭工作台监听失败: %s", exc)
    if thread is not None and thread.is_alive():
        thread.join(timeout=2.0)


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
