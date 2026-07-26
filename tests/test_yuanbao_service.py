from __future__ import annotations

import threading
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from lib.script.yuanbao_free_api import service as yuanbao_service


class YuanbaoServiceSafetyTests(unittest.TestCase):
    def test_invalid_local_port_is_treated_as_unmanaged(self) -> None:
        with patch.object(
            yuanbao_service.oc,
            "API_BASE_URL",
            "http://127.0.0.1:99999/v1",
        ):
            self.assertIsNone(yuanbao_service._parse_local_target())

    def test_frozen_launcher_uses_dedicated_service_mode(self) -> None:
        with (
            patch.object(
                yuanbao_service.sys,
                "frozen",
                True,
                create=True,
            ),
            patch.object(
                yuanbao_service.sys,
                "executable",
                r"C:\Aemeath\AemeathDeskPet.exe",
            ),
        ):
            command = yuanbao_service._launcher_command(8000)

        self.assertEqual(
            [
                r"C:\Aemeath\AemeathDeskPet.exe",
                "--yuanbao-service",
                "8000",
            ],
            command,
        )

    def test_incompatible_listener_is_never_terminated(self) -> None:
        instance = yuanbao_service.YuanbaoFreeApiService.__new__(
            yuanbao_service.YuanbaoFreeApiService
        )
        instance._ec = Mock()
        instance._proc_lock = threading.RLock()
        instance._process = None
        instance._started_by_app = False
        instance._start_service_process = Mock(return_value=True)

        with patch.object(
            yuanbao_service,
            "_probe_status_endpoint",
            return_value=("missing", None),
        ):
            result = instance._ensure_status_endpoint("127.0.0.1", 8000)

        self.assertIsNone(result)
        instance._start_service_process.assert_not_called()
        instance._ec.publish.assert_called_once()

    def test_control_requests_send_the_configured_bearer_key(self) -> None:
        response = Mock()
        response.headers.get_content_charset.return_value = "utf-8"
        response.read.return_value = b'{"ok": true}'
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)

        with (
            patch.object(
                yuanbao_service,
                "_configured_api_key",
                return_value="local-test-key",
            ),
            patch.object(
                yuanbao_service,
                "urlopen",
                return_value=response,
            ) as open_url,
        ):
            result = yuanbao_service._http_json(
                "http://127.0.0.1:8000/fsv/status"
            )

        self.assertEqual({"ok": True}, result)
        request = open_url.call_args.args[0]
        self.assertEqual(
            "Bearer local-test-key",
            request.get_header("Authorization"),
        )

    def test_service_env_routes_windowed_boot_output_to_launcher_log(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(
                yuanbao_service,
                "get_shared_root_dir",
                return_value=Path(temp_dir),
            ),
            patch.object(
                yuanbao_service,
                "_configured_api_key",
                return_value="local-test-key",
            ),
        ):
            env = yuanbao_service._build_service_env()

        self.assertEqual(
            str(Path(temp_dir) / "yuanbao_free_api" / "launcher.log"),
            env["AEMEATH_YUANBAO_BOOT_LOG"],
        )

    def test_login_monitor_honors_stop_event_before_polling(self) -> None:
        instance = yuanbao_service.YuanbaoFreeApiService.__new__(
            yuanbao_service.YuanbaoFreeApiService
        )
        instance._login_monitor_stop = threading.Event()
        instance._login_monitor_stop.set()
        instance._login_monitor_lock = threading.RLock()
        instance._login_monitor_thread = threading.current_thread()

        with patch.object(
            yuanbao_service,
            "_fetch_service_status",
        ) as fetch_status:
            instance._run_login_monitor("127.0.0.1", 8000)

        fetch_status.assert_not_called()
        self.assertIsNone(instance._login_monitor_thread)

    def test_stop_monitor_does_not_drop_a_live_thread_reference(self) -> None:
        instance = yuanbao_service.YuanbaoFreeApiService.__new__(
            yuanbao_service.YuanbaoFreeApiService
        )
        instance._login_monitor_stop = threading.Event()
        instance._login_monitor_lock = threading.RLock()
        thread = Mock(spec=threading.Thread)
        thread.is_alive.return_value = True
        instance._login_monitor_thread = thread

        self.assertFalse(instance._stop_login_monitor(timeout=0.0))
        self.assertIs(instance._login_monitor_thread, thread)
        self.assertTrue(instance._login_monitor_stop.is_set())

    def test_source_has_no_unknown_listener_kill_path(self) -> None:
        source = yuanbao_service.Path(
            yuanbao_service.__file__
        ).read_text(encoding="utf-8")
        self.assertNotIn("_find_listener_pids", source)
        self.assertNotIn("_kill_process_by_pid", source)
        self.assertIn("拒绝结束未知进程", source)


if __name__ == "__main__":
    unittest.main()
