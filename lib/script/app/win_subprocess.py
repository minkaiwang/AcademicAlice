"""Windows 下子进程尽量不弹出控制台窗口。"""

from __future__ import annotations

import os
import subprocess
from typing import Any


def merge_create_no_window(creationflags: int = 0) -> int:
    if os.name != "nt":
        return int(creationflags)
    return int(creationflags) | int(getattr(subprocess, "CREATE_NO_WINDOW", 0))


def run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
    """等同 subprocess.run，在 Windows 上默认附加 CREATE_NO_WINDOW。"""
    cf = merge_create_no_window(int(kwargs.pop("creationflags", 0)))
    kwargs["creationflags"] = cf
    return subprocess.run(*args, **kwargs)


def popen(*args: Any, **kwargs: Any) -> subprocess.Popen:
    """等同 subprocess.Popen，在 Windows 上默认附加 CREATE_NO_WINDOW。"""
    cf = merge_create_no_window(int(kwargs.pop("creationflags", 0)))
    kwargs["creationflags"] = cf
    return subprocess.Popen(*args, **kwargs)
