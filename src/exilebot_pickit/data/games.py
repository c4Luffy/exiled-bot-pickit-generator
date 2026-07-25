"""The game table — the ONLY place PoE 1 and PoE 2 differ.

The price engine, the ``.ipd`` writer and the UI shell are all game-agnostic:
they read numbers and write rules without caring which game produced them. The
handful of things that genuinely differ between the two games — the poe.ninja
base URL, the league index, the category list, the price unit — live here, one
row per game, so the rest of the app can just ask the active :class:`GameSpec`.

Design rules baked in:
  * Each game keeps its OWN poe.ninja endpoints. A PoE1 run only ever touches
    ``/poe1/`` and a PoE2 run only ``/poe2/`` — they never share a call.
  * The PoE2 category list is imported from :mod:`api.client` (its historical
    home, with all the load-bearing comments) so this module stays additive and
    PoE2 behaviour is byte-for-byte unchanged.
  * PoE1 is ECONOMY ONLY (``economy_only=True``): no chance/craft/exceptional/
    fracture/rare-gear rules, so it needs almost no bundled game data — uniques
    come live from poe.ninja.

poe.ninja migrated PoE1 onto the same versioned API as PoE2 (the old
``/api/data/currencyoverview`` + ``itemoverview`` are 404). So swapping
``/poe2/`` → ``/poe1/`` on the exact same endpoints is all it takes. Verified
live 2026-07-24; re-verify category ``type`` strings against the live API before
trusting a new PoE1 patch (a wrong ``type`` returns an empty payload silently).
"""

from dataclasses import dataclass

from exilebot_pickit.api.client import (
    EXCHANGE_CATEGORIES as _POE2_EXCHANGE,
    UNIQUE_CATEGORIES as _POE2_UNIQUE,
)

# A category is (key, ninja_type, label, is_unique) — same shape both games.
# is_unique routes the fetch: True → stash/current/item/overview,
#                             False → exchange/current/overview.


@dataclass(frozen=True)
class GameSpec:
    """Everything that differs between one game and another."""

    id: str            # stable key: "poe2" | "poe1" (used in config + cache keys)
    label: str         # full name, e.g. "Path of Exile 2"
    short: str         # sidebar label, e.g. "PoE 2"
    base_url: str      # poe.ninja economy base, e.g. ".../poe2/api/economy"
    index_url: str     # league index-state URL for this game
    unit: str          # price-unit name shown in the UI ("Exalt" / "Chaos")
    unit_short: str    # short unit label ("ex" / "c")
    exchange_categories: tuple  # is_unique=False categories
    unique_categories: tuple    # is_unique=True categories
    economy_only: bool = False  # PoE1: skip every rare-gear rule builder
    default_output_base: str = "pickit"
    # Preferred league when the user hasn't chosen one. PoE1's auto-detected
    # "current" league is often a challenge/event league poe.ninja lists but does
    # NOT price (0 items), so PoE1 defaults to Standard, which always has data.
    default_league: str = ""

    @property
    def all_categories(self) -> list:
        return list(self.exchange_categories) + list(self.unique_categories)


# ── PoE 2 — today's app, unchanged ────────────────────────────────────────────
POE2 = GameSpec(
    id="poe2",
    label="Path of Exile 2",
    short="PoE 2",
    base_url="https://poe.ninja/poe2/api/economy",
    index_url="https://poe.ninja/poe2/api/data/index-state",
    unit="Exalt",
    unit_short="ex",
    exchange_categories=tuple(_POE2_EXCHANGE),
    unique_categories=tuple(_POE2_UNIQUE),
    economy_only=False,
    default_output_base="poe2_pickit",
)


# ── PoE 1 — economy only ──────────────────────────────────────────────────────
# Category ``type`` strings probed live against poe.ninja's PoE1 versioned API
# (2026-07-24). A wrong/renamed type returns an empty payload with NO error, so
# re-verify these against the live site after a PoE1 patch before shipping.
_POE1_EXCHANGE = (
    # (key,               ninja_type,       label,             is_unique)
    ("currency",          "Currency",       "Currency",          False),
    ("fragments",         "Fragment",       "Fragments",         False),
    ("scarabs",           "Scarab",         "Scarabs",           False),
    ("fossils",           "Fossil",         "Fossils",           False),
    ("resonators",        "Resonator",      "Resonators",        False),
    ("essences",          "Essence",        "Essences",          False),
    ("oils",              "Oil",            "Oils",              False),
    ("divination_cards",  "DivinationCard", "Divination Cards",  False),
    ("artifacts",         "Artifact",       "Artifacts",         False),
    ("omens",             "Omen",           "Omens",             False),
    ("tattoos",           "Tattoo",         "Tattoos",           False),
    ("allflame_embers",   "AllflameEmber",  "Allflame Embers",   False),
    ("delirium_orbs",     "DeliriumOrb",    "Delirium Orbs",     False),
)
_POE1_UNIQUE = (
    ("incubators",        "Incubator",      "Incubators",        True),
    ("vials",             "Vial",           "Vials",             True),
    ("beasts",            "Beast",          "Beasts",            True),
    ("cluster_jewels",    "ClusterJewel",   "Cluster Jewels",    True),
    ("skill_gems",        "SkillGem",       "Skill Gems",        True),
    ("invitations",       "Invitation",     "Invitations",       True),
    ("unique_weapons",    "UniqueWeapon",   "Unique Weapons",    True),
    ("unique_armours",    "UniqueArmour",   "Unique Armours",    True),
    ("unique_accessories","UniqueAccessory","Unique Accessories",True),
    ("unique_flasks",     "UniqueFlask",    "Unique Flasks",     True),
    ("unique_jewels",     "UniqueJewel",    "Unique Jewels",     True),
    ("unique_maps",       "UniqueMap",      "Unique Maps",       True),
    ("unique_relics",     "UniqueRelic",    "Unique Relics",     True),
)
POE1 = GameSpec(
    id="poe1",
    label="Path of Exile",
    short="PoE 1",
    base_url="https://poe.ninja/poe1/api/economy",
    index_url="https://poe.ninja/poe1/api/data/index-state",
    unit="Chaos",
    unit_short="c",
    exchange_categories=_POE1_EXCHANGE,
    unique_categories=_POE1_UNIQUE,
    economy_only=True,
    default_output_base="poe1_pickit",
    default_league="Standard",
)


GAMES = {POE2.id: POE2, POE1.id: POE1}
DEFAULT_GAME = POE2.id


def get_game(game_id: str | None) -> GameSpec:
    """Return the :class:`GameSpec` for *game_id*, defaulting to PoE 2.

    Unknown/blank ids fall back to PoE 2 rather than raising — a stale config
    value must never hard-fail the app (same principle as remote-data loading).
    """
    return GAMES.get((game_id or "").strip().lower(), POE2)
