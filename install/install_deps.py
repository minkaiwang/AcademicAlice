# -*- coding: utf-8 -*-
"""爱弥斯（学术桌面助手）— 依赖安装与启动器。

基于原 Flying Snow Velvet LTS 安装流程；流程:
1. 扫描系统 Python, 选择可用且版本最优的解释器.
2. 若缺少 pip, 自动尝试安装.
3. 评估镜像延迟并按优先级安装依赖.
4. 写入 py.ini:
   - python_executable
   - pythonw_executable
5. 下载 Vosk 中/英文模型到 resc/models/vosk-model-small-*/.
6. 准备 yuanbao-free-api 本地中转服务资源.
7. 启动主程序.

命令行：在参数中加入 `--no-launch` 可只安装依赖并写入 py.ini、不自动启动主程序。
"""

import configparser
import hashlib
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Optional
from urllib.parse import urlparse

# 本脚本位于 install/，仓库根为其上一级（与 py.ini、lib、resc 同级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 已由 CI 覆盖的最低支持 Python 版本
MIN_VERSION = (3, 11, 0)
# 超过该版本后, 仍可用, 但优先级降低(兼容性考虑)
MAX_PREFERRED_VERSION = (3, 13, 999)

PYPI_MIRRORS = [
    {"name": "Tsinghua", "url": "https://pypi.tuna.tsinghua.edu.cn/simple", "host": "pypi.tuna.tsinghua.edu.cn"},
    {"name": "Aliyun", "url": "https://mirrors.aliyun.com/pypi/simple", "host": "mirrors.aliyun.com"},
    {"name": "Tencent", "url": "https://mirrors.cloud.tencent.com/pypi/simple", "host": "mirrors.cloud.tencent.com"},
    {"name": "Douban", "url": "https://pypi.douban.com/simple", "host": "pypi.douban.com"},
    {"name": "Huawei", "url": "https://repo.huaweicloud.com/repository/pypi/simple", "host": "repo.huaweicloud.com"},
    {"name": "USTC", "url": "https://pypi.mirrors.ustc.edu.cn/simple", "host": "pypi.mirrors.ustc.edu.cn"},
    {"name": "PyPI", "url": "https://pypi.org/simple", "host": "pypi.org"},
]

DEPENDENCIES = [
    # (pip package, description, import checks)
    ("PyQt5", "Qt GUI framework", ("PyQt5",)),
    ("Pillow", "image processing", ("PIL",)),
    ("fastapi", "YuanBao relay API framework", ("fastapi",)),
    ("httpx", "async HTTP client for YuanBao relay", ("httpx",)),
    ("packaging", "version / requirement parsing helpers", ("packaging",)),
    ("openai", "OpenAI-compatible client for YuanBao relay", ("openai",)),
    ("opencv-python", "image preprocessing for YuanBao relay", ("cv2",)),
    ("playwright", "browser automation for YuanBao login capture", ("playwright",)),
    ("pydantic", "data validation for YuanBao relay", ("pydantic",)),
    ("pydantic-settings", "settings loader for YuanBao relay", ("pydantic_settings",)),
    ("pygame", "audio playback", ("pygame",)),
    ("requests", "HTTP client", ("requests",)),
    ("pyncm", "NetEase Cloud Music API", ("pyncm",)),
    ("qrcode", "QR code generation for music login", ("qrcode",)),
    ("sse-starlette", "SSE streaming for YuanBao relay", ("sse_starlette",)),
    ("mutagen", "local audio metadata parsing", ("mutagen",)),
    ("pycaw", "Windows audio meter", ("pycaw",)),
    ("comtypes", "COM bindings for pycaw", ("comtypes",)),
    ("pywin32", "Windows COM bridge (win32com/pythoncom)", ("pythoncom", "win32com")),
    ("sounddevice", "microphone capture for speech-to-text", ("sounddevice",)),
    ("uvicorn", "ASGI server for YuanBao relay", ("uvicorn",)),
    ("vosk", "offline speech-to-text engine", ("vosk",)),
]

LOCAL_DEPENDENCY_WHEELS = {
    "pyncm": {
        "path": PROJECT_ROOT / "vendor" / "pyncm-1.8.1-py3-none-any.whl",
        "sha256": "a1798e9ff9007723d0a34b4d61b51b385b5bedb6caac6e04ce5572d00193183c",
    },
}

TOTAL_STEPS = 6

YUANBAO_SERVICE_DIR = PROJECT_ROOT / "services" / "yuanbao-free-api"
YUANBAO_SERVICE_REQUIRED_FILES = ("app.py", "requirements.txt")
YUANBAO_SERVICE_BROWSER = "chromium"
PLAYWRIGHT_RESOURCE_ROOT = PROJECT_ROOT / "resc" / "playwright"
PLAYWRIGHT_RESOURCE_BROWSERS_DIR = PLAYWRIGHT_RESOURCE_ROOT / "browsers" / "ms-playwright"
PLAYWRIGHT_BROWSER_ARCHIVE_DIRS = (
    PLAYWRIGHT_RESOURCE_ROOT,
    PROJECT_ROOT / "resc" / "bundles",
)
PLAYWRIGHT_BROWSER_ARCHIVE_PATTERNS = (
    "*chromium*.zip",
    "*playwright*.zip",
)
PLAYWRIGHT_BROWSER_DIR_PREFIXES = ("chromium-",)
PLAYWRIGHT_BROWSER_EXECUTABLE_RELATIVE_PATHS = (
    Path("chrome-win") / "chrome.exe",
    Path("chrome-win64") / "chrome.exe",
)


def _enable_ansi_color() -> bool:
    if not sys.stdout.isatty():
        return False
    if os.name != "nt":
        return True
    if any(key in os.environ for key in ("ANSICON", "WT_SESSION", "TERM_PROGRAM")):
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            if mode.value & 0x0004:  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
                return True
            if kernel32.SetConsoleMode(handle, mode.value | 0x0004):
                return True
    except Exception:
        pass
    return False


_COLOR_ENABLED = _enable_ansi_color()
_COLOR_RESET = "\033[0m"
_COLOR_MAP = {
    "stage": "\033[95m",
    "info": "\033[96m",
    "ok": "\033[92m",
    "warn": "\033[93m",
    "error": "\033[91m",
}
_LABELS = {
    "info": "[信息] ",
    "ok": "[完成] ",
    "warn": "[警告] ",
    "error": "[错误] ",
}


def _fmt_color(text: str, kind: str) -> str:
    if not _COLOR_ENABLED:
        return text
    code = _COLOR_MAP.get(kind)
    if not code:
        return text
    return f"{code}{text}{_COLOR_RESET}"


def _print_kind(text: str, kind: str = "info", *, prefix: bool = True) -> None:
    if prefix:
        text = f"{_LABELS.get(kind, '')}{text}"
    print(_fmt_color(text, kind))


def _print_info(text: str) -> None:
    _print_kind(text, "info")


def _print_warn(text: str) -> None:
    _print_kind(text, "warn")


def _print_error(text: str) -> None:
    _print_kind(text, "error")


def _print_stage(step: int, text: str) -> None:
    message = f"\n[{step}/{TOTAL_STEPS}] {text}"
    print(_fmt_color(message, "stage"))


VOSK_MODEL_MARKERS = ("am", "conf", "graph", "ivector")
VOSK_MODELS_DIR = PROJECT_ROOT / "resc" / "models"
VOSK_MODEL_SPECS = (
    {
        "name": "vosk-model-small-cn-0.22",
        "label": "Chinese",
        "size": 43898754,
        "sha256": "3af8b0e7e0f835ae9d414ce5df580237a3cfb08d586c9fbbb0f7ff29ad5b14ba",
        "urls": (
            {"name": "Official", "url": "https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip"},
        ),
    },
    {
        "name": "vosk-model-small-en-us-0.15",
        "label": "English",
        "size": 41205931,
        "sha256": "30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498",
        "urls": (
            {"name": "Official", "url": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"},
        ),
    },
)

_MAX_DOWNLOAD_BYTES = 1024 * 1024 * 1024
_MAX_ARCHIVE_ENTRIES = 50_000
_MAX_EXTRACTED_BYTES = 4 * 1024 * 1024 * 1024
_MAX_SINGLE_FILE_BYTES = 2 * 1024 * 1024 * 1024
_MAX_COMPRESSION_RATIO = 200
_WINDOWS_DEVICE_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}

_NOT_FOUND_MARKERS = (
    "no matching distribution found",
    "could not find a version that satisfies",
    "no distributions at all",
)


def _run(cmd, timeout=12):
    """Run command quietly. Return CompletedProcess or None."""
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout,
        )
    except Exception:
        return None


def _python_module_cmd(python_exe, module, *args):
    return [python_exe, "-m", module, *args]


def _run_python_module(python_exe, module, *args, timeout=12):
    return _run(_python_module_cmd(python_exe, module, *args), timeout=timeout)


def _run_pip(python_exe, *args, timeout=12):
    return _run_python_module(python_exe, "pip", *args, timeout=timeout)


def _discover_all_pythons():
    """Find python executables from launcher, PATH, registry and common paths."""
    import glob

    candidates = []

    # 1) py launcher
    r = _run(["py", "-0p"])
    if r and r.returncode == 0:
        for line in r.stdout.splitlines():
            m = re.search(r"([A-Za-z]:\\[^\s]+python(?:w)?\.exe)", line, re.IGNORECASE)
            if m:
                exe = m.group(1)
                if os.path.isfile(exe):
                    candidates.append(exe)

    # 2) where python/python3
    for name in ("python", "python3"):
        r = _run(["where", name])
        if r and r.returncode == 0:
            for line in r.stdout.splitlines():
                exe = line.strip()
                if exe and "WindowsApps" not in exe and os.path.isfile(exe):
                    candidates.append(exe)

    # 3) Windows registry
    try:
        import winreg

        reg_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Python\PythonCore"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Python\PythonCore"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Python\PythonCore"),
        ]
        for hive, base in reg_paths:
            try:
                with winreg.OpenKey(hive, base) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            ver = winreg.EnumKey(key, i)
                            with winreg.OpenKey(hive, rf"{base}\{ver}\InstallPath") as ip:
                                exe, _ = winreg.QueryValueEx(ip, "ExecutablePath")
                                if os.path.isfile(exe):
                                    candidates.append(exe)
                        except OSError:
                            pass
            except OSError:
                pass
    except ImportError:
        pass

    # 4) common install paths
    local_py = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python")
    home = os.path.expanduser("~")
    patterns = [
        os.path.join(local_py, "Python3*", "python.exe"),
        r"C:\Python3*\python.exe",
        r"C:\Program Files\Python3*\python.exe",
        r"C:\Program Files (x86)\Python3*\python.exe",
        os.path.join(home, "miniconda3", "python.exe"),
        os.path.join(home, "anaconda3", "python.exe"),
        os.path.join(home, "miniconda3", "envs", "*", "python.exe"),
    ]
    for pat in patterns:
        for exe in glob.glob(pat):
            if os.path.isfile(exe):
                candidates.append(exe)

    # deduplicate
    seen = set()
    unique = []
    for exe in candidates:
        key = os.path.normcase(os.path.abspath(exe))
        if key not in seen:
            seen.add(key)
            unique.append(exe)
    return unique


def _get_version(python_exe):
    """Return (major, minor, patch), or (0,0,0) if unknown."""
    r = _run([python_exe, "--version"])
    if not r:
        return (0, 0, 0)

    text = (r.stdout + r.stderr).strip().replace("Python ", "")
    try:
        parts = text.split(".")[:3]
        while len(parts) < 3:
            parts.append("0")
        return tuple(int(x) for x in parts)
    except Exception:
        return (0, 0, 0)


def _has_pip(python_exe):
    r = _run_pip(python_exe, "--version")
    return r is not None and r.returncode == 0


def _fmt_ver(ver):
    return ".".join(str(v) for v in ver)


def _sort_key(item):
    """Sort by preferred version range first, then higher version."""
    ver, _exe = item
    in_preferred = 0 if ver <= MAX_PREFERRED_VERSION else 1
    return (in_preferred, (-ver[0], -ver[1], -ver[2]))


def _fallback_python_selection(message="  No Python found via scan, fallback to command: python"):
    print(message)
    return "python", _has_pip("python")


def _select_ranked_python(candidates, *, pip_ready):
    if not candidates:
        return None
    candidates.sort(key=_sort_key)
    best_ver, best_exe = candidates[0]
    detail = "pip ready" if pip_ready else "pip will be installed"
    print(f"\n  -> Selected Python {_fmt_ver(best_ver)} ({detail})")
    print(f"     Path: {best_exe}")
    return best_exe, pip_ready


def select_best_python():
    _print_stage(1, "扫描可用的 Python 解释器...")

    all_exes = _discover_all_pythons()
    if not all_exes:
        return _fallback_python_selection()

    with_pip = []
    without_pip = []

    for exe in all_exes:
        ver = _get_version(exe)
        if ver < MIN_VERSION:
            print(f"  [skip] Python {_fmt_ver(ver)} below minimum {_fmt_ver(MIN_VERSION)}: {exe}")
            continue

        has_pip = _has_pip(exe)
        status = "pip" if has_pip else "no-pip"
        pref = "preferred" if ver <= MAX_PREFERRED_VERSION else "higher-version"
        print(f"  [{status}] Python {_fmt_ver(ver):<8} {pref:<14} {exe}")
        (with_pip if has_pip else without_pip).append((ver, exe))

    selected = _select_ranked_python(with_pip, pip_ready=True)
    if selected is not None:
        return selected

    selected = _select_ranked_python(without_pip, pip_ready=False)
    if selected is not None:
        return selected

    return _fallback_python_selection("  No executable candidate remained, fallback to command: python")


def ensure_pip(python_exe):
    _print_info("\npip 缺失，尝试自动安装...")

    # A) ensurepip
    r = _run_python_module(python_exe, "ensurepip", "--upgrade", timeout=120)
    if r and r.returncode == 0 and _has_pip(python_exe):
        _print_kind("  已通过 ensurepip 安装 pip", "ok", prefix=False)
        return True

    _print_kind(
        "  ensurepip 失败；为避免自动执行未经固定哈希校验的远程脚本，"
        "安装器不会下载 get-pip.py。请从 python.org 安装包含 pip 的 Python。",
        "error",
        prefix=False,
    )
    return False


def _resolve_pythonw_path(python_exe, fallback="pythonw"):
    """Infer pythonw.exe from selected python path."""
    try:
        p = Path(python_exe)
        if p.is_file():
            if p.name.lower() == "pythonw.exe":
                return str(p)
            pw = p.with_name("pythonw.exe")
            if pw.exists():
                return str(pw)
    except Exception:
        pass
    return fallback


def _to_short_windows_path(path):
    """Convert path to DOS 8.3 short path for batch-file compatibility."""
    if os.name != "nt" or not path:
        return path

    if path.lower() in {"python", "python3", "pythonw", "py"}:
        return path

    target = os.path.abspath(path)
    if not os.path.exists(target):
        return path

    try:
        import ctypes

        buf = ctypes.create_unicode_buffer(4096)
        size = ctypes.windll.kernel32.GetShortPathNameW(target, buf, len(buf))
        if size:
            return buf.value
    except Exception:
        pass

    return path


def _to_env_macro_path(path):
    """Replace common user/system prefixes with %ENV% form to avoid UTF-8 parsing issues in batch."""
    if os.name != "nt" or not path:
        return path

    candidates = [
        "LOCALAPPDATA",
        "APPDATA",
        "USERPROFILE",
        "ProgramFiles",
        "ProgramFiles(x86)",
        "ProgramData",
        "SystemRoot",
    ]

    raw = os.path.abspath(path)
    raw_lower = raw.lower()
    best = None

    for key in candidates:
        val = os.environ.get(key)
        if not val:
            continue
        base = os.path.abspath(val).rstrip("\\/")
        if not base:
            continue
        base_lower = base.lower()
        if raw_lower == base_lower or raw_lower.startswith(base_lower + "\\"):
            if best is None or len(base) > len(best[1]):
                best = (key, base)

    if not best:
        return path

    key, base = best
    suffix = raw[len(base) :]
    suffix = suffix.lstrip("\\/")
    if suffix:
        return f"%{key}%\\{suffix}"
    return f"%{key}%"


def _to_batch_safe_path(path):
    """Prefer ASCII-friendly path when original path contains non-ASCII chars."""
    if not path:
        return path
    if all(ord(ch) < 128 for ch in path):
        return path

    short = _to_short_windows_path(path)
    if all(ord(ch) < 128 for ch in short):
        return short

    macro = _to_env_macro_path(short)
    if all(ord(ch) < 128 for ch in macro):
        return macro

    macro = _to_env_macro_path(path)
    if all(ord(ch) < 128 for ch in macro):
        return macro

    return short


def save_config(python_exe):
    """Write python/pythonw executable paths to py.ini."""
    pythonw_exe = _resolve_pythonw_path(python_exe)
    python_cfg = _to_batch_safe_path(python_exe)
    pythonw_cfg = _to_batch_safe_path(pythonw_exe)
    cfg = configparser.RawConfigParser()
    cfg["Python"] = {
        "python_executable": python_cfg,
        "pythonw_executable": pythonw_cfg,
    }

    config_path = PROJECT_ROOT / "py.ini"
    temp_path = config_path.with_name(f".{config_path.name}.tmp")
    try:
        with temp_path.open("w", encoding="utf-8") as f:
            cfg.write(f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, config_path)
        print("\n[config] py.ini updated:")
        print(f"  python_executable  = {python_cfg}")
        print(f"  pythonw_executable = {pythonw_cfg}")
    except Exception as e:
        print(f"\n[config] failed to write py.ini: {e}")
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def _tcp_ms(host, port=443, timeout=4.0):
    """Return TCP connect latency in milliseconds, or inf if unreachable."""
    try:
        start = time.perf_counter()
        with socket.create_connection((host, port), timeout=timeout):
            pass
        return (time.perf_counter() - start) * 1000
    except Exception:
        return float("inf")


def benchmark_mirrors():
    _print_stage(2, "测试依赖镜像延迟...")
    scored = []

    for mirror in PYPI_MIRRORS:
        lat = _tcp_ms(mirror["host"])
        if lat == float("inf"):
            print(f"  {mirror['name']:<10} unreachable")
        else:
            print(f"  {mirror['name']:<10} {lat:>6.0f} ms")
        scored.append((lat, mirror))

    scored.sort(key=lambda x: x[0])
    reachable = [m for lat, m in scored if lat < float("inf")]
    unreachable = [m for lat, m in scored if lat == float("inf")]

    if reachable:
        best_lat = next(lat for lat, m in scored if m is reachable[0])
        _print_kind(f"\n  -> 最优镜像: {reachable[0]['name']} ({best_lat:.0f} ms)", "ok", prefix=False)
    else:
        _print_warn("\n  -> 所有镜像均不可达，将逐一尝试")

    return reachable + unreachable


def _pkg_installed(python_exe, pkg, import_checks=()):
    """
    Check package availability by:
    1) pip metadata exists
    2) referenced runtime modules can be imported
    """
    r = _run_pip(python_exe, "show", pkg)
    if not (r is not None and r.returncode == 0):
        return False

    modules = [m for m in import_checks if str(m or "").strip()]
    if not modules:
        return True

    code = "; ".join(f"import {m}" for m in modules)
    ir = _run([python_exe, "-c", code])
    return ir is not None and ir.returncode == 0


def _install_one(python_exe, pkg, mirrors):
    """Install one package with mirror fallback."""
    local_spec = LOCAL_DEPENDENCY_WHEELS.get(str(pkg).casefold())
    if local_spec is not None:
        wheel_path = Path(local_spec["path"])
        expected_sha256 = str(local_spec["sha256"]).casefold()
        if not wheel_path.is_file():
            print(f"    local wheel missing: {wheel_path}")
            return False
        actual_sha256 = hashlib.sha256(wheel_path.read_bytes()).hexdigest()
        if actual_sha256 != expected_sha256:
            print(
                "    local wheel checksum mismatch: "
                f"expected={expected_sha256} actual={actual_sha256}"
            )
            return False
        print(f"    [local] {wheel_path.name} ...", end=" ", flush=True)
        result = _run_pip(
            python_exe,
            "install",
            str(wheel_path),
            "--no-deps",
            "--no-warn-script-location",
            timeout=240,
        )
        if result is not None and result.returncode == 0:
            print("ok")
            return True
        print("failed")
        return False

    for i, mirror in enumerate(mirrors):
        label = "primary" if i == 0 else f"backup{i}"
        print(f"    [{label}] {mirror['name']} ...", end=" ", flush=True)

        r = _run_pip(
            python_exe,
            "install",
            pkg,
            "-i",
            mirror["url"],
            "--no-warn-script-location",
            timeout=240,
        )

        if r and r.returncode == 0:
            print("ok")
            return True

        combined = ((r.stderr or "") + (r.stdout or "")).lower() if r else ""
        if any(marker in combined for marker in _NOT_FOUND_MARKERS):
            print("not found on this mirror, switching")
        else:
            print("failed, switching")

    return False


def install_all(python_exe, mirrors):
    _print_stage(3, "检查并安装主程序/元宝依赖...")
    failed = []

    for pkg, desc, import_checks in DEPENDENCIES:
        print(f"\n  - {pkg} ({desc})")
        if _pkg_installed(python_exe, pkg, import_checks=import_checks):
            print("    已安装")
            continue

        print("    缺失，正在安装...")
        if not _install_one(python_exe, pkg, mirrors):
            print(f"    安装失败: {pkg}")
            failed.append(pkg)

    if not failed:
        _print_kind("\n  所有依赖已安装", "ok", prefix=False)
        return True

    _print_warn(f"\n  以下依赖安装失败: {', '.join(failed)}")
    print("  可手动执行以下命令：")
    print("    " + " ".join(_python_module_cmd(python_exe, "pip", "install", *failed)))
    ans = input("\n仍要继续启动吗? (y/n): ").strip().lower()
    return ans == "y"


def _format_bytes(num_bytes):
    size = float(max(0, int(num_bytes or 0)))
    units = ("B", "KB", "MB", "GB")
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)}{unit}"
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}GB"


def _render_transfer_progress(prefix, current, total, start_time):
    elapsed = max(time.perf_counter() - start_time, 1e-6)
    speed = current / elapsed
    speed_text = f"{_format_bytes(speed)}/s"
    current_text = _format_bytes(current)
    if total:
        percent = min(100.0, (current * 100.0) / total)
        total_text = _format_bytes(total)
        bar_width = 24
        filled = max(0, min(bar_width, int(percent / 100.0 * bar_width)))
        bar = "#" * filled + "-" * (bar_width - filled)
        return f"{prefix} [{bar}] {percent:6.2f}% {current_text}/{total_text} {speed_text}"
    return f"{prefix} {current_text} {speed_text}"


def _unlink_if_exists(path, *, ignore_errors=False):
    if not path.exists():
        return
    try:
        path.unlink()
    except Exception:
        if not ignore_errors:
            raise


def _rmtree_if_exists(path, *, ignore_errors=True):
    if path.exists():
        shutil.rmtree(path, ignore_errors=ignore_errors)


def _cleanup_vosk_temp_artifacts(archive_path, part_path, extract_root, *, ignore_errors=False):
    _rmtree_if_exists(extract_root, ignore_errors=ignore_errors)
    _unlink_if_exists(part_path, ignore_errors=ignore_errors)
    _unlink_if_exists(archive_path, ignore_errors=ignore_errors)


def _service_bundle_ready(service_dir: Path, required_files) -> bool:
    if not service_dir.exists() or not service_dir.is_dir():
        return False
    for name in required_files:
        if not (service_dir / name).exists():
            return False
    return True


def _find_bundle_root(extract_root: Path, required_files) -> Optional[Path]:
    candidates = [extract_root]
    candidates.extend(path for path in extract_root.iterdir() if path.is_dir())
    for candidate in candidates:
        if all((candidate / name).exists() for name in required_files):
            return candidate
    for candidate in extract_root.rglob('*'):
        if candidate.is_dir() and all((candidate / name).exists() for name in required_files):
            return candidate
    return None


def _iter_playwright_browser_dirs(root_dir: Path):
    if not root_dir.exists() or not root_dir.is_dir():
        return

    seen = set()
    candidates = [root_dir]
    try:
        candidates.extend(path for path in root_dir.rglob("*") if path.is_dir())
    except Exception:
        pass

    for candidate in candidates:
        name = candidate.name.lower()
        if not any(name.startswith(prefix) for prefix in PLAYWRIGHT_BROWSER_DIR_PREFIXES):
            continue
        for relative in PLAYWRIGHT_BROWSER_EXECUTABLE_RELATIVE_PATHS:
            executable = candidate / relative
            if executable.exists():
                resolved = candidate.resolve()
                if resolved in seen:
                    break
                seen.add(resolved)
                yield candidate
                break


def _find_local_playwright_browser_dir() -> Optional[Path]:
    search_roots = [PLAYWRIGHT_RESOURCE_BROWSERS_DIR, PLAYWRIGHT_RESOURCE_ROOT]
    for root in search_roots:
        for candidate in _iter_playwright_browser_dirs(root):
            return candidate
    return None


def _find_local_playwright_browser_archive() -> Optional[Path]:
    for base_dir in PLAYWRIGHT_BROWSER_ARCHIVE_DIRS:
        if not base_dir.exists() or not base_dir.is_dir():
            continue
        for pattern in PLAYWRIGHT_BROWSER_ARCHIVE_PATTERNS:
            for archive_path in sorted(base_dir.glob(pattern)):
                if archive_path.is_file():
                    return archive_path
    return None


def _install_playwright_browser_from_local_archive() -> bool:
    archive_path = _find_local_playwright_browser_archive()
    if archive_path is None:
        return False

    temp_root = Path(os.environ.get("TEMP", "C:\\Temp")) / "fsv_playwright_browser"
    extract_root = temp_root / "extract"
    _rmtree_if_exists(temp_root, ignore_errors=True)
    temp_root.mkdir(parents=True, exist_ok=True)
    try:
        print(f"  发现本地 Chromium 资源包: {archive_path.relative_to(PROJECT_ROOT)}")
        extract_root.mkdir(parents=True, exist_ok=True)
        _extract_zip_with_progress(archive_path, extract_root)
        browser_dir = None
        for candidate in _iter_playwright_browser_dirs(extract_root):
            browser_dir = candidate
            break
        if browser_dir is None:
            raise FileNotFoundError("压缩包中未找到 Chromium 浏览器目录")

        target_dir = PLAYWRIGHT_RESOURCE_BROWSERS_DIR / browser_dir.name
        _rmtree_if_exists(target_dir, ignore_errors=True)
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(browser_dir), str(target_dir))
        print(f"  已安装本地 Chromium 资源: {target_dir.relative_to(PROJECT_ROOT)}")
        return True
    except Exception as exc:
        _print_warn(f"  本地 Chromium 资源包安装失败: {exc}")
        return False
    finally:
        _rmtree_if_exists(temp_root, ignore_errors=True)


def _download_yuanbao_service_bundle() -> bool:
    if _service_bundle_ready(YUANBAO_SERVICE_DIR, YUANBAO_SERVICE_REQUIRED_FILES):
        print(f"  已存在服务目录: {YUANBAO_SERVICE_DIR}")
        return True
    _print_warn(
        "  发行包缺少 services/yuanbao-free-api；为避免下载未经固定与校验的"
        "浮动源码，安装器不会在线补取。请重新获取完整的爱弥斯发行包。"
    )
    return False


def _ensure_playwright_browser(python_exe) -> bool:
    local_browser_dir = _find_local_playwright_browser_dir()
    if local_browser_dir is not None:
        print(f"  使用 resc 内置 Chromium 资源: {local_browser_dir.relative_to(PROJECT_ROOT)}")
        return True

    if _install_playwright_browser_from_local_archive():
        return True

    print(f"  在线安装 Playwright 浏览器运行时 ({YUANBAO_SERVICE_BROWSER}) ...", end=" ", flush=True)
    r = _run_python_module(python_exe, "playwright", "install", YUANBAO_SERVICE_BROWSER, timeout=1200)
    if r and r.returncode == 0:
        print("ok")
        return True
    print("failed")
    return False


def ensure_yuanbao_service_bundle(python_exe) -> bool:
    _print_stage(5, "准备 YuanBao-Free-API 本地中转服务...")
    bundle_ok = _download_yuanbao_service_bundle()
    if not bundle_ok:
        return False

    browser_ok = _ensure_playwright_browser(python_exe)
    if not browser_ok:
        _print_warn("  Playwright Chromium 安装失败，自动抓取登录态功能可能不可用")

    return bundle_ok


def _stream_download_with_progress(
    url,
    dest_path,
    *,
    label,
    timeout=30,
    chunk_size=256 * 1024,
    use_env_proxy=True,
    expected_size=0,
    max_bytes=_MAX_DOWNLOAD_BYTES,
):
    parsed_url = urlparse(str(url or ""))
    if parsed_url.scheme != "https" or not parsed_url.hostname:
        raise OSError("download URL must use HTTPS")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    _unlink_if_exists(dest_path)

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AemeathDeskPetInstaller/1.0",
            "Accept": "application/zip, application/octet-stream, */*",
        },
    )
    proxy_text = "env-proxy" if use_env_proxy else "direct"
    print(f"    source: {label} ({proxy_text})")

    start_time = time.perf_counter()
    last_draw = 0.0
    opener = urllib.request.build_opener() if use_env_proxy else urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response, open(dest_path, "wb") as fp:
        final_url = urlparse(str(response.geturl() or ""))
        if final_url.scheme != "https" or not final_url.hostname:
            raise OSError("download redirected to a non-HTTPS URL")
        total_header = response.headers.get("Content-Length")
        total = int(total_header) if total_header and total_header.isdigit() else 0
        if total > max_bytes:
            raise OSError("download exceeds size limit")
        current = 0
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            current += len(chunk)
            if current > max_bytes:
                raise OSError("download exceeds size limit")
            fp.write(chunk)
            now = time.perf_counter()
            if now - last_draw >= 0.12:
                sys.stdout.write("\r" + _render_transfer_progress("    downloading", current, total, start_time))
                sys.stdout.flush()
                last_draw = now

        sys.stdout.write("\r" + _render_transfer_progress("    downloading", current, total, start_time) + "\n")
        sys.stdout.flush()

    final_size = dest_path.stat().st_size if dest_path.exists() else 0
    if total and final_size != total:
        raise IOError(f"download incomplete: {final_size}/{total} bytes")
    if expected_size and final_size != expected_size:
        raise IOError(
            f"download size mismatch: {final_size}/{expected_size} bytes"
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_archive_member_path(name: str) -> Path:
    posix = PurePosixPath(str(name).replace("\\", "/"))
    unsafe = posix.is_absolute() or not posix.parts
    for part in posix.parts:
        stem = part.split(".", 1)[0].casefold()
        if (
            part in ("", ".", "..")
            or ":" in part
            or part != part.rstrip(" .")
            or any(ord(char) < 32 for char in part)
            or stem in _WINDOWS_DEVICE_NAMES
        ):
            unsafe = True
            break
    if unsafe:
        raise OSError(f"archive contains unsafe path: {name}")
    return Path(*posix.parts)


def _extract_zip_with_progress(zip_path, extract_root):
    _rmtree_if_exists(extract_root)
    extract_root.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.infolist()
        if len(members) > _MAX_ARCHIVE_ENTRIES:
            raise OSError("archive entry count exceeds safety limit")
        total = 0
        seen_paths: set[str] = set()
        validated: list[tuple[zipfile.ZipInfo, Path]] = []
        for item in members:
            relative = _safe_archive_member_path(item.filename)
            path_key = relative.as_posix().casefold()
            if path_key in seen_paths:
                raise OSError(
                    f"archive contains duplicate path: {item.filename}"
                )
            seen_paths.add(path_key)
            unix_mode = (item.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(unix_mode):
                raise OSError(f"archive contains symlink: {item.filename}")
            if item.flag_bits & 0x1:
                raise OSError(f"archive contains encrypted entry: {item.filename}")
            file_size = max(0, int(item.file_size))
            compressed_size = max(0, int(item.compress_size))
            if file_size > _MAX_SINGLE_FILE_BYTES:
                raise OSError(f"archive file exceeds safety limit: {item.filename}")
            if file_size and (
                compressed_size == 0
                or file_size > compressed_size * _MAX_COMPRESSION_RATIO
            ):
                raise OSError(f"archive compression ratio is unsafe: {item.filename}")
            if not item.is_dir():
                total += file_size
                if total > _MAX_EXTRACTED_BYTES:
                    raise OSError("archive extracted size exceeds safety limit")
            validated.append((item, relative))
        current = 0
        start_time = time.perf_counter()
        last_draw = 0.0

        for item, relative in validated:
            target = extract_root / relative
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                extracted = 0
                with zf.open(item, "r") as source, target.open("wb") as output:
                    while True:
                        chunk = source.read(1024 * 1024)
                        if not chunk:
                            break
                        extracted += len(chunk)
                        if extracted > item.file_size:
                            raise OSError(
                                f"archive entry exceeds declared size: {item.filename}"
                            )
                        output.write(chunk)
                if extracted != item.file_size:
                    raise OSError(
                        f"archive entry size mismatch: {item.filename}"
                    )
                current += extracted
            now = time.perf_counter()
            if now - last_draw >= 0.12:
                sys.stdout.write("\r" + _render_transfer_progress("    extracting ", current, total, start_time))
                sys.stdout.flush()
                last_draw = now

        sys.stdout.write("\r" + _render_transfer_progress("    extracting ", current, total, start_time) + "\n")
        sys.stdout.flush()


def _resolve_vosk_model_source_dir(extract_root):
    if all((extract_root / marker).exists() for marker in ("am", "conf")):
        return extract_root

    children = [item for item in extract_root.iterdir() if item.is_dir()]
    for child in children:
        if all((child / marker).exists() for marker in ("am", "conf")):
            return child

    if len(children) == 1:
        return children[0]

    raise FileNotFoundError("extracted model folder not found")


def _microphone_runtime_ready(python_exe):
    return (
        _pkg_installed(python_exe, "sounddevice", import_checks=("sounddevice",))
        and _pkg_installed(python_exe, "vosk", import_checks=("vosk",))
    )


def _ensure_single_vosk_model(spec: dict) -> bool:
    label = spec.get("label") or spec["name"]
    target_dir = VOSK_MODELS_DIR / spec["name"]
    rel_target = target_dir.relative_to(PROJECT_ROOT)

    if all((target_dir / marker).exists() for marker in VOSK_MODEL_MARKERS):
        print(f"  model already installed ({label}): {rel_target}")
        return True

    archive_path = VOSK_MODELS_DIR / f"{spec['name']}.zip"
    part_path = VOSK_MODELS_DIR / f"{spec['name']}.zip.part"
    extract_root = VOSK_MODELS_DIR / f"_{spec['name']}_extract"
    VOSK_MODELS_DIR.mkdir(parents=True, exist_ok=True)

    for leftover in VOSK_MODELS_DIR.glob("BIT*.tmp"):
        _unlink_if_exists(leftover, ignore_errors=True)

    for source in spec["urls"]:
        print(f"  - {spec['name']} ({label}, {source['name']})")
        try:
            _cleanup_vosk_temp_artifacts(archive_path, part_path, extract_root)
            _stream_download_with_progress(
                source["url"],
                part_path,
                label=source["name"],
                expected_size=int(spec.get("size") or 0),
            )
            actual_sha256 = _sha256_file(part_path)
            expected_sha256 = str(spec.get("sha256") or "").casefold()
            if not expected_sha256 or actual_sha256.casefold() != expected_sha256:
                raise OSError("downloaded model SHA256 mismatch")
            part_path.replace(archive_path)
            _extract_zip_with_progress(archive_path, extract_root)
            source_dir = _resolve_vosk_model_source_dir(extract_root)

            _rmtree_if_exists(target_dir)
            shutil.move(str(source_dir), str(target_dir))
            print(f"    model installed: {rel_target}")
            return True
        except (urllib.error.URLError, OSError, zipfile.BadZipFile, FileNotFoundError) as e:
            print(f"    failed: {e}")
        finally:
            _cleanup_vosk_temp_artifacts(archive_path, part_path, extract_root, ignore_errors=True)

    print(f"  warning: {label} model auto download failed")
    print("  manual download:")
    for source in spec["urls"]:
        print(f"    {source['url']}")
    print(f"  extract target: {rel_target}")
    return False


def ensure_vosk_models():
    _print_stage(4, "准备 Vosk 语音模型...")
    all_ok = True
    for spec in VOSK_MODEL_SPECS:
        if not _ensure_single_vosk_model(spec):
            all_ok = False
    return all_ok


def launch(python_exe):
    """Launch main script, prefer pythonw if available."""
    _print_stage(6, "启动爱弥斯桌面助手...")

    main_script = PROJECT_ROOT / "lib" / "core" / "qt_desktop_pet.py"
    if not main_script.exists():
        print(f"  main script not found: {main_script}")
        return False

    launcher = _resolve_pythonw_path(python_exe, fallback=python_exe)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        subprocess.Popen(
            [launcher, str(main_script)],
            cwd=str(PROJECT_ROOT),
            env=env,
            creationflags=create_no_window,
        )
        print("  launched in background")
        return True
    except Exception as e:
        print(f"  launch failed: {e}")
        return False


def main():
    _root = str(PROJECT_ROOT.resolve())
    if _root not in sys.path:
        sys.path.insert(0, _root)
    try:
        from app_brand import APP_DISPLAY_NAME, APP_TAGLINE
    except Exception:
        APP_DISPLAY_NAME, APP_TAGLINE = ("爱弥斯", "学术桌面助手")

    print("=" * 56)
    print(f" {APP_DISPLAY_NAME} · {APP_TAGLINE} — 安装与启动")
    print("=" * 56)
    print()

    try:
        python_exe, pip_ok = select_best_python()

        if not pip_ok:
            if not ensure_pip(python_exe):
                input(_fmt_color("\n[错误] 无法自动安装 pip，按回车退出...", "error"))
                sys.exit(1)

        save_config(python_exe)

        mirrors = benchmark_mirrors()

        if not install_all(python_exe, mirrors):
            _print_warn("依赖未全部安装，可能影响部分功能")

        if _microphone_runtime_ready(python_exe):
            if not ensure_vosk_models():
                _print_warn("部分 Vosk 模型缺失，语音识别可能无法正常工作")
        else:
            _print_stage(4, "跳过 Vosk 模型下载（sounddevice/vosk 未就绪）")

        if not ensure_yuanbao_service_bundle(python_exe):
            _print_warn("YuanBao-Free-API 本地中转未准备完成，元宝 web 模式可能不可用")

        if "--no-launch" in sys.argv[1:]:
            print("\n[--no-launch] 已跳过自动启动主程序。按回车退出...")
            input()
            return

        if launch(python_exe):
            print("\nLauncher will close in 3 seconds...")
            time.sleep(3)
        else:
            input("\nPress Enter to exit...")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n[cancelled] interrupted by user")
    except Exception as e:
        _print_error(f"\n发生未预期异常: {e}")
        import traceback

        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
