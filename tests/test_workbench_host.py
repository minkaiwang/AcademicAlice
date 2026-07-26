from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from lib.script.workbench_host import create_workbench_server


class WorkbenchHostApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        root = Path(self._temp_dir.name)
        (root / "index.html").write_text("ok", encoding="utf-8")
        (root / "private.json").write_text(
            '{"secret": true}',
            encoding="utf-8",
        )
        (root / "index.html.20260726.bak").write_text(
            "backup",
            encoding="utf-8",
        )
        self.state_path = root / "state" / "state.json"
        self.server = create_workbench_server(
            root,
            preferred_port=0,
            state_path=self.state_path,
        )
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self._temp_dir.cleanup()

    def _json_request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        *,
        authorize: bool = False,
    ) -> tuple[int, dict]:
        body = (
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
            if payload is not None
            else None
        )
        headers = {}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if authorize:
            headers["X-Aemeath-Workbench"] = "1"
            headers["Origin"] = self.base_url
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_state_round_trip_through_http_api(self) -> None:
        status, initial = self._json_request("GET", "/api/workbench/state")
        self.assertEqual(200, status)
        self.assertFalse(initial["exists"])

        expected = {"projects": [{"id": "p1", "name": "论文"}]}
        status, saved = self._json_request(
            "PUT",
            "/api/workbench/state",
            expected,
            authorize=True,
        )
        self.assertEqual(200, status)
        self.assertTrue(saved["ok"])

        status, loaded = self._json_request("GET", "/api/workbench/state")
        self.assertEqual(200, status)
        self.assertEqual(expected, loaded["state"])

        status, cleared = self._json_request(
            "DELETE",
            "/api/workbench/state",
            authorize=True,
        )
        self.assertEqual(200, status)
        self.assertTrue(cleared["cleared"])

    def test_write_without_workbench_header_is_rejected(self) -> None:
        with self.assertRaises(HTTPError) as raised:
            self._json_request(
                "PUT",
                "/api/workbench/state",
                {"forbidden": True},
            )

        self.assertEqual(403, raised.exception.code)
        self.assertFalse(self.state_path.exists())

    def test_root_redirects_without_directory_listing(self) -> None:
        request = Request(f"{self.base_url}/", method="GET")
        with urlopen(request, timeout=3) as response:
            self.assertEqual(f"{self.base_url}/index.html", response.url)
            self.assertEqual(b"ok", response.read())

    def test_non_runtime_and_backup_files_are_not_served(self) -> None:
        for path in (
            "/private.json",
            "/index.html.20260726.bak",
            "/state/",
        ):
            with self.subTest(path=path):
                with self.assertRaises(HTTPError) as raised:
                    urlopen(f"{self.base_url}{path}", timeout=3)
                self.assertEqual(404, raised.exception.code)

    def test_invalid_host_header_is_rejected(self) -> None:
        request = Request(
            f"{self.base_url}/api/workbench/health",
            headers={"Host": "attacker.invalid"},
            method="GET",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=3)
        self.assertEqual(421, raised.exception.code)

    def test_static_security_headers_are_present(self) -> None:
        with urlopen(f"{self.base_url}/index.html", timeout=3) as response:
            self.assertEqual("DENY", response.headers["X-Frame-Options"])
            self.assertIn(
                "default-src 'self'",
                response.headers["Content-Security-Policy"],
            )


if __name__ == "__main__":
    unittest.main()
