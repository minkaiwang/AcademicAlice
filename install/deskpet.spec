# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 规格：Windows 下生成可分发目录（onedir）。

用法（在仓库根目录执行）：
  pip install pyinstaller==6.21.0
  pyinstaller --noconfirm install/deskpet.spec
  或双击 **install/打包Windows.bat**（根目录 **打包Windows.bat** 会转调）。

产物：`dist/AemeathDeskPet/AemeathDeskPet.exe`（将整个 `AemeathDeskPet` 文件夹打包 zip 给好友即可）。
"""
from __future__ import annotations

import sys
from pathlib import Path

def _find_project_root() -> Path:
    candidates: list[Path] = []
    sp = globals().get("SPECPATH")
    if sp:
        candidates.append(Path(sp).resolve().parent)
    candidates.append(Path.cwd().resolve())
    try:
        here = Path(__file__).resolve().parent
        candidates.append(here)
    except NameError:
        pass
    for base in candidates:
        cur = base
        for _ in range(8):
            marker = cur / "lib" / "core" / "qt_desktop_pet.py"
            if marker.is_file():
                return cur.resolve()
            if cur.parent == cur:
                break
            cur = cur.parent
    raise RuntimeError("deskpet.spec：无法定位项目根（缺少 lib/core/qt_desktop_pet.py）")


ROOT = _find_project_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_build_environment import (  # noqa: E402
    format_missing_modules,
    missing_build_modules,
)

_missing_build_modules = missing_build_modules()
if _missing_build_modules:
    raise RuntimeError(format_missing_modules(_missing_build_modules))

# 显式收集 PyQt5（含 Qt5/plugins/platforms 等）；仅靠「跟随主脚本」在部分 Python 版本（如 3.14）下可能收集不全。
try:
    from PyInstaller.utils.hooks import collect_all, collect_submodules

    _pyqt5_datas, _pyqt5_binaries, _pyqt5_hiddenimports = collect_all("PyQt5")
    # yuanbao-free-api 的源码以 data 文件形式随包加载，PyInstaller 无法从主
    # 入口静态看到它对 playwright.async_api 的导入，因此显式收集全部
    # Playwright Python 子模块（浏览器二进制仍按独立资源策略处理）。
    _playwright_hiddenimports = collect_submodules("playwright")
    # PyQt5 5.15.x 的 uic.port_v2 是 Python 2 兼容残留，部分模块引用了仅
    # Python 2 存在的符号。collect_all 会把它们误当运行期隐藏导入并输出
    # ERROR；桌宠只使用 Python 3 的 PyQt5.uic 路径。
    _pyqt5_hiddenimports = [
        module
        for module in _pyqt5_hiddenimports
        if not module.startswith("PyQt5.uic.port_v2.")
    ]
except Exception as exc:
    raise RuntimeError(
        "deskpet.spec：无法 collect_all('PyQt5')，请确认当前解释器已 pip install PyQt5；"
        "若使用 Python 3.14 仍失败，请改用 3.11–3.13 打包。"
    ) from exc


def _obj_hiddenimports() -> list[str]:
    out: list[str] = []
    script = ROOT / "lib" / "script"
    for mp in sorted(script.glob("obj-*/manager.py")):
        pkg = mp.parent.name
        out.append(f"lib.script.{pkg}.manager")
    prac = script / "practical"
    if prac.is_dir():
        for pp in sorted(prac.glob("*_particle.py")):
            out.append(f"lib.script.practical.{pp.stem}")
    return out


def _filtered_data_tree(
    source: Path,
    destination: Path,
    *,
    excluded_roots: tuple[Path, ...] = (),
) -> list[tuple[str, str]]:
    excluded_names = {
        ".env",
        "qrcode.png",
        "storage_state.json",
    }
    excluded_suffixes = {
        ".bak",
        ".log",
        ".pyc",
        ".pyo",
        ".tmp",
    }
    data_files: list[tuple[str, str]] = []
    for file_path in sorted(source.rglob("*")):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(source)
        if any(
            relative.parts[: len(root.parts)] == root.parts
            for root in excluded_roots
        ):
            continue
        if "__pycache__" in relative.parts:
            continue
        lower_name = file_path.name.casefold()
        if (
            lower_name in excluded_names
            or (
                lower_name.startswith("storage_state")
                and file_path.suffix.casefold() == ".json"
            )
            or (
                lower_name.startswith("qrcode")
                and file_path.suffix.casefold() == ".png"
            )
            or file_path.suffix.casefold() in excluded_suffixes
        ):
            continue
        target_dir = destination / relative.parent
        data_files.append((str(file_path), str(target_dir)))
    return data_files


_datas = [
    (str(ROOT / "app_brand.py"), "."),
    (str(ROOT / "ACKNOWLEDGMENTS.md"), "."),
    (str(ROOT / "LICENSE-ASSETS"), "."),
    (str(ROOT / "LICENSE-CODE"), "."),
    (str(ROOT / "THIRD_PARTY_NOTICES.md"), "."),
] + list(_pyqt5_datas)
_datas += _filtered_data_tree(
    ROOT / "resc",
    Path("resc"),
    excluded_roots=(
        Path("user"),
        Path("gsvmove_update"),
        Path("VFX") / "cache",
    ),
)
_datas += _filtered_data_tree(
    ROOT / "config",
    Path("config"),
    excluded_roots=(Path(".shared_pending"),),
)
_datas += _filtered_data_tree(
    ROOT / "services" / "yuanbao-free-api",
    Path("services") / "yuanbao-free-api",
)

_binaries: list = list(_pyqt5_binaries)
_hiddenimports = (
    _obj_hiddenimports()
    + list(_pyqt5_hiddenimports)
    + list(_playwright_hiddenimports)
    + [
    "lib.script.SEanima.animation_player",
    "lib.script.main",
    "lib.script.chat.handler",
    "lib.script.chat.memory",
    "lib.script.tool_dispatcher.dispatcher",
    "PIL.Image",
    "numpy",
    "cv2",
    "pygame",
    "comtypes",
    "pycaw",
    "sounddevice",
    "vosk",
    "fastapi",
    "uvicorn",
    "httpx",
    "pydantic",
    "pydantic_settings",
    "sse_starlette",
    "playwright",
    "openai",
    "requests",
    "qrcode",
    ]
)

a = Analysis(
    [str(ROOT / "lib" / "core" / "qt_desktop_pet.py")],
    pathex=[str(ROOT)],
    binaries=_binaries,
    datas=_datas,
    hiddenimports=_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AemeathDeskPet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AemeathDeskPet",
)
