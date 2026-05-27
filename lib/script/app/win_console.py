"""Windows 控制台：GUI 进程可主动脱离，避免常驻黑色 CMD 窗口。"""

from __future__ import annotations

import os
import sys


def detach_process_console_if_unneeded() -> None:
    """
    若当前进程仍附着控制台（例如用 python.exe 双击/脚本启动），则脱离之。
    调试时设置环境变量 DESKPET_KEEP_CONSOLE=1 可保留控制台。
    """
    if os.name != "nt":
        return
    if getattr(sys, "frozen", False):
        return
    env = os.environ.get("DESKPET_KEEP_CONSOLE", "").strip().lower()
    if env in ("1", "true", "yes", "debug"):
        return
    try:
        import ctypes

        user32 = ctypes.windll.user32
        k32 = ctypes.windll.kernel32
        hwnd = k32.GetConsoleWindow()
        if not hwnd:
            return
        # 先隐藏窗口再脱离，可消除「闪一下」的黑框（仍建议用 pythonw 启动以从根源去掉控制台）。
        SW_HIDE = 0
        user32.ShowWindow(hwnd, SW_HIDE)
        k32.FreeConsole()
    except Exception:
        pass
