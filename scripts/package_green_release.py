#!/usr/bin/env python3
"""
Create a green distribution archive that keeps bundled runtime assets
such as Vosk models and Chromium resources for direct file sharing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSION = "LTS1.0.5pre2"
DIST_DIR = ROOT / "dist"

EXCLUDE_PART_NAMES = {
    ".git",
    ".github",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "logs",
    "tmp",
    ".vscode",
}

EXCLUDE_PATH_PREFIXES = {
    Path("config") / ".shared_pending",
    Path("resc") / "user",
    Path("resc") / "gsvmove_update",
}

EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
    ".tmp",
    ".part",
    ".bak",
}

ROOT_ARCHIVE_SUFFIXES = {
    ".zip",
    ".7z",
    ".tar",
    ".gz",
}

EXCLUDE_FILE_NAMES = {
    ".env",
    "py.ini",
    "playwright-chromium-chromium-1208.zip",
    "qrcode.png",
    "storage_state.json",
}

PLACEHOLDER_DIRS: tuple[Path, ...] = ()

REQUIRED_RELEASE_PATHS = {
    Path("app_brand.py"),
    Path("config/version_info.py"),
    Path("config/secure_secrets.py"),
    Path("lib/core/qt_desktop_pet.py"),
    Path("lib/script/update_manager.py"),
    Path("lib/script/workbench_host.py"),
    Path("lib/script/workbench_storage.py"),
    Path("resc/workbench/research_workbench.html"),
    Path("resc/workbench/LICENSE-UPSTREAM-MIT"),
    Path("resc/workbench/LICENSE-TAILWIND-MIT"),
    Path("resc/workbench/vendor/chart.js/chart.umd.js"),
    Path("resc/workbench/vendor/fontawesome/css/all.min.css"),
    Path("THIRD_PARTY_NOTICES.md"),
    Path("vendor/pyncm-1.8.1-py3-none-any.whl"),
    Path("vendor/README.md"),
}

_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


@dataclass
class FileEntry:
    relative: Path
    size: int


def _is_under(path: Path, prefix: Path) -> bool:
    prefix_parts = prefix.parts
    parts = path.parts
    if len(parts) < len(prefix_parts):
        return False
    return parts[: len(prefix_parts)] == prefix_parts


def _should_exclude(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    for part in rel.parts:
        if part in EXCLUDE_PART_NAMES:
            return True
    for prefix in EXCLUDE_PATH_PREFIXES:
        if _is_under(rel, prefix):
            return True
    if rel.name in EXCLUDE_FILE_NAMES:
        return True
    if rel.parent == Path('.') and path.suffix.lower() in ROOT_ARCHIVE_SUFFIXES:
        return True
    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return True
    return False


def _git_file_paths(*, include_untracked: bool = False) -> set[Path]:
    command = ["git", "-C", str(ROOT), "ls-files", "-z", "--cached"]
    if include_untracked:
        command.extend(["--others", "--exclude-standard"])
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("绿色包必须在可用的 Git 工作树中生成") from exc
    return {
        Path(raw.decode("utf-8"))
        for raw in result.stdout.split(b"\0")
        if raw
    }


def _assert_clean_worktree() -> None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "status",
                "--porcelain",
                "--untracked-files=all",
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("无法核对 Git 工作树状态") from exc
    changes = [line for line in result.stdout.splitlines() if line.strip()]
    if changes:
        raise RuntimeError(
            "正式绿色包要求干净的 Git 工作树；请先审查并提交改动。"
            "仅本地验证可显式使用 --allow-dirty。"
        )


def _validate_version(value: str) -> str:
    version = str(value or "").strip()
    if (
        not _VERSION_PATTERN.fullmatch(version)
        or ".." in version
        or version.endswith((".", " "))
    ):
        raise RuntimeError(
            "版本号仅允许 1-64 位字母、数字、点、下划线和连字符，且不得包含 '..'"
        )
    return version


def _safe_source_file(relative: Path) -> tuple[Path, int]:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError(f"发行路径非法：{relative.as_posix()}")

    path = ROOT / relative
    if path.is_symlink():
        raise RuntimeError(f"发行清单禁止符号链接：{relative.as_posix()}")
    try:
        resolved_root = ROOT.resolve(strict=True)
        resolved_path = path.resolve(strict=True)
        file_stat = path.stat()
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise RuntimeError(f"无法核对发行文件：{relative.as_posix()}") from exc
    if not resolved_path.is_relative_to(resolved_root):
        raise RuntimeError(f"发行文件越出工作区：{relative.as_posix()}")
    if not stat.S_ISREG(file_stat.st_mode):
        raise RuntimeError(f"发行清单只允许普通文件：{relative.as_posix()}")
    return path, file_stat.st_size


def _iter_files(*, include_untracked: bool = False) -> Iterator[FileEntry]:
    relative_paths = _git_file_paths(include_untracked=include_untracked)
    for runtime_root in (Path("resc/models"), Path("resc/playwright")):
        absolute_root = ROOT / runtime_root
        if not absolute_root.exists():
            continue
        relative_paths.update(
            path.relative_to(ROOT)
            for path in absolute_root.rglob("*")
            if path.is_file()
        )
    for rel in sorted(relative_paths, key=lambda item: item.as_posix()):
        path = ROOT / rel
        try:
            if not path.exists():
                continue
        except OSError:
            continue
        if path.is_dir() and not path.is_symlink():
            continue
        if _should_exclude(path):
            continue
        try:
            _, size = _safe_source_file(rel)
        except FileNotFoundError:
            continue
        yield FileEntry(relative=rel, size=size)


def _validate_release_entries(entries: Iterable[FileEntry]) -> None:
    entry_list = list(entries)
    present = {entry.relative for entry in entry_list}
    folded_paths: dict[str, Path] = {}
    for entry in entry_list:
        key = entry.relative.as_posix().casefold()
        previous = folded_paths.get(key)
        if previous is not None and previous != entry.relative:
            raise RuntimeError(
                "发行清单包含 Windows 下冲突的路径："
                f"{previous.as_posix()} / {entry.relative.as_posix()}"
            )
        folded_paths[key] = entry.relative
    missing = sorted(
        REQUIRED_RELEASE_PATHS - present,
        key=lambda path: path.as_posix(),
    )
    if missing:
        raise RuntimeError(
            "发行清单缺少关键文件："
            + ", ".join(path.as_posix() for path in missing)
        )


def _write_manifest(manifest_path: Path, files: Iterable[FileEntry]) -> None:
    data = [
        {
            "path": entry.relative.as_posix(),
            "size": entry.size,
        }
        for entry in files
    ]
    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_archive(
    zip_path: Path,
    file_entries: List[FileEntry],
    placeholder_entries: List[FileEntry],
    placeholder_payloads: Dict[Path, str],
) -> None:
    sources: list[tuple[FileEntry, Path]] = []
    for entry in file_entries:
        src, current_size = _safe_source_file(entry.relative)
        if current_size != entry.size:
            raise RuntimeError(
                f"打包期间文件大小发生变化：{entry.relative.as_posix()}"
            )
        sources.append((entry, src))

    temporary_path = zip_path.with_name(f"{zip_path.name}.tmp")
    temporary_path.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for entry, src in sources:
                info = zipfile.ZipInfo(entry.relative.as_posix(), _ZIP_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                with src.open("rb") as source, zf.open(info, "w") as destination:
                    shutil.copyfileobj(source, destination, length=1024 * 1024)
            for entry in placeholder_entries:
                payload = placeholder_payloads.get(entry.relative, "Generated at runtime.\n")
                info = zipfile.ZipInfo(entry.relative.as_posix(), _ZIP_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                zf.writestr(info, payload)
        os.replace(temporary_path, zip_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_sha256(checksum_path: Path, archive_path: Path) -> str:
    digest = hashlib.sha256()
    with archive_path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    value = digest.hexdigest()
    checksum_path.write_text(
        f"{value}  {archive_path.name}\n",
        encoding="ascii",
    )
    return value


def _build_placeholder_entries(version: str) -> Tuple[List[FileEntry], Dict[Path, str]]:
    entries: List[FileEntry] = []
    payloads: Dict[Path, str] = {}
    for placeholder in PLACEHOLDER_DIRS:
        arcname = placeholder / ".keep"
        text = f"{placeholder.as_posix()} is generated at runtime.\nVersion: {version}\n"
        entries.append(FileEntry(relative=arcname, size=len(text.encode("utf-8"))))
        payloads[arcname] = text
    return entries, payloads


def _format_size(num_bytes: int) -> str:
    units = ("B", "KB", "MB", "GB")
    value = float(num_bytes)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.2f}{unit}"
        value /= 1024.0
    return f"{value:.2f}GB"


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package AemeathDeskPet green release bundle.")
    parser.add_argument("--version", default=DEFAULT_VERSION, help="Version tag (default: %(default)s)")
    parser.add_argument("--output", type=Path, default=DIST_DIR, help="Output directory (default: dist/)")
    parser.add_argument("--dry-run", action="store_true", help="List files without creating archives")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="仅本地验证：包含未跟踪且未忽略的文件；正式发布禁止使用",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        args.version = _validate_version(args.version)
        if not args.allow_dirty:
            _assert_clean_worktree()
        entries = sorted(
            _iter_files(include_untracked=args.allow_dirty),
            key=lambda e: e.relative.as_posix(),
        )
        _validate_release_entries(entries)
    except RuntimeError as exc:
        print(f"[green-package] error: {exc}", file=sys.stderr)
        return 2
    placeholder_entries, placeholder_payloads = _build_placeholder_entries(args.version)
    all_entries = entries + placeholder_entries
    total_size = sum(entry.size for entry in entries)
    print(f"[green-package] files: {len(entries)} (+{len(placeholder_entries)} placeholders) | size: {_format_size(total_size)}")
    for entry in all_entries:
        hint = " [placeholder]" if entry in placeholder_entries else ""
        print(f"  {entry.relative.as_posix()} ({_format_size(entry.size)}){hint}")
    if args.dry_run:
        print("[green-package] dry-run complete; no artifacts produced.")
        return 0

    args.output.mkdir(parents=True, exist_ok=True)
    zip_path = args.output / f"AemeathDeskPet-{args.version}-green.zip"
    manifest_path = args.output / f"AemeathDeskPet-{args.version}-green-manifest.json"
    checksum_path = args.output / f"{zip_path.name}.sha256"

    try:
        _write_archive(zip_path, entries, placeholder_entries, placeholder_payloads)
        _write_manifest(manifest_path, all_entries)
        digest = _write_sha256(checksum_path, zip_path)
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"[green-package] error: {exc}", file=sys.stderr)
        return 2

    print(f"[green-package] wrote {zip_path.relative_to(ROOT)} ({_format_size(zip_path.stat().st_size)})")
    print(f"[green-package] wrote {manifest_path.relative_to(ROOT)}")
    print(f"[green-package] wrote {checksum_path.relative_to(ROOT)} ({digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
