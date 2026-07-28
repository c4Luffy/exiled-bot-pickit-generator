"""Rebuild version.py's HIGHLIGHTS from the CHANGELOG: current release + one prior.

The in-app "What's new" grew by one section per release and was never pruned —
53,320 characters and 63 "Also in" blocks back to v4.38.0, all shipped inside
the exe and rendered into one dialog. Its ordering had also drifted (4.48.4
listed above 4.50.0), because each release prepended by hand.

Generating it from the CHANGELOG makes it correct by construction and caps it
at two updates, which is what the dialog is for.
"""
from __future__ import annotations

import re

MAX_ENTRIES = 2


def _entries(changelog: str):
    """[(version, title, [bullet, ...]), ...] newest first."""
    heads = list(re.finditer(r"(?m)^## \[v([\d.]+)\][^\n]*?\u2014 ([^\n]+)$", changelog))
    out = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(changelog)
        body = changelog[m.end():end]
        bullets = []
        for raw in re.split(r"(?m)^- ", body)[1:]:
            # unwrap the hard-wrapped markdown, drop its emphasis/code marks
            text = " ".join(line.strip() for line in raw.strip().splitlines())
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            text = re.sub(r"\*(.+?)\*", r"\1", text)
            text = re.sub(r"`(.+?)`", r"\1", text)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                bullets.append(text)
        out.append((m.group(1), m.group(2).strip(), bullets))
    return out


def build(changelog: str, version: str) -> str:
    entries = _entries(changelog)
    # the release being cut may not be in the changelog yet when this runs
    if entries and entries[0][0] != version:
        entries = [e for e in entries if e[0] == version] + \
                  [e for e in entries if e[0] != version]
    parts = []
    for n, (ver, _title, bullets) in enumerate(entries[:MAX_ENTRIES]):
        if n:
            parts.append(f"Also in {ver}:")
        parts.extend(f"\u2022 {b}" for b in bullets)
    text = "\n\n".join(parts).strip() + "\n"
    return re.sub(r"\n{3,}", "\n\n", text)      # bullets must not drift apart


if __name__ == "__main__":
    import pathlib
    root = pathlib.Path(r"c:\Users\C4Luffy\Downloads\exiled-bot-pickit-generator")
    vp = root / "src" / "exilebot_pickit" / "version.py"
    src = vp.read_text(encoding="utf-8")
    version = re.search(r'VERSION = "([^"]+)"', src).group(1)
    new = build((root / "CHANGELOG.md").read_text(encoding="utf-8"), version)
    out, n = re.subn(r'(?s)HIGHLIGHTS = """\\\n.*?"""',
                     'HIGHLIGHTS = """\\\n' + new + '"""', src, count=1)
    if n != 1:
        raise SystemExit(f"expected one HIGHLIGHTS block, replaced {n}")
    vp.write_text(out, encoding="utf-8", newline="\n")
    print(f"HIGHLIGHTS rebuilt: {len(src)} -> {len(out)} chars")
    print(new[:700])
