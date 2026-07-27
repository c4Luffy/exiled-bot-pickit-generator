"""Pure pickit-assembly logic — the rule-building half of a generate run.

Everything here is network-free, Tk-free, and I/O-free: it takes already-fetched
poe.ninja payloads plus a settings *snapshot* (a plain dict of the user's choices)
and returns the lines that get written to the ``.ipd``. The GUI's ``_generate``
keeps the fetching, threading, file writing and progress UI; it just delegates the
actual rule assembly to the functions below.

Splitting this out has two payoffs:
  • the generate pipeline becomes unit-testable without a display or the network
    (see test_assembly.py), and
  • the 550-line ``_generate`` god-method shrinks to orchestration.

Behaviour is intentionally identical to the old inline code — these functions were
lifted out of ``_generate`` statement-for-statement.
"""
from __future__ import annotations

import datetime
import re

from exilebot_pickit import generator as gen

_EXVALUE_RE = re.compile(r"ExValue = ([\d.]+)")
_UNIQUE_NAME_RE = re.compile(r'\[UniqueName\] == "([^"]+)"')
_FIRST_QUOTED_RE = re.compile(r'"([^"]+)"')


# ── Rule identity helpers (for diffing one pickit against another) ─────────────

def extract_rule_name(line: str) -> str | None:
    """The item identity a rule targets: its [UniqueName] if present, else the
    first quoted token (the [Type] / base name)."""
    um = _UNIQUE_NAME_RE.search(line)
    if um:
        return um.group(1)
    nm = _FIRST_QUOTED_RE.search(line)
    return nm.group(1) if nm else None


def active_rule_ids(lines) -> set[str]:
    """Identities of active (non-commented) rules — used to diff pickits."""
    ids: set[str] = set()
    for l in lines:
        if not l or l.startswith("//") or "[StashItem]" not in l:
            continue
        n = extract_rule_name(l)
        if n:
            ids.add(n)
    return ids


# ── File header (banner + the Exiled Bot 2 syntax guide) ──────────────────────

def build_header_lines(league: str, gen_ts: datetime.datetime, gen_id: str,
                       min_exalt: float, min_exalt_unique: float) -> list[str]:
    """A banner + the embedded syntax guide (see syntax_guide_lines below), kept
    for its own tests and as a reference format. NOT the banner either shipping
    writer uses — webui/api.py and generator.main() hand-roll a shorter banner
    with info this one lacks (a Divine-rate-missing safety guard, the app
    version): swapping either writer to THIS banner would regress that. What
    both writers DO use is syntax_guide_lines() below, appended after their own
    banner — see the "Configuration guide" call site there for real usage."""
    return [
        "/" * gen._W,
        "//" + f"  EXILEBOT 2  |  PICKIT  |  ID: {gen_id}".center(gen._W - 4) + "//",
        "/" * gen._W,
        f"// League    : {league}",
        f"// Generated : {gen_ts.strftime('%Y-%m-%d %H:%M:%S')}",
        f"// Pickit ID : {gen_id}",
        f"// Threshold : {min_exalt:.0f} ex  (currency/items)  |  {min_exalt_unique:.0f} ex  (unique gear)",
        "/" * gen._W, "",
    ] + syntax_guide_lines()


def is_rule_line(line: str) -> bool:
    """True for a REAL pickit rule line (active or commented-out).

    A rule carries the [StashItem] action AND the "#" before/after-identify
    split. The embedded syntax guide's ``// Example: ...`` lines also contain
    [StashItem], so a bare ``"[StashItem]" in line`` test counted 9 of them as
    commented-out rules — every UI that reads these numbers reported "9 skipped"
    for a pickit with nothing disabled at all. Same class of miscount the
    conversion report fixed in v4.39.5.
    """
    if "[StashItem]" not in line or "#" not in line:
        return False
    return not line.lstrip().lstrip("/").lstrip().startswith("Example:")


def syntax_guide_lines() -> list[str]:
    """The Exiled Bot 2 syntax reference embedded in every generated .ipd —
    [WeightedSum], [IgnoreRitual], WeaponCategory vocabulary, and worked
    examples. Static content (no run-specific data), so both writers can
    append it after their own banner. Wired in 2026-07-21 — previously only
    build_header_lines produced this text, and neither writer called that
    function, so no shipped file ever carried this reference at all."""
    return [
        # ── Configuration guide ───────────────────────────────────────
        "//",
        "// Exiled Bot 2 Pickit - Configuration Guide for Path of Exile 2",
        "//",
        "// This file defines which items your bot should pick up, identify, keep, or salvage.",
        "//",
        "// Important File:",
        "// - ModsList.html in the main bot folder contains all available mods",
        "//   (Use expressions from the right column, like local_minimum_added_physical_damage)",
        "//",
        "// Special Computed Values:",
        "// ----------------------",
        "// [TotalResistances] - Sums all resistance values on an item",
        '//   Example: [Category] == "Helmet" # [TotalResistances] > "50" && [StashItem] == "true"',
        "//",
        "// Defensive Calculations:",
        "// ---------------------",
        "// [ComputedArmour]       - Final armour value after all modifiers",
        "// [ComputedEvasion]      - Final evasion value after all modifiers",
        "// [ComputedEnergyShield] - Final ES value after all modifiers",
        "//",
        "// Damage Calculations:",
        "// ------------------",
        "// [DPS]         - Total weapon DPS (physical + elemental)",
        "// [ElementalDPS]  - Only elemental portion of weapon DPS",
        "// [PhysicalDPS]   - Only physical portion of weapon DPS",
        "//",
        "// Spell Damage Totals:",
        "// ------------------",
        "// [TotalSpellElementalDamage]  - Combined spell + elemental damage (%)",
        "// [TotalFireSpellDamage]       - Fire spell damage including general spell damage (%)",
        "// [TotalColdSpellDamage]       - Cold spell damage including general spell damage (%)",
        "// [TotalLightningSpellDamage]  - Lightning spell damage including general spell damage (%)",
        "//",
        "// Gems:",
        "// ----",
        "// [GemLevel] - Current level of the gem",
        '// Example: [Type] == "Uncut Support Gem" && [GemLevel] == "3" # [StashItem] == "true"',
        "//",
        "// UniqueName:",
        "// ----------",
        "// Matches specific unique items by their exact name",
        '// Example: [Type] == "Heavy Belt" && [Rarity] == "Unique" # [UniqueName] == "Headhunter" && [StashItem] == "true"',
        "//",
        "// ItemTier:",
        "// --------",
        "// Represents the tier of the item base type (higher is better)",
        '// Example: [Category] == "Ring" && [ItemTier] >= "2" # [StashItem] == "true"',
        "//",
        "// Quality:",
        "// -------",
        "// The quality percentage of an item (0-20 for most items)",
        '// Example: [Quality] >= "15" # [StashItem] == "true"',
        "//",
        "// WaystoneTier:",
        "// ------------",
        "// The tier of a waystone (1-16 at the moment)",
        '// Example: [Category] == "Waystone" && [WaystoneTier] >= "10" # [StashItem] == "true"',
        "//",
        "// Basic Syntax:",
        "// -----------",
        "// Each line: [What to Check] Operator \"Value\"",
        "//",
        "// Operators: == != > >= < <=",
        "// Combine:   && (AND)  || (OR)  () (group)",
        "//",
        "// Available Categories:",
        '// Equipment : "BodyArmour", "Gloves", "Boots", "Belt", "Helmet", "Ring", "Amulet"',
        '// Weapons   : "Weapon", "1Handed", "2Handed", "OffHand"',
        '// Others    : "Flask", "Waystone", "Gem"',
        "//",
        "// WeaponCategory:",
        '// 1H : "Claw","Dagger","Wand","OneHandSword","OneHandAxe","OneHandMace","Sceptre","Spear","Flail"',
        '// 2H : "Bow","Staff","TwoHandSword","TwoHandAxe","TwoHandMace","Quarterstaff","Crossbow","Trap"',
        '// OH : "Quiver","Shield","Focus"',
        "//",
        "// Rarity Values:  \"Normal\", \"Magic\", \"Rare\", \"Unique\"",
        "//",
        "// Special Flags:",
        '// [StashItem]    == "true"  - Put item in stash',
        '// [StashUnid]    == "true"  - Stash without identifying',
        '// [Salvage]      == "true"  - Mark for salvaging',
        '// [IgnoreRitual] == "true"  - Ignore item from ritual rewards',
        "//",
        "// Rule split with #:",
        "// Before # = checked BEFORE identifying",
        "// After  # = checked AFTER  identifying",
        '// Example: [Rarity] == "Rare" # [TotalResistances] > "50" && [StashItem] == "true"',
        "//",
        "// Local vs Global Modifiers:",
        "// local_* mods (local_attack_speed_+%) affect only the item itself",
        "// regular mods (attack_speed_+%)       affect your entire character",
        "//",
        "// Weighted Sums:",
        "// -------------",
        "// [WeightedSum(stat:weight, stat:weight, ...)] scores several stats as one",
        "// number instead of one condition per stat: each stat's rolled value is",
        "// multiplied by its weight, then all of them are added together.",
        "// Example: (life roll 100, weight 2) + (mana roll 200, weight 1) = 200 + 200 = 400",
        "// Set weights by comparing each stat's own top roll to the others (e.g. if life's",
        "// top roll is ~2x mana's, life is worth 2 sum points per point of mana).",
        "// The higher the total threshold you require, the stricter the pickit becomes.",
        "// Example: [WeightedSum(base_maximum_life:2,base_maximum_mana:1)] >= \"350\" "
        "&& [StashItem] == \"true\"",
        "//",
        "/" * gen._W, "",
    ]


# ── Currency → Divine conversion rate ─────────────────────────────────────────

def compute_divine_rate(currency_payload: dict) -> tuple[float, bool, float]:
    """Return ``(divine_rate_exalts, divine_found, exalted_rate)`` from the
    currency payload — the exalt value of one Divine Orb."""
    items_by_id = {i["id"]: i for i in currency_payload.get("items", [])}
    rate = gen.exalted_rate(currency_payload)
    divine_rate_exalts = 1.0
    found = False
    for line in currency_payload.get("lines", []):
        item = items_by_id.get(line.get("id"))
        if item and item.get("name") == "Divine Orb":
            pv = float(line.get("primaryValue") or 0.0)
            divine_rate_exalts = pv * rate if rate else pv
            found = True
            break
    return divine_rate_exalts, found, rate


# ── Coverage self-check ───────────────────────────────────────────────────────

# Categories that legitimately price ZERO items: poe.ninja doesn't list them and
# the app fills them from fallback rules, so an empty payload is normal, not a
# gap. Waystones has always returned 0 from the exchange endpoint — WAYSTONE_
# FALLBACK_RULES exists for exactly that. Grow this set, never silence the check.
EXPECTED_EMPTY_CATEGORIES = {"waystones"}


def coverage_warnings(payloads: dict, categories: list,
                      expected_empty: set | None = None) -> list:
    """Fetched categories whose payload ARRIVED but carries no priced items —
    so no rule was written for that whole category and nothing said so (the
    class of bug that hid Verisium).

    This is NOT proof the type was renamed: poe.ninja 404s an unknown type, and
    a failed fetch is reported separately. An empty-but-valid payload means the
    selected league prices none of that category — PoE1 Incubators return 29
    items in Standard and 0 in a league that doesn't drop them. Word any
    user-facing message accordingly.

    Returns ``[(key, label), ...]``. The expected-empty allowlist is skipped.
    A *missing* payload (network failure) is deliberately NOT flagged here — it
    is transient and reported separately; this only fires on a payload that came
    back successfully yet empty, which is a real, persistent coverage break."""
    skip = EXPECTED_EMPTY_CATEGORIES if expected_empty is None else expected_empty
    warns = []
    for key, _t, label, _is_unique in categories:
        if key in skip:
            continue
        p = payloads.get(key)
        # dict = fetched OK (a missing payload is None/str and skipped)
        if isinstance(p, dict) and not (p.get("items") or p.get("lines")):
            warns.append((key, label))
    return warns


# ── Per-category rule building ────────────────────────────────────────────────

def effective_min(snapshot: dict, key: str, is_unique: bool,
                  min_exalt_gear: float, min_exalt_unique: float) -> float:
    """The exalt threshold for a category: its per-category override when set
    (>= 0), otherwise the appropriate global (unique gear vs everything else)."""
    cat_thresh = snapshot.get("cat_thresh", {}).get(key, -1.0)
    if not isinstance(cat_thresh, (int, float)):
        cat_thresh = -1.0
    global_min = min_exalt_unique if is_unique else min_exalt_gear
    return cat_thresh if cat_thresh >= 0 else global_min


def enabled_names_for(key: str, is_unique: bool, payload: dict,
                      cat_states: dict) -> set[str] | None:
    """The set of item names to keep for an exchange category given the Items-tab
    on/off state, or ``None`` to fall back to pure threshold filtering (the default
    when nothing is disabled, and always for uniques)."""
    if cat_states and not is_unique:
        items_in_payload = {
            gen.ITEM_NAME_CORRECTIONS.get(i["name"], i["name"])
            for i in payload.get("items", []) if i.get("name")
        }
        disabled = {n for n, s in cat_states.items() if not s.get("enabled", True)}
        return items_in_payload - disabled
    return None


def build_category_lines(key: str, is_unique: bool, payload: dict,
                         divine_rate_exalts: float, eff_min: float,
                         min_exalt_gear: float,
                         enabled_names: set[str] | None,
                         cat_states: dict | None = None) -> list[str]:
    """Build the pickit lines for one economy category, dispatching to the right
    builder in poe2_pickit_generator based on the category key."""
    if key == "tablets":
        # Regular tablets are priced PER RARITY VARIANT (Normal/Magic/Rare),
        # not by name alone — this must be checked before the generic
        # is_unique branch below, even though this category also uses the
        # stash endpoint (is_unique=True) for fetching.
        dis = {n for n, s in (cat_states or {}).items()
               if not s.get("enabled", True)}
        return gen.build_tablet_market_lines(payload, divine_rate_exalts, min_exalt=eff_min,
                                             disabled_names=dis)
    if is_unique:
        dis = {n for n, s in (cat_states or {}).items()
               if not s.get("enabled", True)}
        # force_names: same "always kept regardless of floor" guarantee the
        # exchange branch below gets — dormant today (nothing force-picked is
        # priced as a unique), but the guarantee must hold if that ever changes.
        return gen.build_unique_lines(payload, divine_rate_exalts, min_exalt=eff_min,
                                      disabled_names=dis,
                                      force_names=gen.always_pick_force_names())
    if key == "uncut_gems":
        return gen.build_uncut_gem_lines(payload, divine_rate_exalts, min_exalt=eff_min,
                                         enabled_names=enabled_names)
    if key == "waystones":
        # waystone rows are synthetic (poe.ninja doesn't price them), so the
        # Economy-tab toggles come from cat_states, not the payload names
        dis = {n for n, s in (cat_states or {}).items()
               if not s.get("enabled", True)}
        return gen.build_waystone_lines(disabled=dis)
    pick_all  = key in gen.PICK_ALL_CATEGORIES
    tier_sort = (key == "essences")
    always    = gen.ALWAYS_PICK_CURRENCY if key == "currency" else (
        gen.ALWAYS_PICK_RUNES if key == "runes" else None)
    ritual_th = min_exalt_gear if key == "omens" else None
    return gen.build_exchange_lines(payload, divine_rate_exalts,
                                    pick_all=pick_all,
                                    min_exalt=eff_min,
                                    tier_sort=tier_sort,
                                    enabled_names=enabled_names,
                                    always_names=always,
                                    force_names=gen.always_pick_force_names(),
                                    ritual_threshold=ritual_th)


def top_items_from_lines(lines) -> list[tuple[str, float, str]]:
    """Pull ``(name, exalt_value, kind)`` triples out of active rules that
    carry an ``ExValue =`` comment — used to surface the most valuable picks.
    ``kind`` is a coarse display label derived from the rule itself."""
    out: list[tuple[str, float, str]] = []
    for l in lines:
        if l.startswith("//") or "[StashItem]" not in l:
            continue
        name = extract_rule_name(l)
        vm = _EXVALUE_RE.search(l)
        if name and vm:
            kind = ("Unique" if "[UniqueName]" in l else
                    "Base" if '[Rarity] == "Normal"' in l else "Currency")
            out.append((name, float(vm.group(1)), kind))
    return out


# ── Static / curated sections (tablets, wombgifts, chance, craft bases) ────────

def chance_base_disabled(snapshot: dict) -> set[str]:
    return {
        base for base, st in snapshot.get("item_states", {}).get("_chance", {}).items()
        if not st.get("enabled", True)
    }


def craft_base_section(snapshot: dict) -> tuple[list[str], int, int]:
    """Return ``(lines, rule_count, floor_ilvl)`` for the craft-base section.

    Every visible craft base carries an explicit per-base ilvl in the snapshot
    (the GUI bakes the value shown in each Craft Bases card into item_states before
    generating), so the .ipd always matches what the tab displays. ``floor_ilvl`` is
    the lowest level actually emitted among enabled bases, used for the section
    header so it never claims a level the rules don't use.
    """
    cb_states = snapshot.get("item_states", {}).get("_craftbase", {})
    disabled = {name for name, st in cb_states.items() if not st.get("enabled", True)}
    overrides = {name: st["ilvl"] for name, st in cb_states.items() if "ilvl" in st}
    global_min = int(snapshot.get("base_min_level", gen.CRAFT_BASE_MIN_ILVL))
    active_ilvls = [v for n, v in overrides.items() if n not in disabled]
    floor = min(active_ilvls) if active_ilvls else global_min
    lines = gen.build_craft_base_rules(disabled, min_ilvl=floor, ilvl_overrides=overrides)
    count = sum(1 for l in lines if l.startswith("[Type]"))
    return lines, count, floor


def fracture_pickit_section(snapshot: dict) -> list[str]:
    """Return pickit lines for the Fracture Bases section: Magic/Rare bases
    matching a per-class enabled, verified fracture target. Empty list if no
    class is enabled or none of the enabled classes have a verified target."""
    fb_states = snapshot.get("item_states", {}).get("_fracture", {})
    return gen.build_fracture_pickit_rules(fb_states)



# ── PoE 1 economy assembly (economy only — no rare gear) ──────────────────────

def _poe1_enabled_names(is_unique: bool, payload: dict, cat_states: dict) -> set | None:
    """PoE1 version of enabled_names_for: no PoE2 name corrections applied."""
    if cat_states and not is_unique:
        names = {i["name"] for i in payload.get("items", []) if i.get("name")}
        disabled = {n for n, s in cat_states.items() if not s.get("enabled", True)}
        return names - disabled
    return None


def build_poe1_stash_lines(payload: dict, min_exalt: float,
                           disabled: set | None = None,
                           key_tag: str = "Type") -> list[str]:
    """Rules for a PoE1 stash-endpoint category, matched by item name.

    ``key_tag`` picks EB1's native condition: real uniques use ``[UniqueName]``
    (EB1 identifies uniques by name alone — every unique line in a real EB1
    generated pickit is ``[UniqueName] == "X" # [StashItem] == "true"``, no
    base/rarity prefix), while non-unique stash items (incubators, gems, beasts,
    …) use ``[Type]``. Both differ from the PoE2 unique builder, so PoE1 needs
    its own. These payloads carry the name on the LINE (no ``items`` table), and
    exalted_rate is 0 for PoE1 so primaryValue (chaos) is used directly.
    """
    threshold = min_exalt
    dis = set(disabled or ())
    rate = gen.exalted_rate(payload)
    rows = []
    seen = set()
    for line in payload.get("lines", []):
        name = line.get("name")
        if not name or name in seen:      # EB1 keys these by name alone
            continue
        seen.add(name)
        pv = float(line.get("primaryValue") or 0.0)
        ev = pv * rate if rate else pv
        rule = (f'[{key_tag}] == "{gen._quote_ipd(name)}" '
                f'# [StashItem] == "true" // ExValue = {ev:.2f}')
        keep = ev >= threshold and name not in dis
        rows.append((ev, rule if keep else f"//{rule}"))
    rows.sort(key=lambda r: r[0], reverse=True)
    return [rule for _, rule in rows]


# Since Path of Exile 3.28's Atlas rework the generic map base IS literally named
# "Map (Tier N)" — the old named bases (Strand Map, Cemetery Map, …) are gone.
# poe.ninja reports it as the baseType, and Exiled Bot matches it by [Type].
# A conqueror variant ("Drox Map (Tier 16)") is that same base with influence, so
# it is covered by the tier's [Type] rule and needs no rule of its own.
_MAP_TIER_ANY = re.compile(r"Map \(Tier \d+\)\Z")

MAX_MAP_TIER = 16

# Quick presets on the Maps page. Each is just a SET of tiers, so a preset and a
# hand-picked selection are the same thing to the builder.
MAP_TIER_PRESETS = (
    ("t16", "T16 only", (16,)),
    ("t14", "T14 and up", (14, 15, 16)),
    ("red", "Red maps", tuple(range(11, 17))),
    ("yellow", "Yellow and up", tuple(range(6, 17))),
    ("all", "Every map", tuple(range(1, 17))),
)


def normalise_map_tiers(tiers) -> list[int]:
    """Accept a set/list of tiers, or a legacy ``>= N`` integer, -> sorted list.

    The setting used to be one integer meaning "this tier and above". Configs
    written before multi-select still hold that, so an int is expanded to the
    range it used to mean rather than being read as a single tier.
    """
    if isinstance(tiers, (int, float)) and not isinstance(tiers, bool):
        n = int(tiers)
        return list(range(n, MAX_MAP_TIER + 1)) if 1 <= n <= MAX_MAP_TIER else []
    out = set()
    for t in tiers or ():
        try:
            n = int(t)
        except (TypeError, ValueError):
            continue
        if 1 <= n <= MAX_MAP_TIER:
            out.add(n)
    return sorted(out)


def map_tier_runs(tiers) -> list[tuple[int, int]]:
    """Collapse selected tiers into contiguous runs: [14,15,16] -> [(14,16)],
    [14,16] -> [(14,14),(16,16)]. Used for the secondary [MapTier] rules."""
    runs: list[list[int]] = []
    for t in normalise_map_tiers(tiers):
        if runs and t == runs[-1][1] + 1:
            runs[-1][1] = t
        else:
            runs.append([t, t])
    return [(a, b) for a, b in runs]


def map_tier_rule(lo: int, hi: int) -> str:
    """One tier run -> one [MapTier] rule, in its simplest correct form.

    A run that reaches the top of the ladder stays OPEN-ENDED (``>=``): Exiled
    Bot's own default.ipd notes "Conquer/Boss maps can drop T14-18", so tiers
    above the 16 you can pick do exist.
    """
    if hi >= MAX_MAP_TIER:
        cond = f'[MapTier] >= "{lo}"'
    elif lo == hi:
        cond = f'[MapTier] == "{lo}"'
    else:
        cond = f'[MapTier] >= "{lo}" && [MapTier] <= "{hi}"'
    return f'[Category] == "Map" && {cond} # [StashItem] == "true"'


def map_base_rule(tier: int) -> str:
    """The rule that actually picks a map up on the current patch."""
    return f'[Type] == "Map (Tier {int(tier)})" # [StashItem] == "true"'


def build_poe1_map_lines(payload: dict, min_chaos: float, tiers,
                         disabled: set | None = None) -> list[str]:
    """Rules for Path of Exile 1 maps.

    Since 3.28 every ordinary map shares ONE base per tier, literally named
    ``Map (Tier N)`` — so a tier is picked up by naming that base. Exiled Bot
    v0.102 does not resolve ``[MapTier]`` on those bases (its own default.ipd
    says so and ships the same ``[Type]`` lines as the fix), which is why the
    ``[Type]`` rules below are the ones that do the work. The ``[MapTier]`` rules
    are kept alongside them: they cost nothing and still catch the named bases
    that do carry a tier, and newer bot builds may resolve it.

    Named maps poe.ninja prices under their own base (Vaal Temple, Nightmare,
    Shaper Guardian) get a rule each. An influenced map like "Drox Map (Tier 16)"
    is base ``Map (Tier 16)`` with influence, so the tier rule already covers it.

    An empty selection means no tier rules — named maps only. Pure: no I/O.
    """
    dis = set(disabled or ())
    picked = normalise_map_tiers(tiers)
    lines: list[str] = []

    if picked:
        lines.append("// Every ordinary map of the selected tiers. Since 3.28 the base is")
        lines.append('// literally called "Map (Tier N)", and this is what the bot matches on.')
        for t in sorted(picked, reverse=True):
            lines.append(map_base_rule(t))
        lines.append("")
        lines.append("// Belt and braces: the same tiers expressed with [MapTier], which still")
        lines.append("// catches older named bases that carry a tier.")
        for lo, hi in map_tier_runs(picked):
            lines.append(map_tier_rule(lo, hi))
    else:
        lines.append("// No tier selected — only the named maps below are taken.")
    lines.append("")

    rate = gen.exalted_rate(payload)
    rows, seen, covered = [], set(), 0
    for line in payload.get("lines", []):
        base = line.get("baseType") or line.get("name")
        if not base:
            continue
        if _MAP_TIER_ANY.search(base):
            covered += 1          # an ordinary/influenced map — the tier rules have it
            continue
        if base in seen:
            continue
        seen.add(base)
        pv = float(line.get("primaryValue") or 0.0)
        ev = pv * rate if rate else pv
        rule = (f'[Type] == "{gen._quote_ipd(base)}" '
                f'# [StashItem] == "true" // ExValue = {ev:.2f}')
        keep = ev >= min_chaos and base not in dis
        rows.append((ev, rule if keep else f"//{rule}"))
    rows.sort(key=lambda r: r[0], reverse=True)
    lines += [rule for _, rule in rows]
    if covered:
        lines.append(f"// {covered} more priced rows are ordinary or influence-marked maps"
                     ' ("Drox Map (Tier 16)" and similar) — same "Map (Tier N)" base, so'
                     " the tier rules above already pick them up.")
    return lines


def build_poe1_economy_lines(league: str, categories: list, payloads: dict,
                             divine_rate: float, divine_found: bool,
                             snapshot: dict) -> tuple[list[str], int]:
    """Assemble a full PoE 1 economy pickit from already-fetched payloads.

    PoE 1 is ECONOMY ONLY: currency, fragments, uniques and the other market
    categories, each kept or commented out by the value floor. None of the PoE 2
    rare-gear / craft / chance / fracture sections exist here. Prices are in
    Chaos (PoE 1's base unit) exactly as PoE 2's are in Exalt — the value math is
    identical, only the unit label differs.

    Returns ``(lines, active_rule_count)``. Pure: no network, no file I/O.
    """
    min_gear = float(snapshot.get("min_exalt_gear", 0.0) or 0.0)
    min_uniq = float(snapshot.get("min_exalt_unique", 0.0) or 0.0)
    item_states = snapshot.get("item_states", {}) or {}
    cat_enabled = snapshot.get("category_enabled", {}) or {}

    lines: list[str] = [
        "/" * gen._W,
        "//" + "  EXILEBOT  |  AUTO-GENERATED PICKIT  |  PATH OF EXILE 1".center(gen._W - 4) + "//",
        "/" * gen._W,
        f"// League    : {league}",
        f"// Threshold : {min_gear:.0f} c (currency/items)  |  {min_uniq:.0f} c (uniques)",
        "// Source    : poe.ninja PoE1 economy API",
    ]
    if divine_found:
        lines.append(f"// Conversion: 1 Divine = {divine_rate:.2f} Chaos")
    else:
        lines.append("// Conversion: Divine rate unavailable")
    # NOT the PoE2 syntax guide — that references PoE2-only categories/flags
    # ([Salvage], WaystoneTier, PoE2 WeaponCategory) which are wrong for Exiled
    # Bot 1. A short, EB1-accurate note instead.
    lines += [
        "/" * gen._W,
        "// Exiled Bot pickit (Path of Exile 1) — economy only.",
        "// Priced items to keep; anything below your floor is commented out.",
        '// Currency / market items:  [Type] == "Name" # [StashItem] == "true"',
        '// Uniques:                  [UniqueName] == "Name" # [StashItem] == "true"',
        "// Values in the // comments are Chaos.",
        "/" * gen._W, "",
    ]
    lines.append(gen.header_major("Economy Items"))
    lines.append("")

    for key, _ninja_type, label, is_unique in categories:
        payload = payloads.get(key)
        lines.append(gen.header_sub(label))
        lines.append("")
        if isinstance(payload, Exception) or payload is None:
            lines.append(f"// Could not fetch {label} — try again when poe.ninja is reachable")
            lines.append("")
            continue
        if not cat_enabled.get(key, True):
            lines.append(f"// {label} turned off in Economy")
            lines.append("")
            continue
        cat_states = item_states.get(key, {})
        eff_min = effective_min(snapshot, key, is_unique, min_gear, min_uniq)
        if key == "maps":
            # Maps price by base and are taken by tier — not uniques, so they
            # follow the general items floor rather than the unique floor.
            eff_min = effective_min(snapshot, key, False, min_gear, min_uniq)
            dis = {n for n, s in cat_states.items() if not s.get("enabled", True)}
            cat_lines = build_poe1_map_lines(
                payload, eff_min,
                snapshot.get("poe1_map_tiers", snapshot.get("poe1_map_tier", 16)), dis)
        elif is_unique:
            dis = {n for n, s in cat_states.items() if not s.get("enabled", True)}
            # Stash-endpoint category. Real uniques (unique_* keys) match by
            # [UniqueName]; other stash items (incubators, gems, beasts…) by
            # [Type] — both EB1's native forms.
            tag = "UniqueName" if key.startswith("unique_") else "Type"
            cat_lines = build_poe1_stash_lines(payload, eff_min, dis, key_tag=tag)
        else:
            enabled = _poe1_enabled_names(is_unique, payload, cat_states)
            cat_lines = gen.build_exchange_lines(payload, divine_rate, pick_all=False,
                                                 min_exalt=eff_min, enabled_names=enabled,
                                                 corrections={}, skip=set())
        if not cat_lines:
            lines.append(f"// poe.ninja returned no rows for {label} in this league")
        lines += cat_lines
        lines.append("")

    active = sum(1 for l in lines if is_rule_line(l) and not l.lstrip().startswith("//"))
    return lines, active


# ── Price-move alerts ─────────────────────────────────────────────────────────

def compute_price_alerts(categories, all_payloads: dict,
                         prev_league_prices: dict, chaos_ex_val: float,
                         threshold: float = 0.20):
    """Compare current vs previous-run prices and flag big movers.

    Returns ``(new_gen_prices, alerts)`` where ``new_gen_prices`` is
    ``{cat_key: {name: exalt_value}}`` (the new baseline to persist) and ``alerts``
    is a list of ``(abs_delta, display_text)`` for moves of at least *threshold*.
    """
    new_gen_prices: dict = {}
    alerts: list[tuple[float, str]] = []

    for key, _t, _label, _is_unique in categories:
        payload = all_payloads.get(key)
        if not payload or isinstance(payload, Exception):
            continue
        rate = gen.exalted_rate(payload)
        items_by_id = {i["id"]: i for i in payload.get("items", [])}
        cur_prices: dict = {}
        for line in payload.get("lines", []):
            # Unique payloads ship items: [] and carry the name on the LINE — the
            # same reason build_unique_lines reads the line directly. Requiring an
            # items-table entry silently skipped every unique, so all 7 unique
            # categories recorded zero prices and Top movers could never show one.
            item = items_by_id.get(line.get("id"))
            raw_name = (item or {}).get("name") or line.get("name")
            if not raw_name:
                continue
            if raw_name in gen.ITEM_NAME_SKIP:
                continue
            name = gen.ITEM_NAME_CORRECTIONS.get(raw_name, raw_name)
            pv = float(line.get("primaryValue") or 0.0)
            ex = pv * rate if rate else pv  # same convention as build_exchange_lines
            # A unique is priced once per base type it rolls on, so the same name
            # can appear several times. Keep the highest rather than letting
            # iteration order decide which price represents it.
            cur_prices[name] = max(ex, cur_prices.get(name, 0.0))
        new_gen_prices[key] = cur_prices

        prev_cat = prev_league_prices.get(key, {})
        for name, ex_now in cur_prices.items():
            ex_prev = prev_cat.get(name)
            if ex_prev is None or ex_prev <= 0 or ex_now <= 0:
                continue
            delta = (ex_now - ex_prev) / ex_prev
            if abs(delta) < threshold:
                continue
            chaos_now  = ex_now  / chaos_ex_val if chaos_ex_val else ex_now
            chaos_prev = ex_prev / chaos_ex_val if chaos_ex_val else ex_prev
            # Skip near-worthless items — they round to "0c → 0c" and just spam the
            # panel with meaningless huge percentages.
            if max(chaos_now, chaos_prev) < 1.0:
                continue
            sign  = "+" if delta > 0 else ""
            arrow = "▲" if delta > 0 else "▼"
            text = f"{arrow} {name}: {chaos_prev:.0f}c → {chaos_now:.0f}c  ({sign}{delta*100:.0f}%)"
            alerts.append((abs(delta), text))

    return new_gen_prices, alerts
