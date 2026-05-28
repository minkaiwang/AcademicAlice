# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 规格：Windows 下生成可分发目录（onedir）。

用法（在仓库根目录执行）：
  pip install pyinstaller
  pyinstaller --noconfirm install/deskpet.spec
  或双击 **install/打包Windows.bat**（根目录 **打包Windows.bat** 会转调）。

产物：`dist/AemeathDeskPet/AemeathDeskPet.exe`（将整个 `AemeathDeskPet` 文件夹打包 zip 给好友即可）。
"""
from __future__ import annotations

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

# 显式收集 PyQt5（含 Qt5/plugins/platforms 等）；仅靠「跟随主脚本」在部分 Python 版本（如 3.14）下可能收集不全。
try:
    from PyInstaller.utils.hooks import collect_all

    _pyqt5_datas, _pyqt5_binaries, _pyqt5_hiddenimports = collect_all("PyQt5")
except Exception as exc:
    raise RuntimeError(
        "deskpet.spec：无法 collect_all('PyQt5')，请确认当前解释器已 pip install PyQt5；"
        "若使用 Python 3.14 仍失败，请改用 3.11–3.12 打包。"
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


_datas = [
    (str(ROOT / "resc"), "resc"),
    (str(ROOT / "config"), "config"),
    (str(ROOT / "app_brand.py"), "."),
] + list(_pyqt5_datas)

_binaries: list = list(_pyqt5_binaries)
_hiddenimports = _obj_hiddenimports() + list(_pyqt5_hiddenimports) + [
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
