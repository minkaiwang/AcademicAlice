"""学术数据本地路径（SQLite 等），与 `PROGRESS.md` 决策 D2 一致。"""

from __future__ import annotations

from pathlib import Path

from config.shared_storage_paths import get_shared_root_dir

_ACADEMIC_DIRNAME = "academic"
_DB_FILENAME = "deskpet_academic.db"


def get_academic_data_dir() -> Path:
    """`{共享根}/academic/`，与桌宠配置同盘策略一致。"""
    p = get_shared_root_dir() / _ACADEMIC_DIRNAME
    return p


def get_academic_db_path() -> Path:
    return get_academic_data_dir() / _DB_FILENAME


def get_academic_attachments_dir() -> Path:
    """学术附件目录（预留）：`{共享根}/academic/attachments/`。"""
    p = get_academic_data_dir() / "attachments"
    p.mkdir(parents=True, exist_ok=True)
    return p
