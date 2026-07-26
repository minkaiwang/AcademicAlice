from __future__ import annotations

import re
import unittest
from pathlib import Path


WORKBENCH_ROOT = (
    Path(__file__).resolve().parents[1] / "resc" / "workbench"
)


class WorkbenchOfflineAssetTests(unittest.TestCase):
    def test_runtime_scripts_and_styles_are_local(self) -> None:
        html = (WORKBENCH_ROOT / "research_workbench.html").read_text(
            encoding="utf-8"
        )
        remote_runtime_assets = re.findall(
            r"""<(?:script|link)\b[^>]+(?:src|href)=["']https?://[^"']+""",
            html,
            flags=re.IGNORECASE,
        )
        self.assertEqual([], remote_runtime_assets)

    def test_referenced_local_assets_exist(self) -> None:
        html = (WORKBENCH_ROOT / "research_workbench.html").read_text(
            encoding="utf-8"
        )
        references = re.findall(
            r"""<(?:script|link)\b[^>]+(?:src|href)=["'](\./[^"'?#]+)""",
            html,
            flags=re.IGNORECASE,
        )
        self.assertTrue(references)
        for reference in references:
            target = WORKBENCH_ROOT / reference.removeprefix("./")
            self.assertTrue(target.is_file(), f"本地资源不存在：{reference}")

    def test_unimplemented_cloud_sync_is_explicitly_disabled(self) -> None:
        sync_ui = (WORKBENCH_ROOT / "sync" / "ui.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("disableUnavailableCloudSync", sync_ui)
        self.assertIn("element.disabled = true", sync_ui)
        self.assertNotRegex(
            sync_ui,
            r"""(?:import|from)\s*['"]https?://""",
        )

    def test_local_third_party_license_files_exist(self) -> None:
        self.assertTrue((WORKBENCH_ROOT / "LICENSE-UPSTREAM-MIT").is_file())
        self.assertTrue((WORKBENCH_ROOT / "LICENSE-TAILWIND-MIT").is_file())
        self.assertTrue(
            (WORKBENCH_ROOT / "vendor" / "chart.js" / "LICENSE.md").is_file()
        )
        self.assertTrue(
            (WORKBENCH_ROOT / "vendor" / "fontawesome" / "LICENSE.txt").is_file()
        )


if __name__ == "__main__":
    unittest.main()
