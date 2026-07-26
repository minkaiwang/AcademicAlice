from __future__ import annotations

import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import package_green_release, package_release


FORBIDDEN_ROOTS = {
    ".git",
    "build",
    "dist",
    "logs",
}


class PackagingManifestTests(unittest.TestCase):
    def _assert_manifest_is_clean(self, entries) -> None:
        paths = [entry.relative for entry in entries]
        self.assertTrue(paths)
        for path in paths:
            self.assertFalse(
                FORBIDDEN_ROOTS.intersection(path.parts),
                f"发行清单包含禁止目录：{path.as_posix()}",
            )
            self.assertNotEqual(
                ("resc", "user"),
                path.parts[:2],
                f"发行清单包含用户数据：{path.as_posix()}",
            )
            self.assertFalse(
                path.name.endswith((".bak", ".log", ".tmp", ".part")),
                f"发行清单包含临时文件：{path.as_posix()}",
            )
            self.assertNotIn(
                path.name.casefold(),
                {".env", "qrcode.png", "storage_state.json"},
                f"发行清单包含认证或登录态文件：{path.as_posix()}",
            )

    def test_source_manifest_excludes_build_and_runtime_data(self) -> None:
        entries = list(package_release._iter_files(include_untracked=True))
        self._assert_manifest_is_clean(entries)
        package_release._validate_release_entries(entries)

    def test_green_manifest_excludes_build_and_user_data(self) -> None:
        entries = list(
            package_green_release._iter_files(include_untracked=True)
        )
        self._assert_manifest_is_clean(entries)
        package_green_release._validate_release_entries(entries)

    def test_source_archive_metadata_and_bytes_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source_path = root / "sample.txt"
            source_path.write_text("stable\n", encoding="utf-8")
            entry = package_release.FileEntry(
                relative=Path("sample.txt"),
                size=source_path.stat().st_size,
            )
            first = root / "first.zip"
            second = root / "second.zip"
            with patch.object(package_release, "ROOT", root):
                package_release._write_archive(first, [entry], [], {})
                package_release._write_archive(second, [entry], [], {})

            self.assertEqual(
                hashlib.sha256(first.read_bytes()).digest(),
                hashlib.sha256(second.read_bytes()).digest(),
            )
            with zipfile.ZipFile(first) as archive:
                info = archive.getinfo("sample.txt")
                self.assertEqual((1980, 1, 1, 0, 0, 0), info.date_time)

    def test_sensitive_runtime_files_are_defensively_excluded(self) -> None:
        relative_paths = (
            Path("services/yuanbao-free-api/.env"),
            Path("services/yuanbao-free-api/qrcode.png"),
            Path("services/yuanbao-free-api/storage_state.json"),
        )
        for module in (package_release, package_green_release):
            for relative in relative_paths:
                with self.subTest(module=module.__name__, path=relative):
                    self.assertTrue(module._should_exclude(module.ROOT / relative))

    def test_version_cannot_escape_output_directory(self) -> None:
        for module in (package_release, package_green_release):
            for invalid in ("../escape", r"..\escape", "v1/escape", "v1:escape", ""):
                with self.subTest(module=module.__name__, version=invalid):
                    with self.assertRaises(RuntimeError):
                        module._validate_version(invalid)
            self.assertEqual("LTS1.0.5pre2", module._validate_version("LTS1.0.5pre2"))

    def test_release_defaults_match_canonical_version(self) -> None:
        version_source = (
            package_release.ROOT / "config" / "version_info.py"
        ).read_text(encoding="utf-8")
        for module in (package_release, package_green_release):
            with self.subTest(module=module.__name__):
                self.assertIn(
                    f'APP_VERSION = "{module.DEFAULT_VERSION}"',
                    version_source,
                )

    def test_case_insensitive_archive_collisions_are_rejected(self) -> None:
        entries = [
            package_release.FileEntry(Path("Docs/Readme.md"), 1),
            package_release.FileEntry(Path("docs/README.md"), 1),
        ]
        with self.assertRaises(RuntimeError):
            package_release._validate_release_entries(entries)

    def test_archive_writer_rejects_symlink_source_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            outside = root.parent / f"{root.name}-outside.txt"
            outside.write_text("private", encoding="utf-8")
            link = root / "linked.txt"
            try:
                link.symlink_to(outside)
            except OSError:
                outside.unlink(missing_ok=True)
                self.skipTest("当前 Windows 账户不允许创建符号链接")
            try:
                entry = package_release.FileEntry(Path("linked.txt"), outside.stat().st_size)
                with (
                    patch.object(package_release, "ROOT", root),
                    self.assertRaises(RuntimeError),
                ):
                    package_release._write_archive(root / "bad.zip", [entry], [], {})
            finally:
                outside.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
