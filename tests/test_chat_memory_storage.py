from pathlib import Path

from lib.script.chat import memory as memory_module


def test_legacy_memory_is_migrated_once_but_not_mirrored(monkeypatch, tmp_path: Path):
    project_root = tmp_path / "project"
    legacy = project_root / "resc" / "user" / "memory.txt"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("[old][日常][user:]旧记录\n", encoding="utf-8")
    primary = tmp_path / "shared" / "chat" / "memory.txt"
    monkeypatch.setattr(memory_module, "get_project_root", lambda: project_root)

    stream_memory = memory_module.StreamMemory(memory_file=primary)
    try:
        assert primary.read_text(encoding="utf-8") == legacy.read_text(encoding="utf-8")
        stream_memory._append_lines("user", "日常", ["新记录"])
        assert "新记录" in primary.read_text(encoding="utf-8")
        assert "新记录" not in legacy.read_text(encoding="utf-8")
    finally:
        stream_memory.cleanup()


def test_memory_does_not_create_legacy_repo_directory(monkeypatch, tmp_path: Path):
    project_root = tmp_path / "project"
    primary = tmp_path / "shared" / "chat" / "memory.txt"
    legacy_parent = project_root / "resc" / "user"
    monkeypatch.setattr(memory_module, "get_project_root", lambda: project_root)

    stream_memory = memory_module.StreamMemory(memory_file=primary)
    try:
        stream_memory._append_lines("you", "日常", ["仅共享目录"])
        assert primary.exists()
        assert not legacy_parent.exists()
        ok, error = stream_memory.clear_all_history()
        assert ok, error
        assert not legacy_parent.exists()
    finally:
        stream_memory.cleanup()
