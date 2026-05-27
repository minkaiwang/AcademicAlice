"""学术数据 SQLite：占位库路径与版本迁移；仅用于清理早期实验性表。学术数据以 resc/workbench 为准。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# 与迁移脚本对齐；v4 起不再创建 events / todos 等 M1 表
SCHEMA_VERSION = 4


def init_database(db_path: Path) -> None:
    """
    确保库文件与目录存在。若库为 v3 及以前，则删除已弃用的实验性表并升级 user_version。

    若将来在 Python 侧为工作台做备份/同步而落库，再于此处追加建表与迁移。
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.cursor()
        cur.execute("PRAGMA user_version")
        row = cur.fetchone()
        ver = int(row[0]) if row else 0

        if ver < 4:
            # 早期实验性栈（已不维护）；主数据在浏览器科研工作台
            conn.execute("DROP TABLE IF EXISTS event_subtasks")
            conn.execute("DROP TABLE IF EXISTS events")
            conn.execute("DROP TABLE IF EXISTS todos")
            conn.execute("DROP TABLE IF EXISTS categories")
            conn.execute(f"PRAGMA user_version = {int(SCHEMA_VERSION)}")
        conn.commit()
    finally:
        conn.close()
