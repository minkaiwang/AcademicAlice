"""桌面宠物主程序 (PyQt5版)"""
import os
import sys
import traceback

# 开发：仓库根（lib 的上一级）；冻结：必须与 _MEIPASS 一致，勿用 dirname 链（否则会落到 dist 等错误路径并抢占 sys.path，导致 PyQt5 等从包内加载失败）
if getattr(sys, 'frozen', False):
    project_root = getattr(sys, '_MEIPASS', None) or os.path.dirname(os.path.abspath(sys.executable))
else:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root and project_root not in sys.path:
    sys.path.insert(0, project_root)


def _startup_error_title() -> str:
    try:
        from app_brand import APP_DISPLAY_NAME

        return f"{APP_DISPLAY_NAME} 启动失败"
    except Exception:
        return "爱弥斯 启动失败"


def _show_startup_error(message: str) -> None:
    """输出启动错误，并在 Windows 下弹窗提示。"""
    try:
        print(message, file=sys.stderr)
    except Exception:
        pass

    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, _startup_error_title(), 0x10)
    except Exception:
        pass


def _build_missing_dependency_message(missing_module: str, install_bat: str) -> str:
    return (
        f"缺少 Python 依赖模块：{missing_module}\n\n"
        f"请先运行：{install_bat}\n"
        "然后重新启动程序。\n\n"
        f"也可手动执行：python -m pip install {missing_module}"
    )


def _prepare_yuanbao_service_output():
    """为无控制台的冻结服务恢复可写日志流。

    PyInstaller 的 windowed 模式会把 ``sys.stdout`` / ``sys.stderr`` 设为
    ``None``。Uvicorn 在配置日志处理器时需要真实流；若不恢复，后台子进程
    会在开始监听前失败，且错误只能落入不可见的弹窗。
    """
    configured = str(
        os.environ.get("AEMEATH_YUANBAO_BOOT_LOG", "") or ""
    ).strip()
    if configured:
        candidates = [os.path.abspath(os.path.expanduser(configured))]
    else:
        local_app_data = str(os.environ.get("LOCALAPPDATA", "") or "").strip()
        temp_dir = str(os.environ.get("TEMP", "") or "").strip()
        candidates = []
        if local_app_data:
            candidates.append(
                os.path.join(
                    local_app_data,
                    "AemeathDeskPet",
                    "yuanbao_free_api",
                    "launcher.log",
                )
            )
        if temp_dir:
            candidates.append(
                os.path.join(temp_dir, "AemeathDeskPet-yuanbao-service.log")
            )

    for log_path in candidates:
        try:
            parent = os.path.dirname(log_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            stream = open(
                log_path,
                "a",
                encoding="utf-8",
                errors="backslashreplace",
                buffering=1,
            )
            sys.stdout = stream
            sys.stderr = stream
            print("\n===== YuanBao local service boot =====", flush=True)
            return stream
        except (OSError, ValueError):
            continue

    # 最后的降级也必须提供文件对象，避免 Uvicorn 因 None 流二次失败。
    stream = open(os.devnull, "w", encoding="utf-8")
    sys.stdout = stream
    sys.stderr = stream
    return stream


if __name__ == '__main__':
    # 尽早脱离控制台，减轻用 python.exe / IDE 启动时闪出黑色 CMD 窗口。
    try:
        from lib.script.app.win_console import detach_process_console_if_unneeded

        detach_process_console_if_unneeded()
    except Exception:
        pass

    # PyInstaller：启动/退出动画子进程复用同一 exe，不得进入 main()（否则会抢单实例锁并反复弹「已在运行」）。
    if (
        len(sys.argv) >= 3
        and sys.argv[1] == '--deskpet-animation-player'
        and sys.argv[2] in ('start', 'exit')
    ):
        animation_type = sys.argv[2]
        sys.argv = [sys.argv[0], animation_type]
        _bundle_root = getattr(sys, '_MEIPASS', None)
        if not _bundle_root:
            _bundle_root = project_root
        if _bundle_root not in sys.path:
            sys.path.insert(0, _bundle_root)
        try:
            from lib.script.SEanima.animation_player import main as _animation_player_main

            _animation_player_main()
        except SystemExit:
            raise
        except Exception:
            _show_startup_error('动画子进程启动失败：\n\n' + traceback.format_exc())
            sys.exit(1)

    # 冻结版使用同一可执行文件承载本机 YuanBao-Free-API 子进程。
    if len(sys.argv) == 3 and sys.argv[1] == '--yuanbao-service':
        _service_output = _prepare_yuanbao_service_output()
        try:
            port = int(sys.argv[2])
            if not 1 <= port <= 65535:
                raise ValueError("port out of range")
            service_dir = os.path.join(
                project_root,
                'services',
                'yuanbao-free-api',
            )
            entry_path = os.path.join(service_dir, 'app.py')
            if not os.path.isfile(entry_path):
                raise FileNotFoundError(entry_path)
            if service_dir not in sys.path:
                sys.path.insert(0, service_dir)
            os.chdir(service_dir)
            import importlib
            import uvicorn

            service_module = importlib.import_module('app')
            uvicorn.run(
                service_module.app,
                host='127.0.0.1',
                port=port,
                reload=False,
                access_log=False,
            )
            sys.exit(0)
        except SystemExit:
            raise
        except Exception:
            print(
                '元宝本机服务子进程启动失败：\n\n' + traceback.format_exc(),
                file=sys.stderr,
                flush=True,
            )
            sys.exit(1)

    try:
        from lib.script.main import main
    except ModuleNotFoundError as e:
        missing = getattr(e, "name", None) or "unknown"
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            msg = (
                f"缺少运行库模块：{missing}\n\n"
                "【使用方式】请解压整个 AemeathDeskPet 文件夹后再运行其中的 AemeathDeskPet.exe，"
                "不要只复制单个 exe 到别处；好友电脑无需安装 Python。\n\n"
                "【若仍缺模块】多为打包环境未完整收集 Qt。请用已安装 PyQt5 的 Python 3.11–3.13 "
                "在仓库根目录重新执行打包；不推荐用 3.14 等过新版本打正式包。\n\n"
                f"（开发机可选）在含 Python 的环境执行：python -m pip install {missing}\n"
                f"仓库依赖脚本：{os.path.join(exe_dir, '安装依赖.bat')}（若已随包复制）"
            )
        else:
            install_bat = os.path.join(project_root, "安装依赖.bat")
            msg = _build_missing_dependency_message(missing, install_bat)
        _show_startup_error(msg)
        sys.exit(1)
    except Exception:
        _show_startup_error("程序启动失败：\n\n" + traceback.format_exc())
        sys.exit(1)

    main()
