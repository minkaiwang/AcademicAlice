#!/usr/bin/env python3
"""Fail fast when a release build environment lacks bundled runtime modules."""

from __future__ import annotations

import importlib.util
import sys

REQUIRED_BUILD_MODULES: tuple[tuple[str, str], ...] = (
    ("PyInstaller", "pyinstaller"),
    ("PyQt5.QtWidgets", "PyQt5"),
    ("PIL.Image", "Pillow"),
    ("numpy", "numpy"),
    ("cv2", "opencv-python"),
    ("pygame", "pygame"),
    ("comtypes", "comtypes"),
    ("pycaw", "pycaw"),
    ("sounddevice", "sounddevice"),
    ("vosk", "vosk"),
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("httpx", "httpx"),
    ("pydantic", "pydantic"),
    ("pydantic_settings", "pydantic-settings"),
    ("sse_starlette", "sse-starlette"),
    ("playwright", "playwright"),
    ("openai", "openai"),
    ("requests", "requests"),
    ("qrcode", "qrcode"),
    ("mutagen", "mutagen"),
    ("pyncm", "pyncm"),
    ("win32com.client", "pywin32"),
)


def missing_build_modules() -> list[tuple[str, str]]:
    missing: list[tuple[str, str]] = []
    for module_name, distribution_name in REQUIRED_BUILD_MODULES:
        try:
            available = importlib.util.find_spec(module_name) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            available = False
        if not available:
            missing.append((module_name, distribution_name))
    return missing


def format_missing_modules(missing: list[tuple[str, str]]) -> str:
    details = ", ".join(f"{module} ({distribution})" for module, distribution in missing)
    return (
        "构建环境缺少发行包必需模块："
        f"{details}。请先运行当前解释器的 "
        "`python -m pip install -r install/requirements.txt -r requirements-dev.txt`。"
    )


def main() -> int:
    missing = missing_build_modules()
    if missing:
        print(f"[build-env] error: {format_missing_modules(missing)}", file=sys.stderr)
        return 2
    print(f"[build-env] OK: {len(REQUIRED_BUILD_MODULES)} 个发行模块均可发现")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
