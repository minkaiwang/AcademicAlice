"""Bundled yuanbao-free-api local service bootstrap."""

from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from lib.script.app.win_subprocess import run as _subprocess_run_hidden

import config.ollama_config as oc
from config.shared_storage_paths import get_shared_root_dir
from lib.core.event.center import Event, EventType, get_event_center
from lib.core.logger import get_logger

logger = get_logger(__name__)

_STARTUP_WAIT_SECS = 165.0
_POLL_INTERVAL_SECS = 0.5
_LOGIN_MONITOR_SECS = 300.0
_SERVICE_REQUIRED_FILES = ('app.py', 'requirements.txt')
_STATUS_ENDPOINT = '/fsv/status'
_LOGIN_ENDPOINT = '/fsv/login'
_LOGOUT_ENDPOINT = '/fsv/logout'
_REQUIRED_MODULES = (
    'fastapi',
    'uvicorn',
    'openai',
    'httpx',
    'pydantic_settings',
    'sse_starlette',
    'playwright',
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _service_dir() -> Path:
    return _project_root() / 'services' / 'yuanbao-free-api'


def _service_entry() -> Path:
    return _service_dir() / 'app.py'


def _log_path() -> Path:
    path = get_shared_root_dir() / 'yuanbao_free_api' / 'launcher.log'
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _qrcode_path() -> Path:
    path = get_shared_root_dir() / 'yuanbao_free_api' / 'qrcode.png'
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_service_bundle_extracted() -> bool:
    if all((_service_dir() / name).exists() for name in _SERVICE_REQUIRED_FILES):
        return True
    logger.warning(
        '[YuanbaoFreeApiService] 发行包缺少受版本控制的服务目录: %s；'
        '已拒绝下载或解压未经校验的外部源码',
        _service_dir(),
    )
    return False


def _launcher_python() -> str:
    executable = Path(sys.executable)
    if executable.name.lower() == 'pythonw.exe':
        python_exe = executable.with_name('python.exe')
        if python_exe.exists():
            return str(python_exe)
    return str(executable)


def _launcher_command(port: int) -> list[str]:
    if getattr(sys, 'frozen', False):
        return [
            str(Path(sys.executable)),
            '--yuanbao-service',
            str(port),
        ]
    return [
        _launcher_python(),
        '-m',
        'uvicorn',
        'app:app',
        '--host',
        '127.0.0.1',
        '--port',
        str(port),
    ]


def _build_page_url(agent_id: str, login_url: str) -> str:
    text = str(login_url or '').strip()
    if text.startswith('http://') or text.startswith('https://'):
        if '/chat/' in text:
            return text
        return f"{text.rstrip('/')}/chat/{agent_id}"
    return f'https://yuanbao.tencent.com/chat/{agent_id}'


def _configured_api_key() -> str:
    active = oc.get_active_config() if hasattr(oc, 'get_active_config') else {}
    return str(
        (active or {}).get('api_key')
        or getattr(oc, 'API_KEY', '')
        or ''
    ).strip()


def _control_headers() -> Dict[str, str]:
    api_key = _configured_api_key()
    return {'Authorization': f'Bearer {api_key}'} if api_key else {}


def _build_service_env() -> Dict[str, str]:
    options = getattr(oc, 'YUANBAO_FREE_API', {}) or {}
    api_key = _configured_api_key()
    agent_id = str(options.get('agent_id', '') or 'naQivTmsDa').strip() or 'naQivTmsDa'
    page_url = _build_page_url(agent_id, str(options.get('login_url', '') or '').strip())

    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    env.setdefault('PYTHONUNBUFFERED', '1')
    env['API_KEYS'] = api_key
    env['AGENT_ID'] = agent_id
    env['PAGE_URL'] = page_url
    env['QRCODE_PATH'] = str(_qrcode_path())
    env['STORAGE_STATE_PATH'] = str(
        get_shared_root_dir() / 'yuanbao_free_api' / 'storage_state.json'
    )
    env['AEMEATH_YUANBAO_BOOT_LOG'] = str(_log_path())
    return env


def _remove_qrcode_if_exists() -> None:
    try:
        if _qrcode_path().exists():
            _qrcode_path().unlink()
    except Exception:
        pass


def _parse_local_target() -> Optional[Tuple[str, int]]:
    base_url = str(getattr(oc, 'API_BASE_URL', '') or '').strip()
    if not base_url:
        return None
    parsed = urlparse(base_url)
    host = (parsed.hostname or '').strip().lower()
    if host not in ('127.0.0.1', 'localhost'):
        return None
    try:
        port = int(parsed.port or (443 if parsed.scheme == 'https' else 80))
    except ValueError:
        return None
    if not (1 <= port <= 65535):
        return None
    return host, port


def _should_manage_local_service() -> bool:
    options = getattr(oc, 'YUANBAO_FREE_API', {}) or {}
    force_mode = str(getattr(oc, 'FORCE_REPLY_MODE', '') or '').strip()
    if not bool(options.get('enabled', False)) and force_mode != '4':
        return False
    return _parse_local_target() is not None


def _can_connect(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _status_url(host: str, port: int) -> str:
    return f'http://{host}:{port}{_STATUS_ENDPOINT}'


def _login_url(host: str, port: int) -> str:
    return f'http://{host}:{port}{_LOGIN_ENDPOINT}'


def _logout_url(host: str, port: int) -> str:
    return f'http://{host}:{port}{_LOGOUT_ENDPOINT}'


def _http_json(url: str, *, method: str = 'GET', timeout: float = 5.0) -> Optional[Dict[str, object]]:
    request = Request(
        url,
        method=method.upper(),
        headers=_control_headers(),
    )
    if method.upper() == 'POST':
        request.add_header('Content-Type', 'application/json')
        request.data = b'{}'
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or 'utf-8'
            payload = response.read().decode(charset, errors='ignore').strip()
            if not payload:
                return {}
            data = json.loads(payload)
            return data if isinstance(data, dict) else {'value': data}
    except (OSError, URLError, ValueError) as exc:
        logger.debug('[YuanbaoFreeApiService] HTTP %s %s failed: %s', method, url, exc)
        return None


def _probe_status_endpoint(host: str, port: int, timeout: float = 3.0) -> Tuple[str, Optional[Dict[str, object]]]:
    if not _can_connect(host, port, timeout=min(timeout, 1.0)):
        return 'offline', None

    request = Request(
        _status_url(host, port),
        method='GET',
        headers=_control_headers(),
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or 'utf-8'
            payload = response.read().decode(charset, errors='ignore').strip()
            if not payload:
                return 'ok', {}
            data = json.loads(payload)
            if isinstance(data, dict):
                return 'ok', data
            return 'invalid', {'value': data}
    except HTTPError as exc:
        logger.debug('[YuanbaoFreeApiService] HTTP GET %s failed: %s', _status_url(host, port), exc)
        if exc.code == 404:
            return 'missing', None
        if exc.code in (401, 403):
            return 'unauthorized', None
        return 'http_error', None
    except (OSError, URLError, ValueError) as exc:
        logger.debug('[YuanbaoFreeApiService] HTTP GET %s failed: %s', _status_url(host, port), exc)
        return 'error', None


def _fetch_service_status(host: str, port: int, timeout: float = 3.0) -> Optional[Dict[str, object]]:
    state, status = _probe_status_endpoint(host, port, timeout=timeout)
    return status if state == 'ok' else None


def _request_service_login(host: str, port: int, timeout: float = 10.0) -> Optional[Dict[str, object]]:
    return _http_json(_login_url(host, port), method='POST', timeout=timeout)


def _request_service_logout(host: str, port: int, timeout: float = 10.0) -> Optional[Dict[str, object]]:
    return _http_json(_logout_url(host, port), method='POST', timeout=timeout)


def _status_bool(status: Optional[Dict[str, object]], key: str) -> bool:
    return bool((status or {}).get(key, False))


def _status_text(status: Optional[Dict[str, object]], key: str) -> str:
    return str((status or {}).get(key, '') or '').strip()


def _read_qrcode_bytes() -> Optional[bytes]:
    try:
        path = _qrcode_path()
        if path.exists():
            return path.read_bytes()
    except Exception:
        pass
    return None


def _describe_status_message(status: Optional[Dict[str, object]]) -> str:
    stage = _status_text(status, 'last_message')
    if _status_bool(status, 'logged_in'):
        return '元宝已登录，可直接使用。'
    if _status_bool(status, 'qrcode_exists'):
        return '请使用微信扫码登录元宝。'
    if _status_text(status, 'last_error'):
        return _status_text(status, 'last_error')
    mapping = {
        'starting_login': '正在初始化登录流程',
        'starting_playwright': '正在启动浏览器驱动',
        'launching_browser': '正在启动浏览器',
        'creating_page': '正在创建页面',
        'page_loading': '正在打开元宝页面',
        'page_loaded': '元宝页面已打开，正在继续登录',
        'browser_initialized': '浏览器已就绪，正在继续登录',
        'dismissing_dialog': '正在关闭页面弹窗',
        'resolving_login_button': '正在定位登录入口',
        'waiting_login_button': '正在等待登录入口出现',
        'clicking_login_button': '正在点击登录入口',
        'login_button_clicked': '登录入口已点击，正在等待二维码',
        'login_button_not_found': '未找到登录入口',
        'waiting_qrcode': '正在等待二维码出现',
        'qrcode_ready': '二维码已生成，请使用微信扫码登录元宝。',
        'waiting_scan_confirm': '二维码已生成，正在等待扫码确认',
        'login_success': '元宝登录成功',
        'login_timeout': '扫码超时，请重新扫码',
        'browser_init_failed': '浏览器初始化失败',
        'login_failed': '元宝登录失败',
    }
    return mapping.get(stage, '正在准备元宝扫码登录...')


def _missing_runtime_modules() -> list[str]:
    missing: list[str] = []
    for name in _REQUIRED_MODULES:
        if importlib.util.find_spec(name) is None:
            missing.append(name)
    return missing


def _format_yuanbao_missing_deps_hint(modules: list[str]) -> str:
    """启动时缺依赖的气泡说明（用户常口述为「什么未安装」）。"""
    joined = '、'.join(modules)
    return (
        f'检测到元宝本地中转依赖未安装或未就绪：{joined}。\n\n'
        '请先运行仓库根目录「安装依赖.bat」（或 install/install_deps.py），装好后重启桌宠。\n\n'
        '若暂时不用元宝 Web：请打开 config/ollama_config.py，将 FORCE_REPLY_MODE 改为 2（本地 Ollama）'
        '或留空并按说明配置可用的 API_BASE_URL，保存后重启。'
    )


class YuanbaoFreeApiService:
    def __init__(self):
        self._ec = get_event_center()
        self._proc_lock = threading.RLock()
        self._login_monitor_lock = threading.RLock()
        self._process: Optional[subprocess.Popen] = None
        self._login_monitor_thread: Optional[threading.Thread] = None
        self._login_monitor_stop = threading.Event()
        self._started_by_app = False
        self._ec.subscribe(EventType.APP_PRE_START, self._on_app_pre_start)

    def _on_app_pre_start(self, _event: Event):
        if not _should_manage_local_service():
            return
        missing = _missing_runtime_modules()
        if missing:
            text = _format_yuanbao_missing_deps_hint(missing)
            logger.warning('[YuanbaoFreeApiService] 跳过启动本地中转：%s', '、'.join(missing))
            self._ec.publish(Event(EventType.INFORMATION, {
                'text': text,
                'min': 28,
                'max': 420,
                'particle': False,
            }))
            return
        self.ensure_service_ready()

    def _ensure_login_dialog(self) -> None:
        if threading.current_thread() is not threading.main_thread():
            logger.debug('[YuanbaoFreeApiService] Skip login dialog init in background thread; wait for main thread to create it')
            return
        try:
            from lib.script.ui.yuanbao_login_dialog import init_yuanbao_login_dialog
            init_yuanbao_login_dialog()
        except Exception as exc:
            logger.debug('[YuanbaoFreeApiService] 初始化登录对话框失败: %s', exc)

    def _publish_login_dialog_show(self, status: Optional[Dict[str, object]] = None) -> None:
        self._ensure_login_dialog()
        payload = {
            'title': '元宝扫码登录',
            'status': _describe_status_message(status),
            'qr_png': _read_qrcode_bytes(),
        }
        self._ec.publish(Event(EventType.YUANBAO_LOGIN_QR_SHOW, payload))

    def _publish_login_dialog_status(self, status: Optional[Dict[str, object]] = None) -> None:
        self._ensure_login_dialog()
        payload = {
            'status': _describe_status_message(status),
            'qr_png': _read_qrcode_bytes(),
            'logged_in': _status_bool(status, 'logged_in'),
        }
        self._ec.publish(Event(EventType.YUANBAO_LOGIN_QR_STATUS, payload))

    def _publish_login_dialog_hide(self) -> None:
        self._ec.publish(Event(EventType.YUANBAO_LOGIN_QR_HIDE, {}))

    def _start_login_monitor(self, host: str, port: int) -> None:
        with self._login_monitor_lock:
            thread = self._login_monitor_thread
            if thread is not None and thread.is_alive():
                return
            self._login_monitor_stop.clear()
            thread = threading.Thread(
                target=self._run_login_monitor,
                args=(host, port),
                daemon=True,
                name='yuanbao-login-monitor',
            )
            self._login_monitor_thread = thread
            thread.start()

    def _stop_login_monitor(self, timeout: float = 3.0) -> bool:
        self._login_monitor_stop.set()
        with self._login_monitor_lock:
            thread = self._login_monitor_thread
        if thread is None:
            return True
        if thread is not threading.current_thread():
            thread.join(timeout=max(0.0, timeout))
        stopped = not thread.is_alive()
        if stopped:
            with self._login_monitor_lock:
                if self._login_monitor_thread is thread:
                    self._login_monitor_thread = None
        return stopped

    def _run_login_monitor(self, host: str, port: int) -> None:
        deadline = time.monotonic() + _LOGIN_MONITOR_SECS
        last_status: Optional[Dict[str, object]] = None
        try:
            while (
                time.monotonic() < deadline
                and not self._login_monitor_stop.is_set()
            ):
                status = _fetch_service_status(host, port, timeout=2.0)
                if status is not None:
                    last_status = status
                    self._publish_login_dialog_status(status)
                    if _status_bool(status, 'logged_in'):
                        self._publish_status_hint(status)
                        self._publish_login_dialog_hide()
                        return
                self._login_monitor_stop.wait(_POLL_INTERVAL_SECS)
        finally:
            with self._login_monitor_lock:
                current = threading.current_thread()
                if self._login_monitor_thread is current:
                    self._login_monitor_thread = None
        if last_status is not None:
            self._publish_login_dialog_status(last_status)

    def get_service_status(self) -> Optional[Dict[str, object]]:
        target = _parse_local_target()
        if target is None:
            return None
        host, port = target
        return self._ensure_status_endpoint(host, port)

    def ensure_service_ready(self) -> bool:
        target = _parse_local_target()
        if target is None:
            return False
        host, port = target
        status = self._ensure_status_endpoint(host, port)
        if status is None:
            return False
        if _status_bool(status, 'logged_in'):
            logger.info('[YuanbaoFreeApiService] 元宝服务已登录并就绪: %s:%s', host, port)
            return True
        if (not _status_bool(status, 'qrcode_exists')
                and not _status_bool(status, 'login_in_progress')
                and not _status_text(status, 'last_error')):
            login_result = _request_service_login(host, port)
            if login_result:
                logger.info('[YuanbaoFreeApiService] 已触发元宝登录流程: %s', login_result)
                status = self._wait_for_login_state(host, port, allow_logged_out=True) or status
        self._publish_status_hint(status)
        return _status_bool(status, 'logged_in')

    def stop_login_flow(self) -> Dict[str, object]:
        self._publish_login_dialog_hide()
        monitor_stopped = self._stop_login_monitor()
        if not monitor_stopped:
            logger.warning('[YuanbaoFreeApiService] 元宝登录监控线程未在超时内结束')
        target = _parse_local_target()
        result: Dict[str, object] = {'success': True, 'message': 'stopped'}
        if target is not None:
            host, port = target
            logout_result = _request_service_logout(host, port, timeout=8.0)
            if isinstance(logout_result, dict):
                result.update(logout_result)
        with self._proc_lock:
            proc = self._process
            started = self._started_by_app
            self._process = None
            self._started_by_app = False
        if started and proc is not None:
            self._terminate_process_tree(proc)
        return result

    def begin_login_flow(self) -> Dict[str, object]:
        _remove_qrcode_if_exists()
        self._publish_login_dialog_show({'last_message': 'starting_login'})
        target = _parse_local_target()
        if target is None:
            self._publish_login_dialog_status({'last_error': '当前接口地址不是本地 YuanBao-Free-API。'})
            return {
                'success': False,
                'message': '当前接口地址不是本地 YuanBao-Free-API，无法启动登录流程。',
            }

        host, port = target
        status = self._ensure_status_endpoint(host, port)
        if status is None:
            self._publish_login_dialog_status({'last_error': f'元宝服务未能启动，请查看 {_log_path().name}。'})
            return {
                'success': False,
                'message': f'元宝服务未能启动，请查看 {_log_path().name}。',
            }

        if _status_bool(status, 'logged_in'):
            self._publish_login_dialog_hide()
            return {
                'success': True,
                'logged_in': True,
                'qrcode_exists': _status_bool(status, 'qrcode_exists'),
                'status': status,
                'message': '元宝服务已登录，可直接使用。',
            }

        login_result = _request_service_login(host, port)
        if login_result is None:
            refreshed = self._wait_for_login_state(host, port, allow_logged_out=True) or status
            self._publish_login_dialog_status(refreshed)
            error_text = _status_text(refreshed, 'last_error') or '无法调用元宝登录接口。'
            return {
                'success': False,
                'logged_in': _status_bool(refreshed, 'logged_in'),
                'qrcode_exists': _status_bool(refreshed, 'qrcode_exists'),
                'status': refreshed,
                'message': error_text,
            }

        refreshed = self._wait_for_login_state(host, port, allow_logged_out=True) or self.get_service_status() or status
        self._publish_status_hint(refreshed)
        self._publish_login_dialog_status(refreshed)
        last_error = _status_text(refreshed, 'last_error')
        if _status_bool(refreshed, 'logged_in'):
            self._publish_login_dialog_hide()
            return {
                'success': True,
                'logged_in': True,
                'qrcode_exists': _status_bool(refreshed, 'qrcode_exists'),
                'status': refreshed,
                'message': '元宝登录已完成，可直接使用。',
            }
        if _status_bool(refreshed, 'qrcode_exists'):
            self._start_login_monitor(host, port)
            return {
                'success': True,
                'logged_in': False,
                'qrcode_exists': _status_bool(refreshed, 'qrcode_exists'),
                'status': refreshed,
                'message': '元宝二维码已就绪，请扫码完成登录。',
            }
        if _status_bool(refreshed, 'login_in_progress'):
            self._start_login_monitor(host, port)
            return {
                'success': False,
                'logged_in': False,
                'qrcode_exists': False,
                'status': refreshed,
                'message': '元宝登录流程已启动，但二维码尚未生成，请稍候再试。',
            }
        return {
            'success': False,
            'logged_in': False,
            'qrcode_exists': False,
            'status': refreshed,
            'message': last_error or _status_text(refreshed, 'last_message') or '元宝登录未能启动。',
        }

    def _ensure_status_endpoint(self, host: str, port: int) -> Optional[Dict[str, object]]:
        state, status = _probe_status_endpoint(host, port)
        if state == 'ok' and status is not None:
            logger.info('[YuanbaoFreeApiService] 检测到元宝服务已在运行: %s:%s status=%s', host, port, status)
            return status
        if state not in ('offline', 'ok'):
            with self._proc_lock:
                proc = self._process
                owned_listener = bool(
                    self._started_by_app
                    and proc is not None
                    and proc.poll() is None
                )
            if owned_listener:
                logger.warning(
                    '[YuanbaoFreeApiService] 自有服务状态异常（%s），正在安全重启',
                    state,
                )
                self._stop_owned_process()
                if not self._start_service_process(host, port):
                    return None
                return self._wait_for_status_endpoint(host, port)
            logger.warning(
                '[YuanbaoFreeApiService] %s:%s 已被其他或不兼容服务占用；'
                '状态=%s，拒绝结束未知进程',
                host,
                port,
                state,
            )
            self._ec.publish(Event(EventType.INFORMATION, {
                'text': f'端口 {port} 已被其他服务占用。为避免误关程序，爱弥斯没有自动结束该进程；请更换端口或手动确认占用者。',
                'min': 24,
                'max': 300,
                'particle': False,
            }))
            return None
        if not self._start_service_process(host, port):
            return None
        return self._wait_for_status_endpoint(host, port)

    def _wait_for_status_endpoint(self, host: str, port: int) -> Optional[Dict[str, object]]:
        deadline = time.monotonic() + _STARTUP_WAIT_SECS
        while time.monotonic() < deadline:
            state, status = _probe_status_endpoint(host, port, timeout=2.0)
            if state == 'ok' and status is not None:
                logger.info('[YuanbaoFreeApiService] 元宝服务状态接口已就绪: %s', status)
                return status
            if state == 'missing':
                logger.error(
                    '[YuanbaoFreeApiService] 端口已响应但缺少状态接口，'
                    '拒绝结束未知进程: %s:%s',
                    host,
                    port,
                )
                break
            with self._proc_lock:
                proc = self._process
                if proc is not None and proc.poll() is not None:
                    break
            time.sleep(_POLL_INTERVAL_SECS)
        self._stop_owned_process()
        logger.error('[YuanbaoFreeApiService] 元宝服务状态接口启动失败，目标=%s:%s 日志=%s', host, port, _log_path())
        self._ec.publish(Event(EventType.INFORMATION, {
            'text': '元宝服务未能正常启动，请检查 logs/yuanbao_free_api_launcher.log。',
            'min': 18,
            'max': 220,
            'particle': False,
        }))
        return None

    def _wait_for_login_state(self, host: str, port: int, *, allow_logged_out: bool = False) -> Optional[Dict[str, object]]:
        deadline = time.monotonic() + 20.0
        last_status: Optional[Dict[str, object]] = None
        while time.monotonic() < deadline:
            status = _fetch_service_status(host, port, timeout=2.0)
            if status is not None:
                last_status = status
                self._publish_login_dialog_status(status)
                if _status_bool(status, 'logged_in'):
                    return status
                if _status_bool(status, 'qrcode_exists'):
                    return status
                if allow_logged_out and _status_text(status, 'last_error'):
                    return status
            time.sleep(_POLL_INTERVAL_SECS)
        return last_status

    def _publish_status_hint(self, status: Optional[Dict[str, object]]) -> None:
        if not status:
            return
        if _status_bool(status, 'logged_in'):
            self._ec.publish(Event(EventType.INFORMATION, {
                'text': '元宝服务已登录并就绪。',
                'min': 10,
                'max': 100,
                'particle': False,
            }))
            return
        if _status_bool(status, 'qrcode_exists'):
            qr_rel = _qrcode_path().relative_to(_project_root())
            self._ec.publish(Event(EventType.INFORMATION, {
                'text': f'元宝登录二维码已生成：{qr_rel}，请扫码完成登录。',
                'min': 18,
                'max': 220,
                'particle': False,
            }))
            return
        error_text = _status_text(status, 'last_error')
        if error_text:
            self._ec.publish(Event(EventType.INFORMATION, {
                'text': f'元宝登录初始化失败：{error_text}',
                'min': 20,
                'max': 260,
                'particle': False,
            }))

    def _start_service_process(self, host: str, port: int) -> bool:
        _remove_qrcode_if_exists()
        api_key = _configured_api_key()
        if (
            not api_key
            or ',' in api_key
            or any(char.isspace() for char in api_key)
        ):
            logger.warning(
                '[YuanbaoFreeApiService] 本地服务访问密钥为空或格式无效，已拒绝启动'
            )
            self._ec.publish(Event(EventType.INFORMATION, {
                'text': '请先在 AI 设置中填写不含逗号或空白字符的元宝本地服务访问密钥。',
                'min': 20,
                'max': 260,
                'particle': False,
            }))
            return False
        missing_modules = _missing_runtime_modules()
        if missing_modules:
            text = _format_yuanbao_missing_deps_hint(missing_modules)
            logger.warning('[YuanbaoFreeApiService] %s', text.replace('\n', ' '))
            self._ec.publish(Event(EventType.INFORMATION, {
                'text': text,
                'min': 28,
                'max': 420,
                'particle': False,
            }))
            return False
        entry = _service_entry()
        if not entry.exists():
            _ensure_service_bundle_extracted()
            entry = _service_entry()
        if not entry.exists():
            logger.warning('[YuanbaoFreeApiService] 未找到本地中转入口: %s', entry)
            self._ec.publish(Event(EventType.INFORMATION, {
                'text': '发行包缺少 yuanbao-free-api 服务目录，请重新获取完整的爱弥斯发行包。',
                'min': 16,
                'max': 160,
                'particle': False,
            }))
            return False

        with self._proc_lock:
            if self._process is not None and self._process.poll() is None:
                return True
            log_handle = _log_path().open('a', encoding='utf-8', errors='ignore')
            env = _build_service_env()
            create_no_window = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            try:
                self._process = subprocess.Popen(
                    _launcher_command(port),
                    cwd=str(_service_dir()),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    creationflags=create_no_window,
                )
                self._started_by_app = True
                log_handle.close()
            except Exception as exc:
                log_handle.close()
                logger.error('[YuanbaoFreeApiService] 启动本地中转失败: %s', exc)
                self._ec.publish(Event(EventType.INFORMATION, {
                    'text': f'元宝本地中转启动失败: {exc}',
                    'min': 16,
                    'max': 180,
                    'particle': False,
                }))
                self._process = None
                self._started_by_app = False
                return False

        deadline = time.monotonic() + _STARTUP_WAIT_SECS
        while time.monotonic() < deadline:
            if _can_connect(host, port):
                logger.info('[YuanbaoFreeApiService] 元宝服务端口已启动: %s:%s', host, port)
                return True
            with self._proc_lock:
                proc = self._process
                if proc is not None and proc.poll() is not None:
                    break
            time.sleep(_POLL_INTERVAL_SECS)

        logger.error('[YuanbaoFreeApiService] 元宝服务启动超时或已退出，目标=%s:%s 日志=%s', host, port, _log_path())
        self._stop_owned_process()
        self._ec.publish(Event(EventType.INFORMATION, {
            'text': '元宝服务未能成功启动，请检查 logs/yuanbao_free_api_launcher.log。',
            'min': 18,
            'max': 220,
            'particle': False,
        }))
        return False

    def cleanup(self):
        self._ec.unsubscribe(EventType.APP_PRE_START, self._on_app_pre_start)
        self._publish_login_dialog_hide()
        if not self._stop_login_monitor():
            logger.warning('[YuanbaoFreeApiService] 清理时登录监控线程未在超时内结束')

        with self._proc_lock:
            proc = self._process
            started = self._started_by_app
            self._process = None
            self._started_by_app = False

        if started and proc is not None:
            self._terminate_process_tree(proc)

    def _stop_owned_process(self) -> None:
        with self._proc_lock:
            proc = self._process
            started = self._started_by_app
            self._process = None
            self._started_by_app = False
        if started and proc is not None:
            self._terminate_process_tree(proc)

    @staticmethod
    def _terminate_process_tree(proc: subprocess.Popen) -> bool:
        if proc.poll() is not None:
            return True
        try:
            result = _subprocess_run_hidden(
                ['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
                check=False,
            )
            return result.returncode == 0
        except Exception as exc:
            logger.debug('[YuanbaoFreeApiService] 结束本地中转进程失败: %s', exc)
            return False


_instance: Optional[YuanbaoFreeApiService] = None


def get_yuanbao_free_api_service() -> YuanbaoFreeApiService:
    global _instance
    if _instance is None:
        _instance = YuanbaoFreeApiService()
    return _instance


def cleanup_yuanbao_free_api_service():
    global _instance
    if _instance is not None:
        _instance.cleanup()
        _instance = None


def get_yuanbao_free_api_qrcode_path() -> Path:
    return _qrcode_path()


def get_yuanbao_free_api_log_path() -> Path:
    return _log_path()
