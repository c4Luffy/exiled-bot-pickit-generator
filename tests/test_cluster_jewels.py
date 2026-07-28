"""Cluster jewels, and the class of bug they belong to.

poe.ninja keys the ClusterJewel category by the jewel's ENCHANTMENT, so its row
names are sentences like "Minions deal 10% increased Damage". Those went
straight into ``[Type] == "..."``, which is not an item type and matched
nothing — 41 dead rules in a shipped pickit, the same silent failure the
pre-3.28 map bases had.

The last test here is the general guard: no rule this app writes may target a
[Type] that is obviously mod text rather than an item name.
"""
from __future__ import annotations

import re

from exilebot_pickit.generators import assembly as asm

# Shaped like the real payload: name = enchantment, baseType = the actual item.
# The value spread mirrors a live league, where the great majority of every
# base's variants sit at 1c and a handful carry all the worth (measured on
# Allflame: 425 Large variants, median 1c, best 1289c).
def _variants(base, dear):
    rows = [{"name": f"{n}% increased Something", "baseType": base,
             "primaryValue": 1.0} for n in range(5)]
    rows.append({"name": f"Minions deal 10% increased Damage ({base})",
                 "baseType": base, "primaryValue": dear})
    return rows


PAYLOAD = {"lines": (_variants("Large Cluster Jewel", 1289.0)
                     + _variants("Medium Cluster Jewel", 88.6)
                     + _variants("Small Cluster Jewel", 937.6))}


def _rules(lines):
    return [ln for ln in lines if not ln.startswith("//")]


def test_targets_the_base_not_the_enchantment():
    lines = asm.build_poe1_cluster_lines(PAYLOAD, 0.0)
    types = set(re.findall(r'\[Type\] == "([^"]+)"', "\n".join(lines)))
    assert types == {"Large Cluster Jewel", "Medium Cluster Jewel",
                     "Small Cluster Jewel"}
    joined = "\n".join(lines)
    assert "Minions deal" not in joined, "enchantment text must never be a [Type]"
    assert "+12% to Chaos Resistance" not in joined


def test_one_rule_per_base():
    lines = asm.build_poe1_cluster_lines(PAYLOAD, 0.0)
    assert len(_rules(lines)) == 3, "425 variants collapse to one rule per base"


def test_prices_at_the_median_not_the_best_roll():
    """A Large Cluster Jewel's best roll is 1289c; a random one is worth 1c."""
    lines = asm.build_poe1_cluster_lines(PAYLOAD, 0.0)
    large = next(ln for ln in lines if "Large Cluster Jewel" in ln)
    ev = float(re.search(r"ExValue = ([\d.]+)", large).group(1))
    assert ev == 1.0, f"expected the median (1c), got {ev}"
    assert "best roll 1289.00" in large, "the best roll is still disclosed"


def test_a_real_floor_leaves_them_commented_out():
    """The honest outcome: visible, with the reason, not silently picked up."""
    lines = asm.build_poe1_cluster_lines(PAYLOAD, 20.0)
    assert _rules(lines) == [], "median 1c must not clear a 20c floor"
    assert any("cannot read" in ln for ln in lines), "and it says why"


def test_a_zero_floor_still_takes_them():
    assert len(_rules(asm.build_poe1_cluster_lines(PAYLOAD, 0.0))) == 3


def test_empty_payload_is_not_a_crash():
    assert asm.build_poe1_cluster_lines({"lines": []}, 5.0) == []
    assert asm.build_poe1_cluster_lines({}, 5.0) == []


def test_rows_without_a_basetype_are_skipped():
    bad = {"lines": [{"name": "whatever", "primaryValue": 99.0}]}
    assert asm.build_poe1_cluster_lines(bad, 0.0) == []


# ── the general guard ────────────────────────────────────────────────────
_MOD_SHAPED = re.compile(
    r'^(?:[+-]?\d+(?:\.\d+)?%?\s|.*\b(?:increased|reduced|more|less)\b)', re.I)


def test_no_rule_targets_mod_text_as_an_item_type():
    """Whatever the category, a [Type] must look like an item, not a stat line.

    This is the check that would have caught the cluster-jewel rules on the day
    they were written, without anyone knowing that category was special.
    """
    lines = asm.build_poe1_cluster_lines(PAYLOAD, 0.0)
    offenders = [t for t in re.findall(r'\[Type\] == "([^"]+)"', "\n".join(lines))
                 if _MOD_SHAPED.match(t)]
    assert not offenders, f"mod text used as an item type: {offenders}"
