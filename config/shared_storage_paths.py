"""Shared config storage path helpers."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

PENDING_SYNC_SUFFIX = '.pending'
LOCAL_PENDING_DIRNAME = '.shared_pending'


def get_project_root() -> Path:
    """源码树为仓库根；PyInstaller 打包后为 `sys._MEIPASS`（内含 resc、config 等）。"""
    if getattr(sys, "frozen", False):
        mei = getattr(sys, "_MEIPASS", None)
        if mei:
            return Path(mei)
    return Path(__file__).resolve().parents[1]


def get_project_config_dir() -> Path:
    return get_project_root() / 'config'


def get_project_config_path(*parts: str) -> Path:
    return get_project_config_dir().joinpath(*parts)


def _legacy_drive_root() -> Path:
    """旧版共享目录；仅在已存在时沿用，避免普通用户首次写系统盘根目录。"""
    drive = str(os.environ.get('SystemDrive', 'C:') or 'C:').strip()
    if not drive:
        drive = 'C:'
    drive = drive.rstrip('\\/')
    if not drive.endswith(':'):
        drive = f'{drive}:'
    return Path(f'{drive}\\AemeathDeskPet')


def _user_data_root() -> Path:
    local_app_data = str(os.environ.get('LOCALAPPDATA', '') or '').strip()
    if local_app_data:
        return Path(local_app_data).expanduser() / 'AemeathDeskPet'
    user_profile = str(os.environ.get('USERPROFILE', '') or '').strip()
    if user_profile:
        return Path(user_profile).expanduser() / 'AppData' / 'Local' / 'AemeathDeskPet'
    return Path.home() / 'AppData' / 'Local' / 'AemeathDeskPet'


@lru_cache(maxsize=1)
def get_shared_root_dir() -> Path:
    override = str(os.environ.get('AEMEATH_SHARED_ROOT', '') or '').strip()
    if override:
        return Path(override).expanduser().resolve()
    legacy_root = _legacy_drive_root()
    if legacy_root.exists():
        return legacy_root
    return _user_data_root()


def get_shared_config_dir() -> Path:
    return get_shared_root_dir() / 'config'


def resolve_shared_config_path(*parts: str) -> Path:
    base = get_shared_config_dir().resolve()
    candidate = base.joinpath(*parts).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as e:
        raise ValueError(f'共享配置路径越界: {candidate}') from e
    return candidate


def get_shared_config_path(*parts: str) -> Path:
    return resolve_shared_config_path(*parts)


def is_ignored(path: Path) -> bool:
    name = path.name.lower()
    return (
        name == '__pycache__'
        or name.endswith('.pyc')
        or name.endswith('.pyo')
        or name.endswith(PENDING_SYNC_SUFFIX)
    )


def pending_sync_path(path: Path) -> Path:
    return path.with_name(f'{path.name}{PENDING_SYNC_SUFFIX}')


def local_pending_root() -> Path:
    return get_project_config_dir() / LOCAL_PENDING_DIRNAME


def local_pending_sync_path(path: Path) -> Path:
    shared_base = get_shared_config_dir()
    try:
        rel = path.relative_to(shared_base)
    except ValueError:
        rel = Path(path.name)
    return local_pending_root().joinpath(*rel.parts[:-1], f'{rel.name}{PENDING_SYNC_SUFFIX}')
