"""Source files must not contain invisible control characters.

A stray control character is the one class of corruption that survives every
other gate: ruff parses it, `node --check` parses it, grep prints it as if the
line were fine, and the editor shows nothing. It reached a shipped regex once —
a scripted edit turned the two characters ``\\b`` into a literal backspace
(0x08), so ``re.compile(r"\\bMap ...")`` silently matched nothing and the map
rules it guarded stopped working. The file looked perfect in every tool.

Tab, newline and carriage return are the only control characters allowed.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECKED_SUFFIXES = {".py", ".html", ".json", ".mjs", ".md", ".yml", ".yaml", ".txt"}
SKIP_DIRS = {".git", "build", "dist", "__pycache__", ".pytest_cache", ".ruff_cache",
             "node_modules", ".build-venv", "docs"}
ALLOWED = {0x09, 0x0A, 0x0D}          # tab, LF, CR


def _files():
    for path in ROOT.rglob("*"):
        if path.suffix.lower() not in CHECKED_SUFFIXES or not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        yield path


def test_no_control_characters_in_source():
    offenders = []
    for path in _files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue                   # binary or unreadable: not our business
        for lineno, line in enumerate(text.splitlines(), 1):
            for ch in line:
                code = ord(ch)
                if code < 0x20 and code not in ALLOWED:
                    offenders.append(
                        f"{path.relative_to(ROOT)}:{lineno} contains "
                        f"U+{code:04X} — likely a mangled escape (\\b, \\v, \\f)")
                    break
    assert not offenders, "control characters found:\n  " + "\n  ".join(offenders)


def test_the_guard_would_actually_catch_one(tmp_path):
    """Guard the guard: a file with a backspace must be rejected."""
    bad = tmp_path / "bad.py"
    bad.write_text('X = re.compile(r"\x08Map")\n', encoding="utf-8")
    text = bad.read_text(encoding="utf-8")
    hits = [c for c in text if ord(c) < 0x20 and ord(c) not in ALLOWED]
    assert hits, "the detection logic itself is broken"
