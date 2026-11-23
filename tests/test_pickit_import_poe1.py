"""Create your filter for Path of Exile 1.

Same promise as PoE 2 — the filter shows everything the pickit could take,
equal or more, never less — with PoE 1's own vocabulary: MapTier instead of
WaystoneTier, PoE 1 item classes, Chaos prices, and Exiled Bot 1's
[UniqueName] rules, which a filter can only match through the unique's base.
"""
from __future__ import annotations

from exilebot_pickit.generators.filter_classification import extract_divine_rate
from exilebot_pickit.generators.pickit_import import convert_pickit_text

PICKIT = """\
// Conversion: 1 Divine = 200.00 Chaos
[Type] == "Divine Orb" # [StashItem] == "true" // ExValue = 200.00
[Type] == "Chaos Orb" # [StashItem] == "true" // ExValue = 1.00
[UniqueName] == "Headhunter" # [StashItem] == "true" // ExValue = 9000.00
[Category] == "Map" && [MapTier] >= "14" # [StashItem] == "true"
[Type] == "Map (Tier 16)" # [StashItem] == "true"
"""
BASES = {"Headhunter": "Leather Belt"}


def _blocks(lines):
    """Show blocks as lists of their indented lines."""
    out, cur = [], None
    for ln in lines:
        if ln == "Show":
            cur = []
            out.append(cur)
        elif cur is not None and ln.startswith("    "):
            cur.append(ln.strip())
        elif not ln:
            cur = None
    return out


def test_poe1_filter_header_and_chaos_ladder():
    res = convert_pickit_text(PICKIT, game="poe1", unique_bases=BASES)
    assert res["ok"]
    head = "\n".join(res["filter_lines"][:12])
    assert "Path of Exile 1 filter" in head
    assert " c |" in head and " ex " not in head      # Chaos, not Exalted
    assert res["report"]["game"] == "poe1"


def test_divine_rate_is_read_from_a_chaos_banner():
    assert extract_divine_rate(["// Conversion: 1 Divine = 209.40 Chaos"]) == 209.40


def test_unique_name_becomes_rarity_unique_plus_its_base():
    res = convert_pickit_text(PICKIT, game="poe1", unique_bases=BASES)
    blocks = _blocks(res["filter_lines"])
    hh = [b for b in blocks if 'BaseType == "Leather Belt"' in b]
    assert hh and "Rarity = Unique" in hh[0]
    # other uniques share the base, so the rule is reported as shown wider
    assert res["report"]["widened"] >= 1
    assert res["report"]["unresolved_uniques"] == 0


def test_unknown_unique_is_shown_through_every_unique_never_dropped():
    res = convert_pickit_text(PICKIT, game="poe1", unique_bases={})
    assert res["ok"]
    blocks = _blocks(res["filter_lines"])
    assert any(b[0] == "Rarity = Unique" and not any(x.startswith("BaseType") for x in b)
               for b in blocks)
    assert res["report"]["unresolved_uniques"] == 1
    assert res["report"]["untranslatable_total"] == 0


def test_map_tier_and_class_translate_exactly():
    res = convert_pickit_text(PICKIT, game="poe1", unique_bases=BASES)
    blocks = _blocks(res["filter_lines"])
    assert any('Class == "Maps"' in b and "MapTier >= 14" in b for b in blocks)
    assert any('BaseType == "Map (Tier 16)"' in b for b in blocks)


def test_poe2_only_vocabulary_is_never_written_into_a_poe1_filter():
    text = ('[Category] == "Waystone" && [WaystoneTier] >= "15" # [StashItem] == "true"\n'
            '[Category] == "Charm" && [Rarity] == "Rare" # [StashItem] == "true"\n')
    res = convert_pickit_text(text, game="poe1")
    body = "\n".join(res["filter_lines"])
    assert "WaystoneTier" not in body
    assert '"Waystones"' not in body and '"Charms"' not in body
    # the Charm rule keeps its rarity and is reported wider, not silently exact
    assert res["report"]["widened"] >= 1


def test_poe2_conversion_is_unchanged_by_default():
    text = '[Category] == "Waystone" && [WaystoneTier] >= "15" # [StashItem] == "true"\n'
    res = convert_pickit_text(text)
    body = "\n".join(res["filter_lines"])
    assert "Path of Exile 2 filter" in body
    assert "WaystoneTier >= 15" in body and 'Class == "Waystones"' in body
    assert res["report"]["game"] == "poe2"


def test_hide_keeps_gold_visible_in_poe1_too():
    res = convert_pickit_text(PICKIT, game="poe1", unique_bases=BASES, hide_rest=True)
    lines = res["filter_lines"]
    assert lines.index("    BaseType == \"Gold\"") < lines.index("Hide")
