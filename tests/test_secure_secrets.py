from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config.secure_secrets import (
    load_ai_secrets,
    migrate_legacy_config_secrets,
    save_ai_secrets,
)
from lib.script.ui.ai_settings_storage import save_ai_values


@unittest.skipUnless(sys.platform == "win32", "Windows DPAPI only")
class SecureSecretsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._temp_dir.name)
        self.secret_path = self.root / "secrets" / "ai_credentials.dpapi"

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def test_dpapi_round_trip_does_not_store_plaintext(self) -> None:
        values = {
            "api_key": "api-secret-sentinel",
            "yuanbao_x_uskey": "yuanbao-secret-sentinel",
        }

        save_ai_secrets(values, secret_path=self.secret_path)
        loaded = load_ai_secrets(secret_path=self.secret_path)
        encrypted = self.secret_path.read_bytes()

        self.assertEqual(values, loaded)
        self.assertNotIn(b"api-secret-sentinel", encrypted)
        self.assertNotIn(b"yuanbao-secret-sentinel", encrypted)

    def test_legacy_plaintext_is_migrated_and_scrubbed(self) -> None:
        legacy_text = (
            "API_KEY = 'legacy-api-secret'\n"
            "YUANBAO_FREE_API = {\n"
            "    'x_uskey': 'legacy-yuanbao-secret',\n"
            "    'enabled': True,\n"
            "}\n"
        )
        project_path = self.root / "project" / "ollama_config.py"
        shared_path = self.root / "shared" / "ollama_config.py"
        project_path.parent.mkdir(parents=True)
        shared_path.parent.mkdir(parents=True)
        project_path.write_text(legacy_text, encoding="utf-8")
        shared_path.write_text(legacy_text, encoding="utf-8")

        migrated = migrate_legacy_config_secrets(
            project_config_path=project_path,
            shared_config_path=shared_path,
            secret_path=self.secret_path,
        )

        self.assertEqual("legacy-api-secret", migrated["api_key"])
        self.assertEqual(
            "legacy-yuanbao-secret",
            migrated["yuanbao_x_uskey"],
        )
        for path in (project_path, shared_path):
            sanitized = path.read_text(encoding="utf-8")
            self.assertNotIn("legacy-api-secret", sanitized)
            self.assertNotIn("legacy-yuanbao-secret", sanitized)
        self.assertEqual(
            migrated,
            load_ai_secrets(secret_path=self.secret_path),
        )

    def test_settings_save_keeps_secret_out_of_python_config(self) -> None:
        config_path = self.root / "ollama_config.py"
        source_path = Path(__file__).resolve().parents[1] / "config" / "ollama_config.py"
        config_path.write_text(
            source_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        values = {
            "api_key": "do-not-write-this-api-key",
            "force_reply_mode": "0",
            "api_base_url": "https://example.test/v1",
            "api_model": "test-model",
            "yuanbao_free_api_enabled": False,
            "yuanbao_login_url": "https://example.test/login",
            "yuanbao_hy_source": "web",
            "yuanbao_hy_user": "",
            "yuanbao_x_uskey": "do-not-write-this-uskey",
            "yuanbao_agent_id": "agent",
            "yuanbao_chat_id": "",
            "yuanbao_remove_conversation": False,
            "yuanbao_upload_images": True,
            "ollama_base_url": "http://localhost:11434",
            "ollama_model": "qwen2.5",
            "num_gpu": -1,
            "num_thread": 0,
            "api_temperature": 0.8,
            "gsv_temperature": 1.35,
            "gsv_speed_factor": 1.0,
            "ai_voice_max_chars": 40,
            "memory_context_limit": 12,
            "api_enable_thinking": False,
            "auto_companion_enabled": True,
        }

        with (
            patch(
                "lib.script.ui.ai_settings_storage._ollama_config_path",
                return_value=config_path,
            ),
            patch(
                "lib.script.ui.ai_settings_storage.save_ai_secrets"
            ) as secure_save,
            patch(
                "lib.script.ui.ai_settings_storage._mirror_config_text_to_shared"
            ),
        ):
            save_ai_values(values, {"memory_context_limit": 12})

        secure_save.assert_called_once()
        output = config_path.read_text(encoding="utf-8")
        self.assertNotIn("do-not-write-this-api-key", output)
        self.assertNotIn("do-not-write-this-uskey", output)
        self.assertIn("API_KEY = ''", output)
        self.assertIn("'x_uskey': ''", output)

    def test_settings_save_with_blank_secrets_removes_encrypted_file(self) -> None:
        config_path = self.root / "ollama_config.py"
        source_path = (
            Path(__file__).resolve().parents[1]
            / "config"
            / "ollama_config.py"
        )
        config_path.write_text(
            source_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        values = {
            "api_key": "",
            "force_reply_mode": "0",
            "api_base_url": "https://example.test/v1",
            "api_model": "test-model",
            "yuanbao_free_api_enabled": False,
            "yuanbao_login_url": "https://example.test/login",
            "yuanbao_hy_source": "web",
            "yuanbao_hy_user": "",
            "yuanbao_x_uskey": "",
            "yuanbao_agent_id": "agent",
            "yuanbao_chat_id": "",
            "yuanbao_remove_conversation": False,
            "yuanbao_upload_images": True,
            "ollama_base_url": "http://localhost:11434",
            "ollama_model": "qwen2.5",
            "num_gpu": -1,
            "num_thread": 0,
            "api_temperature": 0.8,
            "gsv_temperature": 1.35,
            "gsv_speed_factor": 1.0,
            "ai_voice_max_chars": 40,
            "memory_context_limit": 12,
            "api_enable_thinking": False,
            "auto_companion_enabled": True,
        }

        with (
            patch(
                "lib.script.ui.ai_settings_storage._ollama_config_path",
                return_value=config_path,
            ),
            patch(
                "lib.script.ui.ai_settings_storage.clear_ai_secrets"
            ) as secure_clear,
            patch(
                "lib.script.ui.ai_settings_storage.save_ai_secrets"
            ) as secure_save,
            patch(
                "lib.script.ui.ai_settings_storage._mirror_config_text_to_shared"
            ),
        ):
            save_ai_values(values, {"memory_context_limit": 12})

        secure_clear.assert_called_once_with()
        secure_save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
