"""Reading Exiled Bot's own run log — the only evidence the bot ever used our file.

Everything else this app reports is about what it WROTE. These lines are what
the bot says it LOADED and PICKED UP, so the parsing has to stay exact: the
drift check compares the bot's rule count against our own "active" count, and
those two numbers were verified equal on a real install (a regenerate from
3452 to 3444 rules showed up in the log as exactly that switch).
"""
from __future__ import annotations

from exilebot_pickit.webui import api as webapi

LOG = """\
2026-07-28 05:43:12 [info] -> pickit.ini file loaded from C:\\Bot\\Configuration\\default\\pickit.ini
2026-07-28 05:43:12 [info] -> Loaded 3452 pickit rules from poe1_pickit.ipd
2026-07-28 05:43:12 [info] -> Loaded 10 map rules from poe1_pickit_maps.ipd
2026-07-28 05:44:21 [info] -> Picking item: Jeweller's Orb
2026-07-28 05:44:25 [info] -> Running state: exploring
2026-07-28 05:44:31 [info] -> Picking item: Portal Scroll
2026-07-28 05:44:33 [info] -> Picking item: Portal Scroll
2026-07-28 05:45:02 [info] -> Selling item...
2026-07-28 05:56:05 [info] -> Loaded 3444 pickit rules from poe1_pickit.ipd
2026-07-28 05:56:05 [info] -> Loaded 10 map rules from poe1_pickit_maps.ipd
2026-07-28 05:57:00 [info] -> Picking item: Orb of Chance
"""


class _Api(webapi.AppApi):
    """Only the log reader: no config file, no bot scan, no webview."""

    def __init__(self, root, active=0, output_base="poe1_pickit", game="poe1"):
        self.cfg = {"output_base": output_base, "active_game": game,
                    "games": {game: {"history": ([{"active": active}] if active else [])}}}
        self._root = str(root)
        self.logs = []

    def bot_log_path(self):
        p = f"{self._root}/Log/lastrun.log"
        import os
        return p if os.path.isfile(p) else ""

    def _log(self, m):
        self.logs.append(m)


def _bot(tmp_path, text=LOG):
    (tmp_path / "Log").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Log" / "lastrun.log").write_text(text, encoding="utf-8")
    return tmp_path


def test_reads_the_latest_load_of_each_kind(tmp_path):
    i = _Api(_bot(tmp_path), active=3444).bot_log_info()
    assert i["found"]
    assert i["pickit"] == {"ts": "2026-07-28 05:56", "n": 3444,
                           "kind": "pickit", "file": "poe1_pickit.ipd"}
    assert i["maps"]["n"] == 10, "the map runner load is reported separately"


def test_counts_pickups_and_sales(tmp_path):
    i = _Api(_bot(tmp_path), active=3444).bot_log_info()
    assert i["pickup_total"] == 4
    assert i["sold"] == 1
    top = i["pickups"][0]
    assert (top["name"], top["n"]) == ("Portal Scroll", 2), "sorted by count"
    # each row also carries art + a price for the UI; unknown names get neither
    assert "icon" in top and "ex" in top
    assert ("Jeweller's Orb", 1) in [(r["name"], r["n"]) for r in i["pickups"]],         "apostrophes survive"


def test_drift_ok_when_the_counts_agree(tmp_path):
    i = _Api(_bot(tmp_path), active=3444).bot_log_info()
    assert i["drift"] == "ok"
    assert i["ours"] == 3444 and i["pickit"]["n"] == 3444


def test_drift_stale_when_we_wrote_a_different_number(tmp_path):
    """The real case: regenerate, but the bot has not reloaded yet."""
    i = _Api(_bot(tmp_path), active=3600).bot_log_info()
    assert i["drift"] == "stale"
    # the raw numbers cross the bridge; the UI formats them so the thousands
    # separator matches the tiles sitting right under the sentence
    assert i["pickit"]["n"] == 3444 and i["ours"] == 3600


def test_drift_other_when_the_bot_loads_someone_elses_file(tmp_path):
    i = _Api(_bot(tmp_path), active=3444, output_base="my_pickit").bot_log_info()
    assert i["drift"] == "other"
    assert i["pickit"]["file"] == "poe1_pickit.ipd"
    assert i["want_file"] == "my_pickit.ipd"


def test_drift_unknown_before_the_first_generate(tmp_path):
    i = _Api(_bot(tmp_path), active=0).bot_log_info()
    assert i["drift"] == "unknown"


def test_no_pickit_load_in_the_session(tmp_path):
    i = _Api(_bot(tmp_path, "2026-07-28 05:43:12 [info] -> Running state: idle\n"),
             active=3444).bot_log_info()
    assert i["drift"] == "none"
    assert i["pickup_total"] == 0


def test_a_missing_log_is_a_blank_panel_not_an_error(tmp_path):
    i = _Api(tmp_path, active=3444).bot_log_info()
    assert i["found"] is False
    assert i["pickups"] == [] and i["drift"] == "unknown"


def test_survives_a_binary_or_truncated_log(tmp_path):
    """errors='replace' keeps a corrupt tail from taking the whole panel down."""
    p = _bot(tmp_path)
    (p / "Log" / "lastrun.log").write_bytes(
        LOG.encode("utf-8") + b"\xff\xfe garbage \x00\x01\n")
    i = _Api(p, active=3444).bot_log_info()
    assert i["drift"] == "ok" and i["pickup_total"] == 4
