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
        return "学术爱丽丝 启动失败"


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

    try:
        from lib.script.main import main
    except ModuleNotFoundError as e:
        missing = getattr(e, "name", None) or "unknown"
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            msg = (
                f"缺少运行库模块：{missing}\n\n"
                "【使用方式】请解压整个 AcademicAlice 文件夹后再运行其中的 AcademicAlice.exe，"
                "不要只复制单个 exe 到别处；好友电脑无需安装 Python。\n\n"
                "【若仍缺模块】多为打包环境未完整收集 Qt。请用已安装 PyQt5 的 Python 3.11 或 3.12 "
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
