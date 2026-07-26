from __future__ import annotations

import hashlib
import shutil
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from lib.script.update_manager import (
    InstalledState,
    ReleaseInfo,
    UpdateError,
    UpdateManager,
    _is_newer_release,
    _version_key,
    expected_update_asset_name,
    select_release_assets,
)


def _release(tag: str = "LTS1.0.6") -> ReleaseInfo:
    return ReleaseInfo(
        tag=tag,
        published_at=datetime(2026, 7, 26, tzinfo=timezone.utc),
        asset_name=f"AemeathDeskPet-{tag}.zip",
        download_url="https://github.com/example/release.zip",
        checksum_name=f"AemeathDeskPet-{tag}.zip.sha256",
        checksum_url="https://github.com/example/release.zip.sha256",
    )


class UpdateAssetSelectionTests(unittest.TestCase):
    def test_selects_only_exact_archive_and_checksum_names(self) -> None:
        tag = "LTS1.0.6"
        archive_name = expected_update_asset_name(tag, "source")
        checksum_name = f"{archive_name}.sha256"
        release_data = {
            "tag_name": tag,
            "assets": [
                {"name": "source.zip", "browser_download_url": "https://bad"},
                {"name": archive_name, "browser_download_url": "https://good"},
                {"name": checksum_name, "browser_download_url": "https://sum"},
            ],
        }

        archive, checksum = select_release_assets(
            release_data,
            variant="source",
        )

        self.assertEqual(archive_name, archive["name"])
        self.assertEqual(checksum_name, checksum["name"])

    def test_rejects_release_with_only_generic_zip(self) -> None:
        release_data = {
            "tag_name": "LTS1.0.6",
            "assets": [{"name": "source.zip"}],
        }

        with self.assertRaises(UpdateError):
            select_release_assets(release_data, variant="source")


class UpdateVersionOrderingTests(unittest.TestCase):
    def test_repository_version_tags_have_expected_order(self) -> None:
        self.assertLess(
            _version_key("LTS1.0.5pre1"),
            _version_key("LTS1.0.5pre2"),
        )
        self.assertLess(
            _version_key("LTS1.0.5pre2"),
            _version_key("LTS1.0.5"),
        )
        self.assertLess(
            _version_key("LTS1.0.5"),
            _version_key("LTS1.0.6"),
        )

    def test_newer_version_wins_even_on_same_or_older_date(self) -> None:
        installed = InstalledState(
            "LTS1.0.5pre2",
            datetime(2026, 7, 26, tzinfo=timezone.utc),
        )
        release = _release("LTS1.0.6")
        self.assertTrue(_is_newer_release(installed, release))

        old_release = ReleaseInfo(
            **{
                **release.__dict__,
                "published_at": datetime(2026, 7, 25, tzinfo=timezone.utc),
            }
        )
        self.assertTrue(_is_newer_release(installed, old_release))

    def test_future_date_cannot_downgrade_parseable_version(self) -> None:
        installed = InstalledState(
            "LTS1.0.6",
            datetime(2026, 7, 26, tzinfo=timezone.utc),
        )
        release = _release("LTS1.0.5pre2")
        future_release = ReleaseInfo(
            **{
                **release.__dict__,
                "published_at": datetime(2027, 1, 1, tzinfo=timezone.utc),
            }
        )
        self.assertFalse(_is_newer_release(installed, future_release))

    def test_legacy_unparseable_tags_fall_back_to_date(self) -> None:
        installed = InstalledState(
            "legacy-build",
            datetime(2026, 7, 25, tzinfo=timezone.utc),
        )
        release = _release("nightly")
        self.assertTrue(_is_newer_release(installed, release))


class UpdateSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._temp_dir.name)
        self.state_path = self.root / "resc" / "user" / "update_state.json"
        self.manager = UpdateManager(
            project_root=self.root,
            state_path=self.state_path,
            asset_variant="source",
        )

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def test_check_for_update_does_not_write_or_install(self) -> None:
        release = _release()
        with patch.object(
            self.manager,
            "_fetch_latest_release",
            return_value=release,
        ):
            result = self.manager.check_for_update()

        self.assertFalse(result.updated)
        self.assertEqual("update_available", result.reason)
        self.assertFalse(self.state_path.exists())
        self.assertEqual([], list(self.root.glob("**/update_backups")))

    def test_safe_extract_rejects_parent_traversal(self) -> None:
        archive_path = self.root / "malicious.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("../outside.txt", "bad")

        with self.assertRaises(UpdateError):
            self.manager._safe_extract(archive_path, self.root / "extract")

        self.assertFalse((self.root.parent / "outside.txt").exists())

    def test_safe_extract_rejects_windows_path_tricks(self) -> None:
        for unsafe_name in (
            "folder/file.txt:payload",
            "folder/CON.txt",
            "folder/trailing. ",
        ):
            archive_path = self.root / "malicious.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(unsafe_name, "bad")

            with self.assertRaises(UpdateError, msg=unsafe_name):
                self.manager._safe_extract(
                    archive_path,
                    self.root / "extract",
                )
            archive_path.unlink()

    def test_safe_extract_rejects_case_insensitive_duplicates(self) -> None:
        archive_path = self.root / "duplicates.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("Config/settings.py", "first")
            archive.writestr("config/settings.py", "second")

        with self.assertRaisesRegex(UpdateError, "大小写"):
            self.manager._safe_extract(archive_path, self.root / "extract")

    def test_safe_extract_rejects_extreme_compression_ratio(self) -> None:
        archive_path = self.root / "zip-bomb.zip"
        with zipfile.ZipFile(
            archive_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.writestr("huge.txt", b"0" * (1024 * 1024))

        with self.assertRaisesRegex(UpdateError, "压缩比"):
            self.manager._safe_extract(archive_path, self.root / "extract")

    def test_protected_paths_are_case_insensitive(self) -> None:
        content_root = self.root / "staged"
        (content_root / "Resc" / "User").mkdir(parents=True)
        protected = content_root / "Resc" / "User" / "preferences.json"
        protected.write_text("do not overwrite", encoding="utf-8")

        files = list(self.manager._iter_content_files(content_root))

        self.assertEqual([], files)

    def test_apply_rejects_existing_symlink_target(self) -> None:
        outside = self.root.parent / f"{self.root.name}-outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = self.root / "linked.txt"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("当前环境不允许创建符号链接")
        content_root = self.root / "staged"
        content_root.mkdir()
        (content_root / "linked.txt").write_text("new", encoding="utf-8")

        with self.assertRaisesRegex(UpdateError, "符号链接"):
            self.manager._apply_with_rollback(content_root, _release())

        self.assertEqual("outside", outside.read_text(encoding="utf-8"))
        outside.unlink()

    def test_apply_failure_rolls_back_already_replaced_files(self) -> None:
        content_root = self.root / "staged"
        (content_root / "config").mkdir(parents=True)
        (content_root / "app_brand.py").write_text("new brand", encoding="utf-8")
        (content_root / "config" / "version_info.py").write_text(
            "new version",
            encoding="utf-8",
        )
        (self.root / "config").mkdir(parents=True)
        (self.root / "app_brand.py").write_text("old brand", encoding="utf-8")
        (self.root / "config" / "version_info.py").write_text(
            "old version",
            encoding="utf-8",
        )

        real_replace = __import__("os").replace
        replace_calls = 0

        def fail_second_replace(source, destination):
            nonlocal replace_calls
            replace_calls += 1
            if replace_calls == 2:
                raise OSError("simulated write failure")
            return real_replace(source, destination)

        with patch(
            "lib.script.update_manager.os.replace",
            side_effect=fail_second_replace,
        ):
            with self.assertRaises(UpdateError):
                self.manager._apply_with_rollback(content_root, _release())

        self.assertEqual(
            "old brand",
            (self.root / "app_brand.py").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            "old version",
            (self.root / "config" / "version_info.py").read_text(
                encoding="utf-8"
            ),
        )

    def test_state_write_failure_rolls_back_applied_release(self) -> None:
        archive_path = self.root / "prepared-update.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("app_brand.py", "new brand")
            archive.writestr("config/version_info.py", "new version")
            archive.writestr("lib/core/qt_desktop_pet.py", "new pet")
            archive.writestr("new-only.txt", "temporary")
        archive_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()

        (self.root / "config").mkdir(parents=True)
        (self.root / "lib" / "core").mkdir(parents=True)
        (self.root / "app_brand.py").write_text("old brand", encoding="utf-8")
        (self.root / "config" / "version_info.py").write_text(
            "old version",
            encoding="utf-8",
        )
        (self.root / "lib" / "core" / "qt_desktop_pet.py").write_text(
            "old pet",
            encoding="utf-8",
        )

        def provide_download(_url, destination, **_kwargs):
            if destination.suffix == ".zip":
                shutil.copy2(archive_path, destination)
            else:
                destination.write_text(
                    f"{archive_sha256}  {_release().asset_name}\n",
                    encoding="utf-8",
                )

        with (
            patch.object(
                self.manager,
                "_download_file",
                side_effect=provide_download,
            ),
            patch.object(
                self.manager,
                "_write_installed_state",
                side_effect=OSError("simulated state failure"),
            ),
        ):
            with self.assertRaisesRegex(UpdateError, "已恢复更新前文件"):
                self.manager.install_release(_release())

        self.assertEqual(
            "old brand",
            (self.root / "app_brand.py").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            "old version",
            (self.root / "config" / "version_info.py").read_text(
                encoding="utf-8"
            ),
        )
        self.assertEqual(
            "old pet",
            (self.root / "lib" / "core" / "qt_desktop_pet.py").read_text(
                encoding="utf-8"
            ),
        )
        self.assertFalse((self.root / "new-only.txt").exists())
        rollback_statuses = list(
            self.root.glob(
                "resc/user/update_backups/*/rollback-status.json"
            )
        )
        self.assertEqual(1, len(rollback_statuses))


if __name__ == "__main__":
    unittest.main()
