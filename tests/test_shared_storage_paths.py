from pathlib import Path

from config import shared_storage_paths


def _clear_root_cache() -> None:
    shared_storage_paths.get_shared_root_dir.cache_clear()


def test_explicit_shared_root_override_has_priority(monkeypatch, tmp_path: Path):
    override = tmp_path / "explicit"
    monkeypatch.setenv("AEMEATH_SHARED_ROOT", str(override))
    _clear_root_cache()
    try:
        assert shared_storage_paths.get_shared_root_dir() == override.resolve()
    finally:
        _clear_root_cache()


def test_existing_legacy_drive_root_is_preserved(monkeypatch, tmp_path: Path):
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    monkeypatch.delenv("AEMEATH_SHARED_ROOT", raising=False)
    monkeypatch.setattr(shared_storage_paths, "_legacy_drive_root", lambda: legacy)
    monkeypatch.setattr(
        shared_storage_paths,
        "_user_data_root",
        lambda: tmp_path / "local-app-data",
    )
    _clear_root_cache()
    try:
        assert shared_storage_paths.get_shared_root_dir() == legacy
    finally:
        _clear_root_cache()


def test_fresh_install_uses_user_writable_data_directory(monkeypatch, tmp_path: Path):
    legacy = tmp_path / "missing-legacy"
    local_data = tmp_path / "local-app-data" / "AemeathDeskPet"
    monkeypatch.delenv("AEMEATH_SHARED_ROOT", raising=False)
    monkeypatch.setattr(shared_storage_paths, "_legacy_drive_root", lambda: legacy)
    monkeypatch.setattr(shared_storage_paths, "_user_data_root", lambda: local_data)
    _clear_root_cache()
    try:
        assert shared_storage_paths.get_shared_root_dir() == local_data
        assert shared_storage_paths.get_shared_config_path("chat", "memory.txt") == (
            local_data / "config" / "chat" / "memory.txt"
        ).resolve()
    finally:
        _clear_root_cache()
