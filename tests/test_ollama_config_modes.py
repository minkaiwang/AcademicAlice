from __future__ import annotations

import unittest
from unittest.mock import patch

import config.ollama_config as ollama_config


class OllamaConfigModeTests(unittest.TestCase):
    def test_disabled_yuanbao_preference_falls_back_to_local_ollama(self) -> None:
        with (
            patch.object(ollama_config, "FORCE_REPLY_MODE", "4"),
            patch.object(ollama_config, "API_KEY", ""),
            patch.object(ollama_config, "_ENV_API_KEY", ""),
            patch.object(
                ollama_config,
                "YUANBAO_FREE_API",
                {"enabled": False, "agent_id": "agent"},
            ),
        ):
            active = ollama_config.get_active_config()

        self.assertEqual("ollama", active["api_type"])
        self.assertEqual("", active["force_mode"])

    def test_enabled_but_incomplete_yuanbao_configuration_is_explicit_error(
        self,
    ) -> None:
        with (
            patch.object(ollama_config, "FORCE_REPLY_MODE", "4"),
            patch.object(ollama_config, "API_KEY", ""),
            patch.object(ollama_config, "_ENV_API_KEY", ""),
            patch.object(
                ollama_config,
                "YUANBAO_FREE_API",
                {"enabled": True, "agent_id": "agent"},
            ),
        ):
            active = ollama_config.get_active_config()

        self.assertEqual("error", active["api_type"])
        self.assertTrue(active["strict_mode"])


if __name__ == "__main__":
    unittest.main()
