from __future__ import annotations

import subprocess
import threading
import unittest
from unittest.mock import Mock, patch

from lib.script.gsvmove import service as gsvmove_service


class GsvmoveServiceSafetyTests(unittest.TestCase):
    def test_no_owned_process_is_already_stopped(self) -> None:
        instance = gsvmove_service.GsvmoveService.__new__(
            gsvmove_service.GsvmoveService
        )

        with patch.object(
            instance,
            "_terminate_process_tree",
        ) as terminate:
            self.assertTrue(instance._shutdown_started_service(None))

        terminate.assert_not_called()

    def test_shutdown_targets_only_the_owned_process(self) -> None:
        instance = gsvmove_service.GsvmoveService.__new__(
            gsvmove_service.GsvmoveService
        )
        proc = Mock(spec=subprocess.Popen)
        proc.pid = 1234
        proc.poll.side_effect = [None, 0, 0]
        proc.wait.return_value = 0

        with patch.object(
            instance,
            "_terminate_process_tree",
            return_value=True,
        ) as terminate:
            self.assertTrue(instance._shutdown_started_service(proc))

        terminate.assert_called_once_with(proc, force=False)

    def test_ensure_ready_does_not_launch_during_shutdown(self) -> None:
        instance = gsvmove_service.GsvmoveService.__new__(
            gsvmove_service.GsvmoveService
        )
        instance._worker_stop = threading.Event()
        instance._worker_stop.set()
        instance._health_check = Mock(return_value=False)
        instance._start_service_process = Mock(return_value=True)

        self.assertFalse(instance._ensure_service_ready())
        instance._health_check.assert_not_called()
        instance._start_service_process.assert_not_called()

    def test_source_has_no_process_enumeration_fallback(self) -> None:
        source = gsvmove_service.Path(
            gsvmove_service.__file__
        ).read_text(encoding="utf-8")
        self.assertNotIn("_find_gsvmove_service_pids", source)
        self.assertNotIn("Get-CimInstance Win32_Process", source)


if __name__ == "__main__":
    unittest.main()
