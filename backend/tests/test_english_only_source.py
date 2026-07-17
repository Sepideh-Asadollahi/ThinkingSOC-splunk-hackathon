"""Prevent non-English Arabic-script copy from entering product source files."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOTS = (
    PROJECT_ROOT / "backend",
    PROJECT_ROOT / "frontend",
    PROJECT_ROOT / "docs",
    PROJECT_ROOT / "install",
    PROJECT_ROOT / "scripts",
    PROJECT_ROOT / "setup_tool",
    PROJECT_ROOT / "submission",
)
TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".env",
    ".example",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
EXCLUDED_PARTS = {
    ".code-review-graph",
    ".next",
    ".venv",
    "__pycache__",
    "artifacts",
    "logs",
    "node_modules",
}
ARABIC_SCRIPT_RANGES = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)


def _contains_arabic_script(text: str) -> bool:
    return any(
        start <= ord(character) <= end
        for character in text
        for start, end in ARABIC_SCRIPT_RANGES
    )


def _source_files() -> list[Path]:
    files: list[Path] = []
    for root in SOURCE_ROOTS:
        for current_root, directories, filenames in os.walk(root):
            directories[:] = [name for name in directories if name not in EXCLUDED_PARTS]
            current_path = Path(current_root)
            files.extend(
                current_path / filename
                for filename in filenames
                if Path(filename).suffix.lower() in TEXT_SUFFIXES
            )
    files.extend(
        path
        for path in (PROJECT_ROOT / "README.md", PROJECT_ROOT / "HACKATHON_CHANGELOG.md")
        if path.is_file()
    )
    return files


def test_product_source_contains_no_arabic_script_copy() -> None:
    violations: list[str] = []
    for path in _source_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if _contains_arabic_script(line):
                violations.append(f"{path.relative_to(PROJECT_ROOT)}:{line_number}")

    assert not violations, "Non-English Arabic-script copy found in:\n" + "\n".join(violations)
