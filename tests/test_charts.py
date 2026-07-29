"""Charts (Path of Exile 1's Fathomless Depths mechanic).

Item class "DeepwaterChart" — brought to Valerie to explore the Depths and
combined on the Voyage Board. poe.ninja does not price this category (no Chart
type on its PoE 1 economy API, and none of the 28 categories we fetch carries
one), so unlike every other section these cannot be valued or floored; they are
picked up on sight.
"""
from __future__ import annotations

import re

from exilebot_pickit.generators import assembly as asm


def _rules(lines):
    return [l for l in lines if not l.startswith("//")]


def test_writes_a_rule_for_every_chart():
    lines = asm.build_poe1_chart_lines()
    assert len(_rules(lines)) == len(asm.CHART_BASES) == 3


def test_every_rule_names_a_type():
    """CLAUDE.md: a rule with no [Type]/[Category] matches EVERYTHING."""
    for rule in _rules(asm.build_poe1_chart_lines()):
        assert re.match(r'^\[Type\] == "[^"]+" # \[StashItem\] == "true"$', rule), rule


def test_the_base_names_are_the_verified_ones():
    assert set(asm.CHART_BASES) == {
        "Coral Forest Chart", "Coral Reef Chart", "Sandy Seabed Chart"}


def test_a_disabled_chart_is_commented_out():
    lines = asm.build_poe1_chart_lines({"Coral Reef Chart"})
    assert len(_rules(lines)) == 2
    assert any(l.startswith('//[Type] == "Coral Reef Chart"') for l in lines)


def test_it_says_why_there_is_no_value():
    """Every other section is floored by price; this one cannot be."""
    assert any("does not price" in l for l in asm.build_poe1_chart_lines())


def test_charts_reach_a_real_poe1_pickit():
    """The section must actually be emitted, not just be buildable.

    A notice added in v4.51.0 was written into the PoE 2 path while the feature
    was PoE 1 only, so it could never run — and its tests passed because they
    only checked the wording. Assemble the real thing instead.
    """
    lines, _active = asm.build_poe1_economy_lines(
        "Allflame", [], {}, 1.0, False,
        {"item_states": {}, "cat_thresh": {}, "poe1_map_tiers": [16]})
    text = "\n".join(lines)
    for base in asm.CHART_BASES:
        assert f'[Type] == "{base}"' in text, f"{base} missing from the pickit"
