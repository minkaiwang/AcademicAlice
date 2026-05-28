#!/usr/bin/env python3
"""检查仓库中是否残留旧产品名（学术爱丽丝 / Alice 等）。发布前可运行：py -3 scripts/check_brand_strings.py"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (pattern, human hint)
FORBIDDEN: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"学术爱丽丝"), "应使用「爱弥斯」"),
    (re.compile(r"爱丽丝科研工作台"), "应使用「爱弥斯科研工作台」"),
    (re.compile(r"\bAcademicAlice\b"), "仓库已更名为 AemeathDeskPet；GITHUB_REPO 或历史说明除外"),
    (re.compile(r"\bAcademic Alice\b"), "应使用 Aemeath / 爱弥斯"),
]

SKIP_DIRS = {".git", "dist", "build", "__pycache__", ".cursor", "node_modules", "services"}
SKIP_FILES = {
    "check_brand_strings.py",
    "package_release.py",
}
# 行内包含以下子串时跳过（迁移 id、文档中「勿用旧名」等说明）
ALLOW_LINE_SUBSTR = (
    "alice-pink",
    "勿用旧名",
    "勿使用",
    "旧名「",
)

TEXT_SUFFIXES = {".py", ".md", ".txt", ".html", ".bat", ".spec", ".json", ".yml", ".yaml"}


def _should_scan(path: Path) -> bool:
    if path.name in SKIP_FILES:
        return False
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    return not any(part in SKIP_DIRS for part in path.parts)


def main() -> int:
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or not _should_scan(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        for i, line in enumerate(text.splitlines(), 1):
            if any(s in line for s in ALLOW_LINE_SUBSTR):
                continue
            for pat, hint in FORBIDDEN:
                if pat.search(line):
                    hits.append(f"{rel}:{i}: {line.strip()[:120]}  ({hint})")
    if hits:
        print("发现旧品牌字符串：", file=sys.stderr)
        for h in hits:
            print(h, file=sys.stderr)
        return 1
    print("check_brand_strings: OK（未发现禁止字符串）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
