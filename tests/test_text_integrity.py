from __future__ import annotations

import re
import unittest
from pathlib import Path

from lib.script.music.providers.netease_provider import NetEaseMusicProvider


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = ("config", "install", "lib", "scripts", "services")
MOJIBAKE_FRAGMENTS = (
    "鎭㈠",
    "浜岀淮",
    "鏈煡",
    "妫€娴",
    "浠呭",
    "鍏辩敤",
    "缁熶竴鎺",
)


class TextIntegrityTests(unittest.TestCase):
    def test_python_sources_have_no_known_mojibake_fragments(self) -> None:
        findings: list[str] = []
        for source_root in SOURCE_ROOTS:
            for path in (ROOT / source_root).rglob("*.py"):
                if "__pycache__" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8")
                for fragment in MOJIBAKE_FRAGMENTS:
                    if fragment in text:
                        findings.append(
                            f"{path.relative_to(ROOT).as_posix()}: {fragment}"
                        )
                if re.search(r"\?{3,}", text):
                    findings.append(
                        f"{path.relative_to(ROOT).as_posix()}: repeated ?"
                    )
        self.assertEqual([], findings)

    def test_netease_missing_title_uses_readable_fallback(self) -> None:
        track = NetEaseMusicProvider()._song_to_track(
            {"id": 1, "ar": [{"name": "测试歌手"}], "dt": 1000}
        )
        self.assertIsNotNone(track)
        self.assertEqual("未知歌曲", track.title)
        self.assertIn("未知歌曲", track.display)


if __name__ == "__main__":
    unittest.main()
