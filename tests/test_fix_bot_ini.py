"""The Maps page's "fix these for me" button edits somebody else's config.ini.

That file belongs to the user's bot install, not to us, so the bar is: change
exactly the two keys asked for and leave every other byte alone. These tests
pin that down — comments, ordering, unknown sections, line endings and even
non-UTF-8 bytes must come back out unchanged.
"""
from __future__ import annotations

import os

import pytest

from exilebot_pickit.webui import api as webapi


class _Api(webapi.AppApi):
    """Just the ini editor: no config file, no bot scan, no webview."""

    def __init__(self, maps_dir, output_base="poe1_pickit"):
        self.cfg = {"output_base": output_base}
        self._maps_dir = str(maps_dir)
        self.logs = []

    def maps_folder(self):
        return {"found": True, "path": self._maps_dir, "files": [], "profile": "default"}

    def _log(self, msg):
        self.logs.append(msg)


FULL = (
    "; Exiled Bot configuration\n"
    "\n"
    "[general]\n"
    "; how long to wait\n"
    "timeout=30\n"
    "\n"
    "[stashing]\n"
    "map_store_stash_tabs=1,2,3\n"
    "; Enable automatic map upgrading.\n"
    "enable_map_tier_upgrading=false\n"
    "minimum_map_number_to_upgrade_tier=3\n"
    "\n"
    "[profile]\n"
    "; Sets which map profile should be used\n"
    "map_profile=default\n"
)


@pytest.fixture()
def bot(tmp_path):
    """A bot install laid out the way the real one is: Configuration/<p>/{Maps,Pickit}."""
    prof = tmp_path / "Configuration" / "default"
    (prof / "Maps").mkdir(parents=True)
    return prof


def _write(bot, text, encoding="latin-1"):
    (bot / "config.ini").write_bytes(text.encode(encoding))
    return bot / "config.ini"


def _read(bot):
    return (bot / "config.ini").read_bytes().decode("latin-1")


def test_rewrites_both_keys_in_place(bot):
    _write(bot, FULL)
    res = _Api(bot / "Maps").fix_bot_ini()
    assert res.get("ok"), res
    out = _read(bot)
    assert "enable_map_tier_upgrading=true\n" in out
    assert "map_profile=poe1_pickit_maps\n" in out
    assert sorted(res["changed"]) == ["enable_map_tier_upgrading=true",
                                      "map_profile=poe1_pickit_maps"]


def test_touches_nothing_else(bot):
    """Every other line must survive byte for byte, in its original order."""
    _write(bot, FULL)
    _Api(bot / "Maps").fix_bot_ini()
    before = [ln for ln in FULL.splitlines()
              if not ln.startswith(("enable_map_tier_upgrading", "map_profile"))]
    after = [ln for ln in _read(bot).splitlines()
             if not ln.startswith(("enable_map_tier_upgrading", "map_profile"))]
    assert before == after


def test_is_idempotent(bot):
    _write(bot, FULL)
    api = _Api(bot / "Maps")
    api.fix_bot_ini()
    once = _read(bot)
    second = api.fix_bot_ini()
    assert second["changed"] == []
    assert _read(bot) == once, "a second run must be a no-op"


def test_adds_a_missing_key_inside_its_own_section(bot):
    _write(bot, FULL.replace("enable_map_tier_upgrading=false\n", ""))
    _Api(bot / "Maps").fix_bot_ini()
    lines = _read(bot).splitlines()
    i = lines.index("enable_map_tier_upgrading=true")
    # inside [stashing]: the nearest header above it is that one, and it is not
    # left orphaned against the next section header
    above = [ln for ln in lines[:i] if ln.startswith("[")]
    assert above[-1] == "[stashing]"
    assert lines[i - 1].strip(), "should sit with its block, not after a blank line"


def test_creates_a_missing_section(bot):
    _write(bot, "[general]\ntimeout=30\n")
    res = _Api(bot / "Maps").fix_bot_ini()
    assert res.get("ok"), res
    out = _read(bot)
    assert "[profile]" in out and "map_profile=poe1_pickit_maps" in out
    assert "[stashing]" in out and "enable_map_tier_upgrading=true" in out
    assert out.startswith("[general]\ntimeout=30\n")


def test_preserves_crlf(bot):
    _write(bot, FULL.replace("\n", "\r\n"))
    _Api(bot / "Maps").fix_bot_ini()
    out = _read(bot)
    assert "\r\n" in out
    assert "\n" not in out.replace("\r\n", ""), "must not leave a bare LF behind"


def test_preserves_non_utf8_bytes(bot):
    """errors='replace' would turn these into U+FFFD and write the damage back."""
    text = FULL + "; caf\xe9 \xff\xfe comment\n"
    _write(bot, text)
    _Api(bot / "Maps").fix_bot_ini()
    assert "; caf\xe9 \xff\xfe comment" in _read(bot)


def test_ignores_a_commented_out_key(bot):
    _write(bot, FULL.replace("map_profile=default", ";map_profile=default"))
    _Api(bot / "Maps").fix_bot_ini()
    out = _read(bot)
    assert ";map_profile=default" in out, "the comment must be left as it was"
    assert "\nmap_profile=poe1_pickit_maps" in out


def test_backs_the_original_up(bot):
    _write(bot, FULL)
    _Api(bot / "Maps").fix_bot_ini()
    baks = [f for f in os.listdir(bot) if f.startswith("config.ini.bak-")]
    assert len(baks) == 1
    assert (bot / baks[0]).read_bytes().decode("latin-1") == FULL


def test_uses_the_configured_output_name(bot):
    _write(bot, FULL)
    _Api(bot / "Maps", output_base="my_pickit").fix_bot_ini()
    assert "map_profile=my_pickit_maps" in _read(bot)


def test_reports_a_missing_file_instead_of_creating_one(bot):
    res = _Api(bot / "Maps").fix_bot_ini()
    assert res.get("error") and "config.ini" in res["error"]
    assert not (bot / "config.ini").exists()


def test_reports_a_missing_bot_folder(tmp_path):
    api = _Api(tmp_path / "Maps")
    api.maps_folder = lambda: {"found": False, "path": "", "files": [], "profile": ""}
    assert "error" in api.fix_bot_ini()
