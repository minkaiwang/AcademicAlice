from __future__ import annotations

import tempfile
import unittest
import zipfile
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch

from install import install_deps


class InstallerSecurityTests(unittest.TestCase):
    def test_archive_extraction_rejects_parent_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "malicious.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../outside.txt", "bad")

            with self.assertRaisesRegex(OSError, "unsafe path"):
                install_deps._extract_zip_with_progress(
                    archive_path,
                    root / "extract",
                )

            self.assertFalse((root / "outside.txt").exists())

    def test_archive_extraction_rejects_windows_path_tricks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for unsafe_name in (
                "folder/file.txt:payload",
                "folder/CON.txt",
                "folder/trailing. ",
            ):
                archive_path = root / "malicious.zip"
                with zipfile.ZipFile(archive_path, "w") as archive:
                    archive.writestr(unsafe_name, "bad")
                with self.assertRaisesRegex(OSError, "unsafe path"):
                    install_deps._extract_zip_with_progress(
                        archive_path,
                        root / "extract",
                    )

    def test_archive_extraction_rejects_case_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "duplicates.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("Config/settings.py", "first")
                archive.writestr("config/settings.py", "second")

            with self.assertRaisesRegex(OSError, "duplicate"):
                install_deps._extract_zip_with_progress(
                    archive_path,
                    root / "extract",
                )

    def test_pip_install_keeps_tls_verification_enabled(self) -> None:
        result = Mock(returncode=0, stdout="", stderr="")
        mirror = {
            "name": "PyPI",
            "url": "https://pypi.org/simple",
            "host": "pypi.org",
        }
        with patch.object(
            install_deps,
            "_run_pip",
            return_value=result,
        ) as run_pip:
            self.assertTrue(
                install_deps._install_one("python", "requests", [mirror])
            )

        arguments = run_pip.call_args.args
        self.assertNotIn("--trusted-host", arguments)

    def test_ensure_pip_does_not_execute_remote_bootstrap_script(self) -> None:
        failed = Mock(returncode=1, stdout="", stderr="")
        with (
            patch.object(
                install_deps,
                "_run_python_module",
                return_value=failed,
            ),
            patch.object(
                install_deps,
                "_has_pip",
                return_value=False,
            ),
            patch.object(
                install_deps.urllib.request,
                "urlretrieve",
            ) as retrieve,
        ):
            self.assertFalse(install_deps.ensure_pip("python"))

        retrieve.assert_not_called()

    def test_vosk_models_have_pinned_size_and_sha256(self) -> None:
        for spec in install_deps.VOSK_MODEL_SPECS:
            self.assertGreater(int(spec["size"]), 0)
            self.assertRegex(str(spec["sha256"]), r"^[0-9a-f]{64}$")

    def test_vendored_pyncm_wheel_checksum_matches_installer_pin(self) -> None:
        local_spec = install_deps.LOCAL_DEPENDENCY_WHEELS["pyncm"]
        wheel_path = Path(local_spec["path"])
        self.assertTrue(wheel_path.is_file())
        self.assertEqual(
            hashlib.sha256(wheel_path.read_bytes()).hexdigest(),
            local_spec["sha256"],
        )


if __name__ == "__main__":
    unittest.main()
