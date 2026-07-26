from __future__ import annotations

import importlib
import os
import unittest
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / "lib" / "script"


class PluginDiscoveryTests(unittest.TestCase):
    def test_all_manager_and_particle_modules_import(self) -> None:
        module_names = [
            f"lib.script.{path.parent.name}.manager"
            for path in sorted(SCRIPT_ROOT.glob("obj-*/manager.py"))
        ]
        module_names.extend(
            f"lib.script.practical.{path.stem}"
            for path in sorted(
                (SCRIPT_ROOT / "practical").glob("*_particle.py")
            )
        )
        self.assertTrue(module_names)

        failures: list[str] = []
        for module_name in module_names:
            try:
                importlib.import_module(module_name)
            except Exception as exc:
                failures.append(
                    f"{module_name}: {type(exc).__name__}: {exc}"
                )
        self.assertEqual([], failures)

        from lib.core.plugin_registry import (
            manager_registry,
            particle_registry,
        )

        expected_manager_count = len(
            list(SCRIPT_ROOT.glob("obj-*/manager.py"))
        )
        self.assertEqual(
            expected_manager_count,
            len(manager_registry.get_all_ids()),
        )
        self.assertTrue(particle_registry.get_all_ids())


if __name__ == "__main__":
    unittest.main()
