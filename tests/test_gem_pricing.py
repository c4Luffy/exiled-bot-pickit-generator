"""Skill gems must be priced as they DROP, not at their best variant.

poe.ninja lists a gem once per (level, quality, corrupted) combination and
returns them dearest-first. Keeping the first row per name therefore priced
every gem at its best possible roll: measured on a live league, 666 of 810
gems were overstated by 10x or more, and Heavy Strike of Trarthus — 2c on the
ground — was written as 36,810c.

The damage was not cosmetic. It made the value floor useless for gems, since
every gem cleared any floor on the strength of a corrupted 21/23 variant it
will never be, so the bot picked up all 810.
"""
from __future__ import annotations

import re

from exilebot_pickit.generators import assembly as asm

# Frostblink's real variant table from a live league, dearest-first the way
# poe.ninja returns it. The plain drop is the last one: level 1, no quality,
# uncorrupted, 702 listings, 1 chaos.
FROSTBLINK = [
    {"name": "Frostblink", "gemLevel": 20, "gemQuality": 20, "corrupted": True,
     "primaryValue": 7853.0},
    {"name": "Frostblink", "gemLevel": 21, "gemQuality": 23, "corrupted": True,
     "primaryValue": 770.7},
    {"name": "Frostblink", "gemLevel": 20, "gemQuality": 23, "corrupted": True,
     "primaryValue": 75.6},
    {"name": "Frostblink", "gemLevel": 20, "gemQuality": 20, "corrupted": None,
     "primaryValue": 72.0},
    {"name": "Frostblink", "gemLevel": 1, "gemQuality": 20, "corrupted": None,
     "primaryValue": 32.1},
    {"name": "Frostblink", "gemLevel": 20, "gemQuality": None, "corrupted": None,
     "primaryValue": 2.0},
    {"name": "Frostblink", "gemLevel": 1, "gemQuality": None, "corrupted": None,
     "primaryValue": 1.0},
]
PAYLOAD = {"lines": FROSTBLINK}


def _ev(line):
    return float(re.search(r"ExValue = ([\d.]+)", line).group(1))


def test_prices_the_gem_as_it_drops():
    line = asm.build_poe1_gem_lines(PAYLOAD, 0.0)[0]
    assert _ev(line) == 1.0, "must use the level-1, quality-0, uncorrupted row"
    assert '[Type] == "Frostblink"' in line


def test_still_discloses_the_best_variant():
    """The gem you level can be worth chasing — just not off the ground."""
    line = asm.build_poe1_gem_lines(PAYLOAD, 0.0)[0]
    assert "best variant 7853.00" in line


def test_the_floor_becomes_meaningful_again():
    """The whole point: a 20c floor must now exclude a 1c gem."""
    assert asm.build_poe1_gem_lines(PAYLOAD, 20.0)[0].startswith("//")
    assert not asm.build_poe1_gem_lines(PAYLOAD, 0.5)[0].startswith("//")


def test_ignores_quality_and_corrupted_rows_entirely():
    """A gem listed ONLY as corrupted/qualified must not borrow those prices."""
    dear_only = {"lines": [line for line in FROSTBLINK
                           if line["corrupted"] or line["gemQuality"]]}
    line = asm.build_poe1_gem_lines(dear_only, 0.0)[0]
    # no plain row exists, so the cheapest variant stands in — conservative,
    # never the 7853c one
    assert _ev(line) == 32.1


def test_one_rule_per_gem():
    payload = {"lines": FROSTBLINK + [
        {"name": "Vaal Arc", "gemLevel": 20, "gemQuality": 20, "corrupted": True,
         "primaryValue": 6810.0},
        {"name": "Vaal Arc", "gemLevel": 1, "gemQuality": None, "corrupted": None,
         "primaryValue": 1.0},
    ]}
    lines = asm.build_poe1_gem_lines(payload, 0.0)
    assert len(lines) == 2
    assert all(_ev(line) == 1.0 for line in lines)


def test_disabled_gems_are_commented_out():
    assert asm.build_poe1_gem_lines(PAYLOAD, 0.0, {"Frostblink"})[0].startswith("//")


def test_empty_payload_is_not_a_crash():
    assert asm.build_poe1_gem_lines({"lines": []}, 5.0) == []
    assert asm.build_poe1_gem_lines({}, 5.0) == []


def test_plain_detector():
    assert asm._gem_is_plain({"gemQuality": None, "corrupted": None})
    assert asm._gem_is_plain({"gemQuality": 0, "corrupted": False})
    assert not asm._gem_is_plain({"gemQuality": 20, "corrupted": None})
    assert not asm._gem_is_plain({"gemQuality": None, "corrupted": True})


# ── the price SHOWN must equal the price the pickit was BUILT from ──────────
def test_drop_value_index_matches_the_rule_it_writes():
    """One definition of "worth as it drops", used by the rules and the UI.

    These were separate: the pickit used the plain row while the History
    pickup list took poe.ninja's first row per name. A dropped Stormbind was
    shown at 124c \u2014 the single listed level-21/quality-23 corrupted copy \u2014
    while the rule beside it said 1c.
    """
    idx = asm.drop_value_index(PAYLOAD)
    assert idx["Frostblink"] == 1.0
    line = asm.build_poe1_gem_lines(PAYLOAD, 0.0)[0]
    assert _ev(line) == idx["Frostblink"], "the shown price must equal the written one"


def test_drop_value_index_ignores_a_lone_expensive_variant():
    """Stormbind's real shape: one 124c corrupted listing, plain copies at 1c."""
    stormbind = {"lines": [
        {"name": "Stormbind", "gemLevel": 21, "gemQuality": 23, "corrupted": True,
         "primaryValue": 124.1},
        {"name": "Stormbind", "gemLevel": 20, "gemQuality": 20, "corrupted": None,
         "primaryValue": 10.0},
        {"name": "Stormbind", "gemLevel": 1, "gemQuality": None, "corrupted": None,
         "primaryValue": 1.0},
    ]}
    assert asm.drop_value_index(stormbind)["Stormbind"] == 1.0


def test_drop_value_index_leaves_single_row_categories_alone():
    plain = {"lines": [{"name": "Chaos Orb", "primaryValue": 1.0},
                       {"name": "Divine Orb", "primaryValue": 430.0}]}
    assert asm.drop_value_index(plain) == {"Chaos Orb": 1.0, "Divine Orb": 430.0}
