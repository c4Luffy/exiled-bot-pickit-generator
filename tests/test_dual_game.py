"""Dual-game (PoE1 / PoE2) support: game table, per-game config, PoE1 economy.

All network-free — poe.ninja is never touched here. These guard the four load-
bearing pieces of the split: the game table, the game-aware client cache/normalize,
the per-game config sections (with lossless migration), and the economy-only
PoE1 assembler.
"""
import copy

import pytest

from exilebot_pickit import generator as gen
from exilebot_pickit.api import client
from exilebot_pickit.data import games
from exilebot_pickit.generators import assembly as asm
from exilebot_pickit.ui import config as cfgmod


# ── Game table ────────────────────────────────────────────────────────────────

def test_get_game_defaults_to_poe2():
    assert games.get_game(None).id == "poe2"
    assert games.get_game("").id == "poe2"
    assert games.get_game("nonsense").id == "poe2"     # unknown never raises
    assert games.get_game("POE1").id == "poe1"          # case-insensitive


def test_game_specs_differ_where_they_should():
    p2, p1 = games.POE2, games.POE1
    assert "/poe2/" in p2.base_url and "/poe1/" in p1.base_url
    assert p2.economy_only is False and p1.economy_only is True
    assert p2.unit == "Exalt" and p1.unit == "Chaos"
    assert p1.default_output_base == "poe1_pickit"
    # PoE1 must carry its own categories, not PoE2's
    assert p1.all_categories and p1.all_categories != p2.all_categories


def test_poe1_categories_have_the_verified_types():
    types = {t for _k, t, _l, _u in games.POE1.all_categories}
    # a sample of the live-verified type strings (see project memory)
    for t in ("Currency", "Scarab", "Fossil", "DivinationCard", "UniqueWeapon"):
        assert t in types


# ── Game-aware client: cache isolation + PoE1 normalize ───────────────────────

def test_cache_keys_are_isolated_per_game():
    client.clear_cache()
    client._cache_set("Standard", "currency", {"a": 1}, "poe2")
    client._cache_set("Standard", "currency", {"a": 2}, "poe1")
    assert client._cache_get("Standard", "currency", "poe2") == {"a": 1}
    assert client._cache_get("Standard", "currency", "poe1") == {"a": 2}
    client.clear_cache()


def test_poe1_unique_payload_gets_primary_value_injected():
    payload = {"lines": [{"name": "Headhunter", "baseType": "Leather Belt",
                          "chaosValue": 5000.0}]}
    out = client._normalize_poe1_payload(payload, is_unique=True)
    assert out["lines"][0]["primaryValue"] == 5000.0


def test_poe1_exchange_payload_is_untouched():
    payload = {"lines": [{"id": 1, "primaryValue": 3.0}]}
    out = client._normalize_poe1_payload(payload, is_unique=False)
    assert out["lines"][0]["primaryValue"] == 3.0


# ── Per-game config ───────────────────────────────────────────────────────────

def test_flat_config_migrates_into_poe2_section():
    cfg = copy.deepcopy(cfgmod.DEFAULT_CONFIG)
    del cfg["games"]
    del cfg["active_game"]
    cfg["league"] = "Standard"
    cfg["min_exalt_unique"] = 6.0
    cfgmod._ensure_game_sections(cfg)
    assert cfg["active_game"] == "poe2"
    assert cfg["games"]["poe2"]["league"] == "Standard"
    assert cfg["games"]["poe2"]["min_exalt_unique"] == 6.0


def test_switch_game_keeps_both_games_separate():
    cfg = copy.deepcopy(cfgmod.DEFAULT_CONFIG)
    cfg["league"] = "Standard"
    cfg["min_exalt_unique"] = 6.0
    cfgmod._ensure_game_sections(cfg)

    cfgmod.switch_game(cfg, "poe1")
    assert cfg["active_game"] == "poe1"
    assert cfg["league"] == ""                     # fresh PoE1 section
    assert cfg["output_base"] == "poe1_pickit"
    cfg["league"] = "Settlers"

    cfgmod.switch_game(cfg, "poe2")                 # back — PoE1 edits preserved
    assert cfg["league"] == "Standard"
    assert cfg["min_exalt_unique"] == 6.0
    assert cfg["games"]["poe1"]["league"] == "Settlers"


def test_config_helpers_never_mutate_shared_default():
    # A shallow dict(DEFAULT_CONFIG) shares the 'games' object; the helpers must
    # rebuild it, never scribble into the module default (real bug this guards).
    before = copy.deepcopy(cfgmod.DEFAULT_CONFIG["games"])
    cfg = dict(cfgmod.DEFAULT_CONFIG)              # shallow, like the config tests
    cfgmod._store_game_section(cfg, "poe2")
    cfgmod.switch_game(cfg, "poe1")
    assert cfgmod.DEFAULT_CONFIG["games"] == before == {}


# ── PoE1 economy assembler ────────────────────────────────────────────────────

def _poe1_payloads():
    currency = {"items": [{"id": 1, "name": "Divine Orb"},
                          {"id": 2, "name": "Chaos Orb"},
                          {"id": 3, "name": "Orb of Alteration"}],
                "lines": [{"id": 1, "primaryValue": 150.0},
                          {"id": 2, "primaryValue": 1.0},
                          {"id": 3, "primaryValue": 0.1}]}
    uniqw = {"lines": [{"name": "Headhunter", "baseType": "Leather Belt",
                        "primaryValue": 50000.0},
                       {"name": "Wanderlust", "baseType": "Wool Boots",
                        "primaryValue": 2.0}]}
    return currency, uniqw


def test_build_poe1_economy_lines_applies_floors_and_syntax():
    currency, uniqw = _poe1_payloads()
    rate, found, _ = asm.compute_divine_rate(currency)
    cats = [("currency", "Currency", "Currency", False),
            ("unique_weapons", "UniqueWeapon", "Unique Weapons", True)]
    payloads = {"currency": currency, "unique_weapons": uniqw}
    snap = {"min_exalt_gear": 1.0, "min_exalt_unique": 10.0,
            "item_states": {}, "category_enabled": {}}
    lines, active = asm.build_poe1_economy_lines(
        "Standard", cats, payloads, rate, found, snap)
    text = "\n".join(lines)
    # kept above floor, active
    assert '[Type] == "Divine Orb" # [StashItem] == "true"' in text
    # uniques use EB1's native [UniqueName] format (no base/rarity prefix)
    assert '[UniqueName] == "Headhunter" # [StashItem] == "true"' in text
    # below floor → commented out
    assert '//[Type] == "Orb of Alteration"' in text
    assert '//[UniqueName] == "Wanderlust"' in text  # unique below 10 floor
    # 3 active: Divine, Chaos, Headhunter
    assert active == 3


def test_build_exchange_lines_can_skip_poe2_name_fixes():
    # With empty corrections/skip, a name that IS a PoE2 correction key must pass
    # through unchanged (PoE1 items must not be renamed by PoE2 rules).
    key = next(iter(gen.ITEM_NAME_CORRECTIONS), None)
    if not key:
        pytest.skip("no corrections table to probe")
    payload = {"items": [{"id": 1, "name": key}],
               "lines": [{"id": 1, "primaryValue": 100.0}]}
    poe1 = gen.build_exchange_lines(payload, 1.0, min_exalt=0.0,
                                    corrections={}, skip=set())
    assert f'"{key}"' in "\n".join(poe1)     # kept its raw PoE1-style name
