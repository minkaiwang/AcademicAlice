from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lib.script.workbench_storage import (
    clear_workbench_state,
    load_workbench_state,
    save_workbench_state,
)


class WorkbenchStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.state_path = Path(self._temp_dir.name) / "workbench" / "state.json"
        self.now = datetime(2026, 7, 26, 8, 0, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def test_save_and_load_round_trip(self) -> None:
        expected = {"tasks": [{"id": "task-1", "title": "写作"}]}

        save_result = save_workbench_state(
            expected,
            state_path=self.state_path,
            now=self.now,
        )
        load_result = load_workbench_state(state_path=self.state_path)

        self.assertEqual(expected, load_result["state"])
        self.assertTrue(load_result["exists"])
        self.assertEqual(1, load_result["schema_version"])
        self.assertEqual(str(self.state_path), save_result["path"])

    def test_legacy_raw_state_is_migrated(self) -> None:
        self.state_path.parent.mkdir(parents=True)
        self.state_path.write_text(
            json.dumps({"legacy": True}, ensure_ascii=False),
            encoding="utf-8",
        )

        result = load_workbench_state(state_path=self.state_path)
        record = json.loads(self.state_path.read_text(encoding="utf-8"))

        self.assertEqual({"legacy": True}, result["state"])
        self.assertEqual(1, record["schema_version"])
        self.assertEqual({"legacy": True}, record["payload"])

    def test_corrupt_primary_recovers_from_latest_valid_backup(self) -> None:
        first = {"revision": 1}
        second = {"revision": 2}
        save_workbench_state(
            first,
            state_path=self.state_path,
            now=self.now,
        )
        save_workbench_state(
            second,
            state_path=self.state_path,
            now=self.now + timedelta(minutes=6),
        )
        self.state_path.write_text("{broken", encoding="utf-8")

        result = load_workbench_state(state_path=self.state_path)

        self.assertEqual(first, result["state"])
        self.assertTrue(result["recovered_from"])
        self.assertTrue(
            list((self.state_path.parent / "backups").glob("corrupt-*.json"))
        )

    def test_clear_keeps_recoverable_backup(self) -> None:
        save_workbench_state(
            {"important": "data"},
            state_path=self.state_path,
            now=self.now,
        )

        result = clear_workbench_state(state_path=self.state_path)

        self.assertFalse(self.state_path.exists())
        self.assertTrue(result["backup_path"])
        self.assertTrue(Path(result["backup_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
