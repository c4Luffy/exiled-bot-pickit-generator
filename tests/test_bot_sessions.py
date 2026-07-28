"""Per-session earnings, because the bot's log cannot remember them.

``lastrun.log`` is overwritten every time the bot starts, so what the previous
session earned is gone the moment the next one begins. The app snapshots the
running session under its start timestamp and updates it in place while it
grows. These tests cover the parts that could quietly go wrong: double-counting
a session, growing the config without bound, mixing the two games together, and
writing the config on every read.
"""
from __future__ import annotations

import exilebot_pickit.generator as gen
from exilebot_pickit.webui import api as webapi


class _Api(webapi.AppApi):
    def __init__(self, game="poe1"):
        self.cfg = {"active_game": game, "bot_sessions": {}}
        self.saves = 0

    def _game(self):
        return gen.get_game(self.cfg.get("active_game"))

    def _log(self, m):
        pass


def _info(sid, picks=10, value=5.0, sold=1, rules=3444, mtime="2026-07-28 07:00",
          priced=True):
    # `priced` mirrors what bot_log_info() reports: whether the price lookup
    # resolved anything at all on this read. It defaults True because that is
    # the normal case; the cold-cache case sets it False explicitly.
    return {"found": True, "session_start": sid, "pickup_total": picks,
            "pickup_value": value, "sold": sold, "mtime": mtime,
            "pickit": {"n": rules}, "priced": priced}


def _patch_save(monkeypatch, api):
    def fake_save(cfg):
        api.saves += 1
        return True
    monkeypatch.setattr(webapi, "save_config", fake_save)


def test_records_the_running_session(monkeypatch):
    api = _Api(); _patch_save(monkeypatch, api)
    rows = api._record_bot_session(_info("2026-07-28 05:43"))
    assert len(rows) == 1
    assert rows[0]["id"] == "2026-07-28 05:43"
    assert rows[0]["value"] == 5.0 and rows[0]["picks"] == 10


def test_the_same_session_updates_in_place(monkeypatch):
    """A session GROWS while the bot runs — it must not become two rows."""
    api = _Api(); _patch_save(monkeypatch, api)
    api._record_bot_session(_info("2026-07-28 05:43", picks=10, value=5.0))
    rows = api._record_bot_session(_info("2026-07-28 05:43", picks=42, value=88.5))
    assert len(rows) == 1, "one session must stay one row"
    assert rows[0]["picks"] == 42 and rows[0]["value"] == 88.5


def test_a_new_session_is_a_new_row(monkeypatch):
    api = _Api(); _patch_save(monkeypatch, api)
    api._record_bot_session(_info("2026-07-28 05:43", value=5.0))
    rows = api._record_bot_session(_info("2026-07-28 09:10", value=7.0))
    assert [r["id"] for r in rows] == ["2026-07-28 05:43", "2026-07-28 09:10"]
    assert sum(r["value"] for r in rows) == 12.0


def test_an_unchanged_session_does_not_rewrite_the_config(monkeypatch):
    """Opening the tab repeatedly must not save on every read."""
    api = _Api(); _patch_save(monkeypatch, api)
    api._record_bot_session(_info("2026-07-28 05:43"))
    assert api.saves == 1
    for _ in range(5):
        api._record_bot_session(_info("2026-07-28 05:43"))
    assert api.saves == 1, "identical data must not trigger a save"


def test_history_is_capped(monkeypatch):
    api = _Api(); _patch_save(monkeypatch, api)
    for n in range(90):
        api._record_bot_session(_info(f"2026-07-{(n % 28) + 1:02d} {n:02d}:00"))
    rows = api.cfg["bot_sessions"]["poe1"]
    assert len(rows) <= 60, f"config would grow without bound: {len(rows)}"


def test_the_two_games_keep_separate_histories(monkeypatch):
    api = _Api("poe1"); _patch_save(monkeypatch, api)
    api._record_bot_session(_info("2026-07-28 05:43", value=5.0))
    api.cfg["active_game"] = "poe2"
    api._record_bot_session(_info("2026-07-28 06:00", value=9.0))
    assert len(api.cfg["bot_sessions"]["poe1"]) == 1
    assert len(api.cfg["bot_sessions"]["poe2"]) == 1
    assert api.cfg["bot_sessions"]["poe2"][0]["value"] == 9.0


def test_a_missing_log_records_nothing(monkeypatch):
    api = _Api(); _patch_save(monkeypatch, api)
    assert api._record_bot_session({"found": False, "session_start": ""}) == []
    assert api.saves == 0


def test_a_session_without_a_timestamp_is_ignored(monkeypatch):
    api = _Api(); _patch_save(monkeypatch, api)
    assert api._record_bot_session(_info("")) == []
    assert api.saves == 0


def test_an_unpriced_read_does_not_erase_recorded_earnings(monkeypatch):
    """The bug this guard exists for.

    The price lookup reads a cache that is empty until the Economy tab or a
    generate has warmed it, so a read taken before then values every pickup at
    0. Writing that over a session that had already been recorded at its real
    worth wiped the number \u2014 observed live: a session recorded at 2.0c came
    back as 0.0c after one cold read.
    """
    api = _Api(); _patch_save(monkeypatch, api)
    api._record_bot_session(_info("2026-07-28 05:43", picks=36, value=2.0))
    rows = api._record_bot_session(
        _info("2026-07-28 05:43", picks=36, value=0.0, priced=False))
    assert rows[0]["value"] == 2.0, "a cold read must not zero real earnings"


def test_a_priced_read_still_updates_the_figure(monkeypatch):
    """The guard must not freeze the value once it is set."""
    api = _Api(); _patch_save(monkeypatch, api)
    api._record_bot_session(_info("2026-07-28 05:43", value=2.0))
    rows = api._record_bot_session(_info("2026-07-28 05:43", value=41.5))
    assert rows[0]["value"] == 41.5
