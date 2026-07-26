from __future__ import annotations

import ast
import unittest
from pathlib import Path

from config.config_runtime import SECURITY
from lib.core.cmd_center import _shell_command_argv


ROOT = Path(__file__).resolve().parents[1]


class SecurityContractTests(unittest.TestCase):
    def test_shell_commands_are_disabled_by_default(self) -> None:
        self.assertIs(False, SECURITY["enable_shell_commands"])
        argv = _shell_command_argv("echo test")
        self.assertIsInstance(argv, list)
        self.assertIn("echo test", argv)
        source = (ROOT / "lib" / "core" / "cmd_center.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("shell=True", source)

    def test_installer_has_no_floating_yuanbao_download(self) -> None:
        source = (ROOT / "install" / "install_deps.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("refs/heads/main", source)
        self.assertNotIn("yuanbao-free-api-main.zip", source)

    def test_normal_shutdown_does_not_schedule_os_exit(self) -> None:
        source_path = ROOT / "lib" / "script" / "main.py"
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        shutdown_step_literals: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not any(
                isinstance(target, ast.Attribute)
                and target.attr == "_shutdown_steps"
                for target in node.targets
            ):
                continue
            shutdown_step_literals.extend(
                child.value
                for child in ast.walk(node.value)
                if isinstance(child, ast.Constant)
                and isinstance(child.value, str)
            )
        self.assertIn("quit_application", shutdown_step_literals)
        self.assertNotIn("force_quit_application", shutdown_step_literals)
        self.assertIn("aemeath-exit-watchdog", source)

    def test_hidden_yuanbao_credentials_are_preserved_on_settings_save(
        self,
    ) -> None:
        source = (
            ROOT / "lib" / "script" / "ui" / "ai_settings_panel.py"
        ).read_text(encoding="utf-8")
        collect_section = source.split(
            "    def _collect_values", 1
        )[1].split("    def _set_values_to_form", 1)[0]
        self.assertIn(
            '"yuanbao_x_uskey": str(self._yuanbao_x_uskey_value',
            collect_section,
        )
        self.assertIn(
            'self._yuanbao_x_uskey_value = str(values.get(',
            source,
        )
        self.assertNotIn('"yuanbao_x_uskey": "",', collect_section)

    def test_yuanbao_routes_do_not_return_exception_details(self) -> None:
        for relative in (
            Path("services/yuanbao-free-api/src/routers/chat.py"),
            Path("services/yuanbao-free-api/src/routers/upload.py"),
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("detail=str(e)", source)
            self.assertIn('detail="internal service error"', source)

    def test_yuanbao_control_api_is_local_and_authenticated(self) -> None:
        app_source = (
            ROOT / "services" / "yuanbao-free-api" / "app.py"
        ).read_text(encoding="utf-8")
        auth_source = (
            ROOT
            / "services"
            / "yuanbao-free-api"
            / "src"
            / "dependencies"
            / "auth.py"
        ).read_text(encoding="utf-8")
        qr_source = (
            ROOT
            / "services"
            / "yuanbao-free-api"
            / "src"
            / "utils"
            / "qr_utils.py"
        ).read_text(encoding="utf-8")
        for function_name in ("fsv_status", "fsv_login", "fsv_logout"):
            definition = next(
                line.strip()
                for line in app_source.splitlines()
                if line.startswith(f"async def {function_name}(")
            )
            self.assertIn("Depends(require_api_key)", definition)
        self.assertIn('host="127.0.0.1"', app_source)
        self.assertNotIn('host="0.0.0.0"', app_source)
        self.assertIn("secrets.compare_digest", (
            ROOT
            / "services"
            / "yuanbao-free-api"
            / "src"
            / "config.py"
        ).read_text(encoding="utf-8"))
        self.assertIn("def require_api_key", auth_source)
        self.assertNotIn("QR content:", qr_source)

    def test_frozen_build_has_a_yuanbao_service_entrypoint(self) -> None:
        launcher_source = (
            ROOT / "lib" / "core" / "qt_desktop_pet.py"
        ).read_text(encoding="utf-8")
        spec_source = (
            ROOT / "install" / "deskpet.spec"
        ).read_text(encoding="utf-8")
        self.assertIn("'--yuanbao-service'", launcher_source)
        self.assertIn("uvicorn.run(", launcher_source)
        self.assertIn('"yuanbao-free-api"', spec_source)
        self.assertIn("_filtered_data_tree(", spec_source)
        self.assertIn('collect_submodules("playwright")', spec_source)


if __name__ == "__main__":
    unittest.main()
