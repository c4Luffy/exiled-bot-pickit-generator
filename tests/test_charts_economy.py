"""Charts must be visible AND switchable, not just written.

They shipped in v4.55.0 as three rules in the .ipd with nowhere in the app to
see or toggle them, because every visible surface is driven by poe.ninja prices
and Charts have none. "No price" is a poor reason for "invisible".
"""
from __future__ import annotations

from exilebot_pickit.generators import assembly as asm
from exilebot_pickit.webui import api as webapi


class _Api(webapi.AppApi):
    def __init__(self, game="poe1", states=None):
        self.cfg = {"active_game": game, "item_states": states or {}}

    def _game(self):
        import exilebot_pickit.generator as gen
        return gen.get_game(self.cfg.get("active_game"))


def test_poe1_gets_a_charts_group():
    groups = _Api("poe1")._ap_groups_for_game()
    assert [k for k, _l, _r in groups] == ["_charts"]
    names = [n for _k, _l, rows in groups for n, _b, _s in rows]
    assert set(names) == set(asm.CHART_BASES)


def test_poe2_is_unaffected():
    keys = [k for k, _l, _r in _Api("poe2")._ap_groups_for_game()]
    assert "_charts" not in keys
    assert keys, "PoE 2 must keep its own always-pick groups"


def test_switching_one_off_comments_out_only_that_rule():
    """The toggle has to reach the written rules, not just the table."""
    snap = {"item_states": {"_charts": {"Coral Reef Chart": {"enabled": False}}},
            "cat_thresh": {}, "poe1_map_tiers": [16]}
    lines, _ = asm.build_poe1_economy_lines("Allflame", [], {}, 1.0, False, snap)
    text = "\n".join(lines)
    assert '//[Type] == "Coral Reef Chart"' in text, "disabled chart must be commented"
    assert '\n[Type] == "Coral Forest Chart"' in text, "the others stay active"


def test_all_on_by_default():
    snap = {"item_states": {}, "cat_thresh": {}, "poe1_map_tiers": [16]}
    lines, _ = asm.build_poe1_economy_lines("Allflame", [], {}, 1.0, False, snap)
    text = "\n".join(lines)
    for base in asm.CHART_BASES:
        assert f'\n[Type] == "{base}"' in text, base


def test_the_disabled_walk_uses_the_active_games_groups():
    """_ap_disabled walked the PoE 2 list, so a PoE 1 toggle was never seen."""
    api = _Api("poe1", {"_charts": {"Sandy Seabed Chart": {"enabled": False}}})
    dis = api._ap_disabled({"item_states": api.cfg["item_states"],
                            "cat_enabled": {}})
    assert "Sandy Seabed Chart" in dis
