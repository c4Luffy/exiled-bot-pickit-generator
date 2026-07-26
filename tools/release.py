#!/usr/bin/env python3
"""One-command release: gate -> bump version.py -> commit -> tag -> push -> notes.

Cuts the manual 7-step dance down to one command, and closes the two footguns that have
actually bitten this project:
  * version.py != tag  -> the release workflow hard-fails ("Version mismatch").
  * tagging a build that never passed the gates -> a broken exe ships (v4.22.0 did).

The script writes version.py FROM the version you pass and tags v<that>, so they can't
disagree; and it runs every gate BEFORE it touches git, aborting on the first failure.

Usage:
  python tools/release.py 4.34.0 -m "subject line for the commit" --notes NOTES.md
  python tools/release.py 4.34.0 -m "subject" --notes NOTES.md --dry-run   # gates only, no writes

Prerequisites: your code + CHANGELOG changes for this version are already in the working
tree (the script bumps version.py, commits everything, tags, and pushes). `gh` must be
authenticated for the notes/latest step; without it the release still publishes via CI —
you just set notes by hand.
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys
from pathlib import Path

# The Windows console defaults to cp1252, which can't encode the status glyphs below and
# would crash the tool mid-run. Force UTF-8 output where the runtime supports it.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "src" / "exilebot_pickit" / "version.py"
CHANGELOG = ROOT / "CHANGELOG.md"
SITE = ROOT / "docs" / "index.html"

GATES = [
    ("tests", [sys.executable, "-m", "pytest", "-q"]),
    ("lint", [sys.executable, "-m", "ruff", "check", "."]),
    ("ui gate", [sys.executable, "tools/check_ui.py"]),
    ("ui logic", ["node", "tests/test_ui_logic.mjs"]),
    ("site carousel", ["node", "tests/test_site_carousel.mjs"]),
]


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, **kw)


def sync_site(tag: str, apply: bool = True) -> list[str]:
    """Point the GitHub Pages site at this release.

    Nothing used to update docs/index.html, so every release left the landing
    page advertising (and linking the .exe of) an older version — it sat on
    v4.42.0 while v4.42.4 was out, so every Download button served a stale
    build. Only the mechanical spots are rewritten: download links always point
    at the current release, as do the "Download vX.Y.Z" labels and the two
    "current release" markers. Prose (the release-notes list) is left alone and
    warned about instead, because it can't be generated.
    """
    if not SITE.exists():
        return []
    html = SITE.read_text(encoding="utf-8")
    today = datetime.date.today().strftime("%-d %B %Y") if os.name != "nt" \
        else datetime.date.today().strftime("%d %B %Y").lstrip("0")
    # NB: `releases/tag/` links are deliberately NOT rewritten. Each entry in the
    # release-list links its OWN tag, and a blanket rewrite repointed all nine of
    # them at the newest release.
    subs = [
        (r"(releases/download/)v\d+\.\d+\.\d+(/)", rf"\g<1>{tag}\g<2>"),
        (r"Download v\d+\.\d+\.\d+", f"Download {tag}"),
        (r"(Current release &middot; |Current release · )v\d+\.\d+\.\d+",
         rf"\g<1>{tag}"),
        (r'(class="release-version">)v\d+\.\d+\.\d+', rf"\g<1>{tag}"),
        (r"(<small>Current release (?:&middot;|·) )[^<]*(</small>)", rf"\g<1>{today}\g<2>"),
        (r"(download v)\d+\.\d+\.\d+", rf"\g<1>{tag[1:]}"),
    ]
    changed = []
    for pattern, repl in subs:
        html, n = re.subn(pattern, repl, html)
        if n:
            changed.append(f"{pattern} ×{n}")
    if apply and changed:
        SITE.write_text(html, encoding="utf-8", newline="\n")
    return changed


def check_site_notes(tag: str) -> None:
    """The site's release panel leads with a hand-written entry. Warn when it
    doesn't mention this version — that's how the panel ended up describing
    v4.41.29's fix under a v4.42.0 heading."""
    if not SITE.exists():
        return
    html = SITE.read_text(encoding="utf-8")
    head = html.split('<ul class="release-list">', 1)
    if len(head) == 2 and tag not in head[1].split("</li>", 1)[0]:
        print(f"⚠ docs/index.html: the top release-list entry doesn't mention {tag} — "
              "write this release's entry before shipping.")


def die(msg: str) -> None:
    print(f"\n✗ {msg}")
    sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description="One-command release.")
    ap.add_argument("version", help="X.Y.Z (no leading v)")
    ap.add_argument("-m", "--message", required=True, help="commit subject (after 'vX.Y.Z: ')")
    ap.add_argument("--notes", help="path to a markdown file for the release body")
    ap.add_argument("--dry-run", action="store_true",
                    help="run the gates and show the plan; make NO commits/tags/pushes")
    a = ap.parse_args()

    if not re.fullmatch(r"\d+\.\d+\.\d+", a.version):
        die(f"version must be X.Y.Z, got {a.version!r}")
    tag = f"v{a.version}"

    # on main, and the tag doesn't already exist
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                 capture_output=True, text=True).stdout.strip()
    if branch != "main":
        die(f"not on main (on {branch}) — releases cut from main")
    if run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
           capture_output=True).returncode == 0:
        die(f"tag {tag} already exists")

    # Sync with the remote BEFORE the gates, so the gates validate exactly the
    # tree that ships. (This used to happen after the commit, exit code ignored:
    # a remote commit pushed mid-release got folded in UNGATED, and a rebase
    # conflict left the repo mid-rebase with the bump already committed.)
    # --autostash: the working tree legitimately carries this release's changes.
    if run(["git", "pull", "--rebase", "--autostash", "-q",
            "origin", "main"]).returncode != 0:
        die("git pull --rebase failed — resolve (or `git rebase --abort`) and rerun")

    # CHANGELOG must mention this version (soft — warn, don't block)
    if CHANGELOG.exists() and f"[{tag}]" not in CHANGELOG.read_text(encoding="utf-8"):
        print(f"⚠ CHANGELOG has no '## [{tag}]' entry — add it before release.")
    check_site_notes(tag)

    # ── gates, before touching anything ─────────────────────────────────────────
    print(f"Releasing {tag}: running gates first\n")
    for name, cmd in GATES:
        print(f"  … {name}")
        if run(cmd, capture_output=True).returncode != 0:
            # re-run visibly so the failure is on screen
            run(cmd)
            die(f"gate '{name}' failed — nothing tagged, nothing pushed")
    print("  ✓ all gates green\n")

    if a.dry_run:
        print("DRY RUN — would now:")
        print(f"  set version.py = {a.version}")
        for line in sync_site(tag, apply=False):
            print(f"  site: {line}")
        print(f"  git commit -am '{tag}: {a.message}'")
        print(f"  git tag {tag} && git push origin main && git push origin {tag}")
        print("  wait for the release build, then set notes + --latest")
        return 0

    # ── bump, commit, tag, push ─────────────────────────────────────────────────
    # Rewrite ONLY the VERSION line and leave the rest of the file intact — version.py
    # also holds HIGHLIGHTS (the in-app "What's new" text). A full-file rewrite silently
    # dropped HIGHLIGHTS, which imports elsewhere, and the tag shipped with a version.py
    # that failed to import in CI. Replace the line in place instead.
    _src = VERSION_FILE.read_text(encoding="utf-8")
    _new, _n = re.subn(
        r'(?m)^VERSION\s*=\s*["\'].*["\']\s*$', f'VERSION = "{a.version}"', _src)
    if _n != 1:
        die(f"expected exactly one VERSION assignment in version.py, found {_n}")
    VERSION_FILE.write_text(_new, encoding="utf-8", newline="\n")

    for line in sync_site(tag):
        print(f"  site updated: {line}")

    run(["git", "add", "-A"])
    if run(["git", "commit", "-q", "-m", f"{tag}: {a.message}"]).returncode != 0:
        die("git commit failed (nothing to commit?)")
    # No pull here: the sync happened BEFORE the gates. If someone pushed during
    # the gate run, fail loudly rather than tagging code the gates never saw.
    if run(["git", "push", "-q", "origin", "main"]).returncode != 0:
        die("git push failed — remote moved during the release? "
            "rerun (the pre-gate sync will pick the new commits up)")
    run(["git", "tag", tag])
    if run(["git", "push", "-q", "origin", tag]).returncode != 0:
        die(f"pushing tag {tag} failed")
    print(f"✓ pushed {tag} — CI is building the exe")

    # ── wait for the build, set notes + latest ──────────────────────────────────
    if not _have_gh():
        print("gh not available — the release will publish via CI; set notes by hand.")
        return 0
    _wait_and_publish(tag, a.notes)
    return 0


def _have_gh() -> bool:
    try:
        return run(["gh", "auth", "status"], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


def _wait_and_publish(tag: str, notes: str | None) -> None:
    import json
    import time
    print("  waiting for the release build …")
    # Match the run to THIS tag (headBranch == the tag name for tag pushes).
    # Grabbing the newest run used to race: seconds after the push, the newest
    # run is often the PREVIOUS release's finished build — watch returned
    # instantly and the asset check then failed with a bogus "no exe" error.
    rid = None
    for _ in range(30):                        # ~5 min for the run to appear
        out = run(["gh", "run", "list", "--workflow=release.yml", "--limit", "5",
                   "--json", "databaseId,headBranch,status"],
                  capture_output=True, text=True).stdout
        try:
            rid = next((r.get("databaseId") for r in json.loads(out) or []
                        if r.get("headBranch") == tag), None)
        except Exception:
            rid = None
        if rid:
            break
        time.sleep(10)
    if rid:
        if run(["gh", "run", "watch", str(rid), "--exit-status"],
               capture_output=True).returncode != 0:
            die(f"release build FAILED — see `gh run view {rid}`")
    else:
        print(f"  ⚠ never saw a run for {tag} — checking release assets anyway")
    assets = run(["gh", "release", "view", tag, "--json", "assets",
                  "--jq", ".assets[].name"], capture_output=True, text=True).stdout
    if "ExileBot2PickitGenerator.exe" not in assets:
        die(f"release build did not produce the exe — check `gh run view {rid}`")
    print("  ✓ exe + checksums built")
    if notes and Path(notes).exists():
        run(["gh", "release", "edit", tag, "--notes-file", notes, "--latest"])
        print("  ✓ notes set, marked latest")
    else:
        run(["gh", "release", "edit", tag, "--latest"])
        print("  ✓ marked latest (no --notes file given; set the body by hand)")
    print(f"\n✓ {tag} released.")


if __name__ == "__main__":
    sys.exit(main())
