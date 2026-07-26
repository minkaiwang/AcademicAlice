from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lib.core.qt_desktop_pet import _prepare_yuanbao_service_output


class FrozenServiceBootstrapTests(unittest.TestCase):
    def test_windowed_service_restores_both_output_streams_to_log(self) -> None:
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        stream = None
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                log_path = Path(temp_dir) / "service.log"
                with patch.dict(
                    os.environ,
                    {"AEMEATH_YUANBAO_BOOT_LOG": str(log_path)},
                    clear=False,
                ):
                    stream = _prepare_yuanbao_service_output()
                    print("service-ready-marker", flush=True)

                self.assertIs(sys.stdout, stream)
                self.assertIs(sys.stderr, stream)
                stream.close()
                stream = None
                text = log_path.read_text(encoding="utf-8")

            self.assertIn("YuanBao local service boot", text)
            self.assertIn("service-ready-marker", text)
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            if stream is not None:
                stream.close()


if __name__ == "__main__":
    unittest.main()
