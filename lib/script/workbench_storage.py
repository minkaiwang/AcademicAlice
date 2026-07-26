"""科研工作台的稳定本地存储。

浏览器 ``localStorage`` 只作为当前页面的缓存；主状态保存在共享目录下的
``workbench/state.json``。写入采用原子替换，并保留有上限的时间点备份。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.shared_storage_paths import get_shared_root_dir

SCHEMA_VERSION = 1
MAX_STATE_BYTES = 16 * 1024 * 1024
BACKUP_LIMIT = 12
BACKUP_MIN_INTERVAL_SECONDS = 5 * 60


class WorkbenchStorageError(RuntimeError):
    """工作台状态无法读取、验证或写入。"""


def get_workbench_storage_dir() -> Path:
    return get_shared_root_dir() / "workbench"


def get_workbench_state_path() -> Path:
    return get_workbench_storage_dir() / "state.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(now: datetime | None = None) -> str:
    value = (now or _utc_now()).astimezone(timezone.utc)
    return value.strftime("%Y%m%dT%H%M%S%fZ")


def _isoformat(now: datetime | None = None) -> str:
    value = (now or _utc_now()).astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _backup_dir(state_path: Path) -> Path:
    return state_path.parent / "backups"


def _validate_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise WorkbenchStorageError("工作台状态必须是 JSON 对象")
    try:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise WorkbenchStorageError(f"工作台状态无法序列化: {exc}") from exc
    if len(encoded) > MAX_STATE_BYTES:
        raise WorkbenchStorageError(
            f"工作台状态过大: {len(encoded)} bytes，限制 {MAX_STATE_BYTES} bytes"
        )
    return payload


def _encode_record(payload: dict[str, Any], now: datetime | None = None) -> bytes:
    record = {
        "schema_version": SCHEMA_VERSION,
        "saved_at": _isoformat(now),
        "payload": _validate_payload(payload),
    }
    encoded = json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8")
    if len(encoded) > MAX_STATE_BYTES:
        raise WorkbenchStorageError(
            f"工作台状态文件过大: {len(encoded)} bytes，限制 {MAX_STATE_BYTES} bytes"
        )
    return encoded


def _decode_record(raw: bytes) -> tuple[dict[str, Any], dict[str, Any]]:
    if len(raw) > MAX_STATE_BYTES:
        raise WorkbenchStorageError(
            f"工作台状态文件过大: {len(raw)} bytes，限制 {MAX_STATE_BYTES} bytes"
        )
    try:
        parsed = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkbenchStorageError(f"工作台状态 JSON 损坏: {exc}") from exc
    if not isinstance(parsed, dict):
        raise WorkbenchStorageError("工作台状态根节点必须是 JSON 对象")

    if "payload" not in parsed or "schema_version" not in parsed:
        return _validate_payload(parsed), {
            "schema_version": 0,
            "saved_at": "",
            "legacy": True,
        }

    try:
        schema_version = int(parsed.get("schema_version"))
    except (TypeError, ValueError) as exc:
        raise WorkbenchStorageError("工作台状态 schema_version 无效") from exc
    if schema_version > SCHEMA_VERSION:
        raise WorkbenchStorageError(
            f"工作台状态版本 {schema_version} 高于当前支持版本 {SCHEMA_VERSION}"
        )
    payload = _validate_payload(parsed.get("payload"))
    return payload, {
        "schema_version": schema_version,
        "saved_at": str(parsed.get("saved_at") or ""),
        "legacy": False,
    }


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp_path.write_bytes(data)
        os.replace(temp_path, path)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def _prune_backups(state_path: Path, limit: int = BACKUP_LIMIT) -> None:
    backup_root = _backup_dir(state_path)
    if not backup_root.exists():
        return
    backups = sorted(
        (
            path
            for path in backup_root.glob("state-*.json")
            if path.is_file()
        ),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    for stale in backups[max(1, int(limit)):]:
        try:
            stale.unlink()
        except OSError:
            continue


def _backup_existing(
    state_path: Path,
    *,
    force: bool = False,
    now: datetime | None = None,
) -> Path | None:
    if not state_path.is_file():
        return None
    backup_root = _backup_dir(state_path)
    backup_root.mkdir(parents=True, exist_ok=True)
    if not force:
        newest = max(
            (path for path in backup_root.glob("state-*.json") if path.is_file()),
            key=lambda path: path.stat().st_mtime_ns,
            default=None,
        )
        if newest is not None:
            age = _utc_now().timestamp() - newest.stat().st_mtime
            if age < BACKUP_MIN_INTERVAL_SECONDS:
                return None

    raw = state_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()[:12]
    backup_path = backup_root / f"state-{_timestamp(now)}-{digest}.json"
    shutil.copy2(state_path, backup_path)
    backup_time = (now or _utc_now()).timestamp()
    os.utime(backup_path, (backup_time, backup_time))
    _prune_backups(state_path)
    return backup_path


def _quarantine_corrupt_state(
    state_path: Path,
    *,
    now: datetime | None = None,
) -> Path | None:
    if not state_path.is_file():
        return None
    backup_root = _backup_dir(state_path)
    backup_root.mkdir(parents=True, exist_ok=True)
    target = backup_root / f"corrupt-{_timestamp(now)}.json"
    try:
        shutil.copy2(state_path, target)
    except OSError:
        return None
    return target


def save_workbench_state(
    payload: dict[str, Any],
    *,
    state_path: Path | None = None,
    make_backup: bool = True,
    force_backup: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    path = Path(state_path) if state_path is not None else get_workbench_state_path()
    encoded = _encode_record(payload, now)
    backup_path = (
        _backup_existing(path, force=force_backup, now=now)
        if make_backup
        else None
    )
    _write_atomic(path, encoded)
    return {
        "path": str(path),
        "schema_version": SCHEMA_VERSION,
        "saved_at": _isoformat(now),
        "backup_path": str(backup_path) if backup_path else "",
    }


def _iter_valid_backups(state_path: Path):
    backup_root = _backup_dir(state_path)
    if not backup_root.exists():
        return
    candidates = sorted(
        (
            path
            for path in backup_root.glob("state-*.json")
            if path.is_file()
        ),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    for candidate in candidates:
        try:
            payload, meta = _decode_record(candidate.read_bytes())
        except (OSError, WorkbenchStorageError):
            continue
        yield candidate, payload, meta


def load_workbench_state(
    *,
    state_path: Path | None = None,
    recover: bool = True,
) -> dict[str, Any]:
    path = Path(state_path) if state_path is not None else get_workbench_state_path()
    if not path.exists():
        return {
            "exists": False,
            "state": {},
            "path": str(path),
            "schema_version": SCHEMA_VERSION,
            "saved_at": "",
            "recovered_from": "",
        }

    try:
        payload, meta = _decode_record(path.read_bytes())
    except (OSError, WorkbenchStorageError) as primary_error:
        if not recover:
            raise WorkbenchStorageError(str(primary_error)) from primary_error
        for backup_path, payload, meta in _iter_valid_backups(path):
            _quarantine_corrupt_state(path)
            restored = save_workbench_state(
                payload,
                state_path=path,
                make_backup=False,
            )
            return {
                "exists": True,
                "state": payload,
                "path": str(path),
                "schema_version": restored["schema_version"],
                "saved_at": restored["saved_at"],
                "recovered_from": str(backup_path),
            }
        raise WorkbenchStorageError(str(primary_error)) from primary_error

    if meta.get("legacy"):
        migrated = save_workbench_state(payload, state_path=path)
        meta = {
            "schema_version": migrated["schema_version"],
            "saved_at": migrated["saved_at"],
            "legacy": False,
        }

    return {
        "exists": True,
        "state": payload,
        "path": str(path),
        "schema_version": int(meta.get("schema_version") or SCHEMA_VERSION),
        "saved_at": str(meta.get("saved_at") or ""),
        "recovered_from": "",
    }


def clear_workbench_state(
    *,
    state_path: Path | None = None,
) -> dict[str, Any]:
    path = Path(state_path) if state_path is not None else get_workbench_state_path()
    backup_path = _backup_existing(path, force=True)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    return {
        "cleared": True,
        "path": str(path),
        "backup_path": str(backup_path) if backup_path else "",
    }
