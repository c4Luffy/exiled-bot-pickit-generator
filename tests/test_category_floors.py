"""A category's FLOOR must come from what it is, not from which endpoint it uses.

``is_unique`` on a category tuple answers "which poe.ninja endpoint", not "is
this a unique item". Eight categories are fetched from the stash endpoint while
being ordinary drops — Precursor Tablets, skill gems, beasts, incubators,
vials, cluster jewels, invitations and maps — and using that flag to pick the
floor put every one of them behind the UNIQUE floor.

Reported from a real setup: with a 100 ex unique floor, tablets worth 75-90 ex
were written commented out while the Economy tab showed them as kept.
"""
from __future__ import annotations

import exilebot_pickit.generator as gen
from exilebot_pickit.generators import assembly as asm

SNAP = {"cat_thresh": {}}
GEAR, UNIQ = 2.0, 100.0


def _floor(key, is_unique):
    return asm.effective_min(SNAP, key, is_unique, GEAR, UNIQ)


def test_tablets_use_the_items_floor_not_the_unique_one():
    """The reported bug: 75 ex tablets vanishing behind a 100 ex unique floor."""
    assert _floor("tablets", True) == GEAR


def test_real_uniques_still_use_the_unique_floor():
    for key in ("unique_weapons", "unique_armours", "unique_tablets",
                "unique_jewels", "unique_relics"):
        assert _floor(key, True) == UNIQ, key


def test_every_stash_routed_non_unique_uses_the_items_floor():
    """Catches a new category being added with the same conflation."""
    offenders = []
    for gid in ("poe1", "poe2"):
        for key, _t, label, is_unique in gen.GAMES[gid].all_categories:
            if is_unique and not key.startswith("unique_"):
                if _floor(key, is_unique) != GEAR:
                    offenders.append(f"{gid}:{label}")
    assert not offenders, f"still on the unique floor: {offenders}"


def test_a_per_category_override_still_wins():
    snap = {"cat_thresh": {"tablets": 50.0}}
    assert asm.effective_min(snap, "tablets", True, GEAR, UNIQ) == 50.0
    assert asm.effective_min(snap, "unique_weapons", True, GEAR, UNIQ) == UNIQ


def test_a_zero_override_is_respected_not_treated_as_unset():
    snap = {"cat_thresh": {"unique_weapons": 0.0}}
    assert asm.effective_min(snap, "unique_weapons", True, GEAR, UNIQ) == 0.0


def test_the_helper_names_only_real_uniques():
    assert asm.is_unique_category("unique_weapons")
    assert not asm.is_unique_category("tablets")
    assert not asm.is_unique_category("skill_gems")
    assert not asm.is_unique_category("maps")
