"""Charts (Fathomless Depths) were removed from Path of Exile 1.

They used to be always-picked with no price, plus their own "Always pick"
group in the Economy tab. Neither may come back by accident: a rule for an item
that no longer drops is dead weight, and a toggle for it is a lie.
"""
from __future__ import annotations

from exilebot_pickit.generators import assembly as asm
from exilebot_pickit.webui import api as webapi


class _Api(webapi.AppApi):
    def __init__(self, game):
        self.cfg = {"active_game": game, "item_states": {}}

    def _game(self):
        import exilebot_pickit.generator as gen
        return gen.get_game(self.cfg.get("active_game"))


def test_poe1_pickit_has_no_chart_rules():
    snap = {"min_exalt_gear": 0.0, "min_exalt_unique": 0.0,
            # a config saved while Charts existed must not bring them back
            "item_states": {"_charts": {"Coral Reef Chart": {"enabled": True}}}}
    lines, active = asm.build_poe1_economy_lines("Covens", [], {}, 200.0, True, snap)
    assert active == 0
    assert not any("Chart" in ln and not ln.startswith("//") for ln in lines)


def test_poe1_has_no_always_pick_groups():
    assert _Api("poe1")._ap_groups_for_game() == []


def test_poe2_keeps_its_always_pick_groups():
    keys = [k for k, _l, _r in _Api("poe2")._ap_groups_for_game()]
    assert keys and "_charts" not in keys
