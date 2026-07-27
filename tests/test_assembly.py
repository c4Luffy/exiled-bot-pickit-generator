"""Unit tests for pickit_assembly — the pure rule-assembly logic lifted out of the
GUI's ``_generate``. These run with no display, no network, no file I/O, so the
generation pipeline is finally testable on its own.

Run with:  python -m pytest test_assembly.py -v
"""
import datetime
import re

from exilebot_pickit.generators import assembly as asm
from exilebot_pickit import generator as gen


# ── Helpers ──────────────────────────────────────────────────────────────────

def _exchange_payload(items, rate=1.0):
    """poe.ninja-shaped exchange payload. items: list of (id, name, primary_value)."""
    return {
        "core":  {"rates": {"exalted": rate}},
        "items": [{"id": i, "name": n} for i, n, _ in items],
        "lines": [{"id": i, "primaryValue": v} for i, _, v in items],
    }


def _unique_payload(rows, rate=1.0):
    """Unique payload. rows: list of (name, base_type, primary_value)."""
    return {
        "core":  {"rates": {"exalted": rate}},
        "lines": [{"name": n, "baseType": b, "primaryValue": v} for n, b, v in rows],
    }


# ── build_header_lines ───────────────────────────────────────────────────────

def test_header_banner_carries_league_and_id():
    ts = datetime.datetime(2026, 6, 28, 16, 37, 44)
    out = asm.build_header_lines("Fate of the Vaal", ts, "20260628_163744", 7.0, 50.0)
    text = "\n".join(out)
    assert "ID: 20260628_163744" in out[1]
    assert "Fate of the Vaal" in text
    assert out[0] == "/" * gen._W           # opening border
    assert "2026-06-28 16:37:44" in text    # generated timestamp


def test_header_documents_core_tokens():
    out = "\n".join(asm.build_header_lines("L", datetime.datetime.now(), "ID", 0, 0))
    for token in ("[TotalResistances]", "[ComputedArmour]", "[UniqueName]",
                  "[WaystoneTier]", "[IgnoreRitual]", "[StashUnid]", "WeaponCategory"):
        assert token in out, f"header missing {token}"
    # The all-important pre/post-identify split must be explained.
    assert "Before # = checked BEFORE identifying" in out


# ── compute_divine_rate ──────────────────────────────────────────────────────

def test_compute_divine_rate_found():
    payload = _exchange_payload([(1, "Divine Orb", 350.0), (2, "Chaos Orb", 1.0)], rate=1.0)
    divine, found, rate = asm.compute_divine_rate(payload)
    assert found is True
    assert divine == 350.0
    assert rate == 1.0


def test_compute_divine_rate_applies_exalted_rate():
    payload = _exchange_payload([(1, "Divine Orb", 2.0)], rate=180.0)
    divine, found, _ = asm.compute_divine_rate(payload)
    assert found is True
    assert divine == 360.0     # primaryValue * exalted rate


def test_compute_divine_rate_missing():
    payload = _exchange_payload([(1, "Chaos Orb", 1.0)], rate=1.0)
    divine, found, _ = asm.compute_divine_rate(payload)
    assert found is False
    assert divine == 1.0


# ── effective_min ────────────────────────────────────────────────────────────

def test_effective_min_category_override_wins():
    snap = {"cat_thresh": {"currency": 12.0}}
    assert asm.effective_min(snap, "currency", False, 5.0, 50.0) == 12.0


def test_effective_min_falls_back_to_gear_global():
    snap = {"cat_thresh": {"currency": -1.0}}
    assert asm.effective_min(snap, "currency", False, 5.0, 50.0) == 5.0


def test_effective_min_uses_unique_global_for_uniques():
    snap = {"cat_thresh": {}}
    assert asm.effective_min(snap, "unique_weapons", True, 5.0, 50.0) == 50.0


def test_effective_min_tolerates_bad_value():
    snap = {"cat_thresh": {"currency": "oops"}}
    assert asm.effective_min(snap, "currency", False, 5.0, 50.0) == 5.0


# ── enabled_names_for ────────────────────────────────────────────────────────

def test_enabled_names_excludes_disabled():
    payload = _exchange_payload([(1, "Chaos Orb", 1), (2, "Divine Orb", 1), (3, "Mirror", 1)])
    states = {"Divine Orb": {"enabled": False}}
    names = asm.enabled_names_for("currency", False, payload, states)
    assert names == {"Chaos Orb", "Mirror"}


def test_enabled_names_none_for_uniques():
    payload = _unique_payload([("Headhunter", "Heavy Belt", 1)])
    assert asm.enabled_names_for("unique_weapons", True, payload, {"x": {}}) is None


def test_enabled_names_none_when_no_states():
    payload = _exchange_payload([(1, "Chaos Orb", 1)])
    assert asm.enabled_names_for("currency", False, payload, {}) is None


# ── build_category_lines ─────────────────────────────────────────────────────

def test_build_category_lines_unique():
    payload = _unique_payload([("Headhunter", "Heavy Belt", 100.0)])
    lines = asm.build_category_lines("unique_weapons", True, payload, 1.0, 10.0, 5.0, None)
    joined = "\n".join(lines)
    assert '[UniqueName] == "Headhunter"' in joined
    assert '[Type] == "Heavy Belt"' in joined


def test_build_category_lines_currency_pick_all():
    # currency is a PICK_ALL category — every item active regardless of threshold.
    payload = _exchange_payload([(1, "Chaos Orb", 0.001)], rate=1.0)
    lines = asm.build_category_lines("currency", False, payload, 1.0, 9999.0, 5.0, None)
    active = [l for l in lines if l.startswith("[Type]")]
    assert any('"Chaos Orb"' in l for l in active)   # not commented out despite tiny value


def test_build_category_lines_waystones_ignores_payload():
    lines = asm.build_category_lines("waystones", False, {}, 1.0, 0.0, 5.0, None)
    assert lines == gen.build_waystone_lines()


def test_build_category_lines_tablets_dispatches_before_is_unique_branch():
    """The "tablets" key must be checked BEFORE the generic `is_unique` branch,
    even though it also fetches via the stash endpoint (is_unique=True) —
    otherwise it would wrongly fall into build_unique_lines and emit
    [UniqueName] rules for an ordinary Normal/Magic/Rare tablet."""
    payload = {
        "core": {"rates": {"exalted": 1.0}},
        "lines": [
            {"name": "Ritual Tablet", "baseType": "Ritual Tablet",
             "variant": "Normal", "primaryValue": 50.0},
            {"name": "Ritual Tablet", "baseType": "Ritual Tablet",
             "variant": "Rare", "primaryValue": 1.0},
        ],
    }
    cat_states = {"Ritual Tablet (Rare)": {"enabled": False}}
    lines = asm.build_category_lines("tablets", True, payload, 1.0, 10.0, 5.0,
                                     None, cat_states=cat_states)
    joined = "\n".join(lines)
    assert '[UniqueName]' not in joined
    assert '[Type] == "Ritual Tablet" && [Rarity] == "Normal"' in joined
    # disabled by its combined (base, variant) identity -> gone entirely
    assert "Rare" not in joined


def test_price_alerts_record_uniques_not_just_items_table_categories():
    """Unique payloads ship items: [] and carry the name on the LINE — the same
    reason build_unique_lines reads the line directly. compute_price_alerts
    required an items-table entry, so all 7 unique categories recorded ZERO
    prices: Mageblood could double and Top movers stayed empty, permanently,
    because the persisted baseline was empty too."""
    cats = [("unique_armours", None, "Unique Armours", True)]
    payloads = {"unique_armours": {
        "core": {"rates": {"exalted": 100.0}},
        "items": [],                                  # uniques have no items table
        "lines": [{"name": "Some Unique", "baseType": "Silk Robe", "primaryValue": 2.0}],
    }}
    prices, _alerts = asm.compute_price_alerts(cats, payloads, {}, 1.0, 0.2)
    assert prices["unique_armours"] == {"Some Unique": 200.0}


def test_price_alerts_fire_for_a_unique_that_moved():
    """With a baseline recorded, a real move must now produce an alert."""
    cats = [("unique_armours", None, "Unique Armours", True)]
    payloads = {"unique_armours": {
        "core": {"rates": {"exalted": 100.0}},
        "items": [],
        "lines": [{"name": "Some Unique", "baseType": "Silk Robe", "primaryValue": 4.0}],
    }}
    prev = {"unique_armours": {"Some Unique": 200.0}}      # doubled to 400
    _prices, alerts = asm.compute_price_alerts(cats, payloads, prev, 1.0, 0.2)
    assert any("Some Unique" in text for _sort, text in alerts), alerts


def test_a_unique_priced_on_several_bases_keeps_its_highest_price():
    """poe.ninja prices a unique once per base it rolls on, so the same name
    repeats. Iteration order must not decide which price represents it."""
    cats = [("unique_armours", None, "Unique Armours", True)]
    payloads = {"unique_armours": {
        "core": {"rates": {"exalted": 1.0}},
        "items": [],
        "lines": [{"name": "Two Base Unique", "baseType": "A", "primaryValue": 5.0},
                  {"name": "Two Base Unique", "baseType": "B", "primaryValue": 50.0}],
    }}
    prices, _ = asm.compute_price_alerts(cats, payloads, {}, 1.0, 0.2)
    assert prices["unique_armours"]["Two Base Unique"] == 50.0


def test_coverage_warnings_flags_empty_but_fetched_categories():
    """A payload that arrives but carries no items is poe.ninja renaming/retiring
    a type — the category silently stops pricing (how Verisium went unfetched).
    That must be flagged; a missing payload (network fail) must NOT be."""
    cats = [
        ("currency", "Currency", "Currency", False),
        ("idols", "Idols", "Idols", False),
        ("runes", "Runes", "Runes", False),
        ("waystones", "Waystones", "Waystones", False),
        ("unique_weapons", "UniqueWeapons", "Unique Weapons", True),
    ]
    payloads = {
        "currency": {"items": [{"name": "Chaos Orb"}]},   # healthy
        "idols": {"items": []},                            # fetched but EMPTY -> flag
        "runes": None,                                     # network fail -> NOT flagged here
        "waystones": {"items": []},                        # expected-empty -> skipped
        "unique_weapons": {"lines": []},                   # empty unique -> flag
    }
    warns = asm.coverage_warnings(payloads, cats)
    keys = {k for k, _l in warns}
    assert keys == {"idols", "unique_weapons"}
    assert "waystones" not in keys      # allowlisted
    assert "runes" not in keys          # missing != empty
    assert "currency" not in keys       # healthy


def test_coverage_warnings_respects_a_custom_allowlist():
    cats = [("idols", "Idols", "Idols", False)]
    payloads = {"idols": {"items": []}}
    assert asm.coverage_warnings(payloads, cats, expected_empty={"idols"}) == []


# ── PoE 1 maps ───────────────────────────────────────────────────────────────
#
# poe.ninja prices most PoE1 maps as "<Boss> Map (Tier N)" — a price bucket for
# "any tier-N map with that influence", not an item name. Writing those as
# [Type] rules would emit rules that match nothing, so the builder turns them
# into the one tier rule Exiled Bot's own default.ipd uses.

def _map_payload():
    return {"lines": [
        {"name": "Nightmare Map", "primaryValue": 40.0},
        {"name": "Baran Vaal Temple Map", "baseType": "Vaal Temple Map",
         "primaryValue": 30.0},
        {"name": "Vaal Temple Map", "baseType": "Vaal Temple Map",
         "primaryValue": 25.0},
        {"name": "Drox Map (Tier 16)", "baseType": "Map (Tier 16)",
         "primaryValue": 6.0},
        {"name": "Veritania Map (Tier 16)", "baseType": "Map (Tier 16)",
         "primaryValue": 6.0},
        {"name": "Shaper Guardian Map", "primaryValue": 3.0},
    ]}


def test_poe1_maps_emit_one_active_tier_rule():
    lines = asm.build_poe1_map_lines(_map_payload(), min_chaos=5.0, tiers=[16])
    active = [ln for ln in lines if ln.startswith("[")]
    tier_rules = [ln for ln in active if "[MapTier]" in ln]
    assert tier_rules == ['[Category] == "Map" && [MapTier] >= "16" # [StashItem] == "true"']
    # a non-contiguous pick becomes two rules, not a bogus range
    two = asm.build_poe1_map_lines(_map_payload(), min_chaos=5.0, tiers=[14, 16])
    conds = [ln for ln in two if ln.startswith("[Category]")]
    assert conds == ['[Category] == "Map" && [MapTier] == "14" # [StashItem] == "true"',
                     '[Category] == "Map" && [MapTier] >= "16" # [StashItem] == "true"'], conds
    # An interior block becomes one rule PER TIER, never a "<=" bound: the map
    # runner's own docs warn that "less than" on [MapTier] hits a bot bug.
    block = asm.build_poe1_map_lines(_map_payload(), min_chaos=5.0, tiers=[11, 12, 13])
    conds = [ln for ln in block if ln.startswith("[Category]")]
    assert conds == [f'[Category] == "Map" && [MapTier] == "{t}" # [StashItem] == "true"'
                     for t in (11, 12, 13)], conds
    assert not any("<=" in c for c in conds)


def test_poe1_maps_name_the_generic_tier_base():
    """Since 3.28 the generic map base IS "Map (Tier N)" — naming it is how the
    bot matches a map. An earlier version treated it as a poe.ninja price bucket
    and threw it away, which left PoE 1 map pickup matching nothing at all:
    Exiled Bot v0.102 does not resolve [MapTier] on those bases (its own
    default.ipd says so and ships these same [Type] lines as the fix)."""
    lines = asm.build_poe1_map_lines(_map_payload(), min_chaos=0.0, tiers=[16])
    active = [ln for ln in lines if ln.startswith("[")]
    assert '[Type] == "Map (Tier 16)" # [StashItem] == "true"' in active
    # the influence-marked variants share that base, so they get no rule of
    # their own — and their names are never written as a [Type]
    joined = " | ".join(active)
    assert "Drox" not in joined and "Veritania" not in joined
    assert any("already pick them up" in ln for ln in lines)


def test_poe1_maps_dedupe_influenced_variants_to_one_base():
    lines = asm.build_poe1_map_lines(_map_payload(), min_chaos=0.0, tiers=[16])
    vaal = [ln for ln in lines if "Vaal Temple Map" in ln]
    assert len(vaal) == 1, vaal
    assert vaal[0].startswith('[Type] == "Vaal Temple Map"')
    assert "Baran" not in vaal[0]          # the influence prefix is not a base type
    assert "ExValue = 30.00" in vaal[0]    # keeps the higher of the two prices


def test_poe1_maps_respect_the_floor_and_disabled_names():
    lines = asm.build_poe1_map_lines(_map_payload(), min_chaos=5.0, tiers=[16])
    assert any(ln.startswith('[Type] == "Nightmare Map"') for ln in lines)
    assert any(ln.startswith('//[Type] == "Shaper Guardian Map"') for ln in lines)

    off = asm.build_poe1_map_lines(_map_payload(), min_chaos=0.0, tiers=[16],
                                   disabled={"Nightmare Map"})
    assert any(ln.startswith('//[Type] == "Nightmare Map"') for ln in off)


def test_poe1_empty_tier_selection_writes_no_tier_rule():
    lines = asm.build_poe1_map_lines(_map_payload(), min_chaos=0.0, tiers=[])
    assert not any(ln.startswith("[Category]") for ln in lines)
    assert any("No tier selected" in ln for ln in lines)
    # named maps still come through
    assert any(ln.startswith('[Type] == "Nightmare Map"') for ln in lines)


def test_poe1_runegrafts_are_fetched():
    """A whole priced category went unfetched before (Verisium, then these)."""
    from exilebot_pickit.data.games import POE1
    keys = {c[0] for c in POE1.all_categories}
    assert "runegrafts" in keys
    assert "maps" in keys


def test_poe1_map_rules_are_never_typeless():
    """A [StashItem] rule with no [Type]/[Category] matches EVERYTHING on the
    ground — the audit's standing rule, checked here for the map builder too."""
    lines = asm.build_poe1_map_lines(_map_payload(), min_chaos=0.0, tiers=[16])
    for ln in lines:
        if ln.startswith("//") or "[StashItem]" not in ln:
            continue
        assert "[Type]" in ln or "[Category]" in ln, ln


def test_poe1_map_names_are_quote_escaped():
    """A map name holding a literal quote must not unbalance its rule — the
    v4.41.28 failure mode, checked for this builder too."""
    payload = {"lines": [{"name": 'Weird " Map', "primaryValue": 99.0}]}
    lines = asm.build_poe1_map_lines(payload, min_chaos=0.0, tiers=[])
    rule = next(ln for ln in lines if ln.startswith("[Type]"))
    assert '\\"' in rule, rule                      # the name's quote is escaped
    # structural quotes (the unescaped ones) must still pair up
    unescaped = len(re.findall(r'(?<!\\)"', rule))
    assert unescaped % 2 == 0, rule


def test_poe1_map_rules_pass_the_validator():
    """[MapTier] is a pickit KEY, not an item mod. The validator's key list was
    PoE2-only (WaystoneTier but no MapTier), so every generated PoE 1 map rule
    came back as `Invalid mod: "MapTier"` — a validation error on a correct file."""
    lines = asm.build_poe1_map_lines(_map_payload(), min_chaos=0.0,
                                     tiers=[14, 16])
    active = [ln for ln in lines if ln and not ln.startswith("//")]
    report = gen.validate_pickit(active)
    assert report["errors"] == [], report["errors"]
    assert report["warnings"] == [], report["warnings"]


def test_map_tier_runs_collapse_and_split():
    assert asm.map_tier_runs([14, 15, 16]) == [(14, 16)]
    assert asm.map_tier_runs([14, 16]) == [(14, 14), (16, 16)]
    assert asm.map_tier_runs([1]) == [(1, 1)]
    assert asm.map_tier_runs([]) == []
    assert asm.map_tier_runs([16, 14, 15, 14]) == [(14, 16)]     # unsorted + dupes
    assert asm.map_tier_runs([0, 99, "x", None, 5]) == [(5, 5)]  # junk dropped


def test_legacy_single_tier_setting_still_means_that_tier_and_up():
    """Configs written before multi-select hold one int meaning ">= N"."""
    assert asm.normalise_map_tiers(14) == [14, 15, 16]
    assert asm.normalise_map_tiers(16) == [16]
    assert asm.normalise_map_tiers(0) == []


def test_top_of_the_ladder_stays_open_ended():
    """Conqueror/boss maps drop up to T18, so the top run must not be pinned."""
    assert asm.map_tier_rule(16, 16) == ['[Category] == "Map" && [MapTier] >= "16" '
                                         '# [StashItem] == "true"']
    assert asm.map_tier_rule(3, 3) == ['[Category] == "Map" && [MapTier] == "3" '
                                       '# [StashItem] == "true"']


def test_map_tier_conditions_never_use_less_than():
    """The map runner's docs warn that "less than" on [MapTier] hits a bot bug
    unless paired with a magic >= 66. Avoid the operator entirely instead."""
    for lo, hi in [(1, 16), (11, 13), (3, 3), (14, 16), (2, 9)]:
        for c in asm.map_tier_conditions(lo, hi):
            assert "<" not in c, (lo, hi, c)


# ── PoE 1 map runner (Maps/*.ipd) ────────────────────────────────────────────

def test_map_runner_follows_the_bot_default_structure():
    """Same rules and order as Exiled Bot's own Maps/default.ipd."""
    out = asm.build_poe1_map_runner_lines([14, 15, 16], "Allflame", "9.9.9")
    active = [ln for ln in out if ln and not ln.startswith("//")]
    assert active[0] == '[Rarity] == "Normal" # [UpgradeToMagic] == "true"'
    assert active[1] == '[Rarity] == "Magic"  # [AugmentIfPossible] == "true"'
    assert '[MapTier] >= "14" # [RunMap] == "true"' in active
    assert '[Rarity] == "Unique" # [IgnoreMap] == "true"' in active
    # each danger mod appears twice: reroll on magic, skip on rare
    for stat, _note in asm.MAP_DANGER_MODS:
        hits = [ln for ln in active if stat in ln]
        assert len(hits) == 2, (stat, hits)
        assert any('[Rarity] == "Magic"' in h and "RerollMods" in h for h in hits)
        assert any('[Rarity] == "Rare"' in h and "IgnoreMap" in h for h in hits)


def test_map_runner_tier_selection_drives_runmap():
    out = asm.build_poe1_map_runner_lines([14, 16])
    runs = [ln for ln in out if "[RunMap]" in ln and not ln.startswith("//")]
    assert runs == ['[MapTier] == "14" # [RunMap] == "true"',
                    '[MapTier] >= "16" # [RunMap] == "true"'], runs


def test_map_runner_never_writes_an_empty_run_rule():
    """No tiers selected must not produce a file that runs nothing — that would
    stop the bot dead. Keep the bot's own default range instead."""
    out = asm.build_poe1_map_runner_lines([])
    runs = [ln for ln in out if "[RunMap]" in ln and not ln.startswith("//")]
    assert runs == ['[MapTier] >= "1" # [RunMap] == "true"'], runs


def test_map_runner_upgrades_the_tiers_you_do_not_run():
    """Tiers below the selection are traded up, and they name the CURRENT base
    (`Map (Tier N)`). The bot's own examples name pre-3.28 bases like "Arena Map"
    that no longer exist, so they'd match nothing even uncommented."""
    out = asm.build_poe1_map_runner_lines([14, 15, 16])
    ups = [ln for ln in out if "UpgradeMapTier" in ln and not ln.startswith("//")]
    assert len(ups) == 13                      # tiers 1..13
    assert ups[0] == ('[Type] == "Map (Tier 1)" && [Rarity] != "Unique" '
                      '# [UpgradeMapTier] == "true"')
    assert all('[Rarity] != "Unique"' in u for u in ups)
    # never marks a tier you actually run for upgrading
    assert not any('(Tier 14)' in u or '(Tier 15)' in u or '(Tier 16)' in u for u in ups)


def test_map_runner_has_nothing_to_upgrade_when_every_tier_runs():
    out = asm.build_poe1_map_runner_lines(list(range(1, 17)))
    assert not [ln for ln in out if "UpgradeMapTier" in ln and not ln.startswith("//")]
    assert any("Nothing to upgrade" in ln for ln in out)
