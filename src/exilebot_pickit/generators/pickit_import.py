"""Convert ANY Exiled Bot pickit (.ipd) into an in-game loot filter.

Both games: ``game="poe2"`` (the default) writes a Path of Exile 2 filter,
``game="poe1"`` a Path of Exile 1 one. The two filter languages are the same
syntax with different vocabularies (item classes, MapTier vs WaystoneTier),
and Exiled Bot 1 names uniques with ``[UniqueName]``, which a filter cannot
match — so PoE 1 resolves a unique to its base type (see ``unique_bases``).

The engine already turns the pickits *we* generate into a matching `.filter`
(``generator.build_loot_filter``). This module is the user-facing sibling: it
takes a pickit from anywhere — hand-written, another tool, months of manual
tuning — and produces a filter from it, plus a plain-language report of what
it understood.

The guiding rule: **the filter shows everything the pickit could take — equal
or more, never less.** A pickit can check things the game filter cannot see
(mods, tiers, resistances); those checks are dropped from the filter side so
the item still gets a label. The one exception is deliberate: when the user
turns on "hide everything else", hide is honored even if some rules couldn't
be translated — the risk is surfaced loudly (report + a warning inside the
filter) instead of refusing, because the owner decided hide must mean hide.
(A hiding filter is still a bad idea while botting — see
``copy_filter_to_game`` in ui/config.py.)

Pure module: no network, no UI, no file I/O — mirrors generators/assembly.py.
"""
from __future__ import annotations

import re
import time

from exilebot_pickit import generator as gen
from exilebot_pickit.generators.filter_classification import (
    classify_rule, extract_divine_rate, section_from_comment,
    threshold_summary, visual_report, visual_sort_key,
)

# Pickup-side conditions the converter can express in a loot filter. Anything
# else found before the `#` (ItemTier, GemLevel, TotalResistances, …) is a
# bot-only check: it gets dropped and the rule is counted as "widened".
_KNOWN_TOKENS = {"Type", "Rarity", "Quality", "Sockets", "Category",
                 "ItemLevel", "WaystoneTier"}
# Path of Exile 1: no WaystoneTier (PoE 2 only), but MapTier and Exiled Bot 1's
# [UniqueName] both carry over. Verified against NeverSink's live PoE 1 SOFT
# filter (2026-11-23): MapTier is a real condition there (46 uses).
_KNOWN_TOKENS_POE1 = {"Type", "Rarity", "Quality", "Sockets", "Category",
                      "ItemLevel", "MapTier", "UniqueName"}

_TOKEN_RE = re.compile(r"\[(\w+)\]")

# ItemLevel and WaystoneTier translate EXACTLY: both are real PoE2 filter
# conditions (verified against NeverSink's live SOFT filter — 74 and 46 uses).
# The filter's comparison operators match the bot's, so the value+op carry
# straight over and these rules stop counting as "shown wider".
_ILVL_RE = re.compile(r'\[ItemLevel\]\s*(>=|<=|==|>|<)\s*"(\d+)"')
_WTIER_RE = re.compile(r'\[WaystoneTier\]\s*(>=|<=|==|>|<)\s*"(\d+)"')
_MTIER_RE = re.compile(r'\[MapTier\]\s*(>=|<=|==|>|<)\s*"(\d+)"')
_UNIQUE_NAME_RE = re.compile(r'\[UniqueName\]\s*==\s*"((?:[^"\\]|\\.)*)"')

# Exiled Bot [Category] value → PoE2 filter Class name(s), keyed lowercase.
# Every Class string is verified against NeverSink's live SOFT filter (the
# game's real vocabulary) — a wrong string silently matches nothing, which
# with Hide on would hide items the pickit wants. Add new entries only after
# checking that filter again (see .claude/skills/verify-game-data).
_CATEGORY_CLASS = {
    "helmet": ["Helmets"], "bodyarmour": ["Body Armours"],
    "gloves": ["Gloves"], "boots": ["Boots"],
    "ring": ["Rings"], "amulet": ["Amulets"], "belt": ["Belts"],
    "flask": ["Life Flasks", "Mana Flasks"],
    "lifeflask": ["Life Flasks"], "manaflask": ["Mana Flasks"],
    "charm": ["Charms"], "jewel": ["Jewels"], "quiver": ["Quivers"],
    "shield": ["Shields"], "buckler": ["Bucklers"], "focus": ["Foci"],
    "wand": ["Wands"], "staff": ["Staves"], "bow": ["Bows"],
    "crossbow": ["Crossbows"], "sceptre": ["Sceptres"], "spear": ["Spears"],
    "talisman": ["Talismans"], "quarterstaff": ["Quarterstaves"],
    "onehandmace": ["One Hand Maces"], "twohandmace": ["Two Hand Maces"],
    "mace": ["One Hand Maces", "Two Hand Maces"],
    "waystone": ["Waystones"], "tablet": ["Tablet"],
    "currency": ["Stackable Currency"],
}

# Path of Exile 1 [Category] → filter Class. Every Class string appears in
# NeverSink's live PoE 1 SOFT filter (checked 2026-11-23). PoE 2-only classes
# (Charms, Foci, Crossbows, Spears, Waystones, Tablet…) are absent on purpose:
# a category that has no PoE 1 class is dropped and the rule shown wider.
_CATEGORY_CLASS_POE1 = {
    "helmet": ["Helmets"], "bodyarmour": ["Body Armours"],
    "gloves": ["Gloves"], "boots": ["Boots"],
    "ring": ["Rings"], "amulet": ["Amulets"], "belt": ["Belts"],
    "flask": ["Life Flasks", "Mana Flasks", "Hybrid Flasks", "Utility Flasks"],
    "lifeflask": ["Life Flasks"], "manaflask": ["Mana Flasks"],
    "hybridflask": ["Hybrid Flasks"], "utilityflask": ["Utility Flasks"],
    "jewel": ["Jewels"], "abyssjewel": ["Abyss Jewels"], "quiver": ["Quivers"],
    "shield": ["Shields"], "wand": ["Wands"], "staff": ["Staves"],
    "warstaff": ["Warstaves"], "bow": ["Bows"], "sceptre": ["Sceptres"],
    "dagger": ["Daggers"], "runedagger": ["Rune Daggers"], "claw": ["Claws"],
    "onehandsword": ["One Hand Swords"], "twohandsword": ["Two Hand Swords"],
    "onehandmace": ["One Hand Maces"], "twohandmace": ["Two Hand Maces"],
    "mace": ["One Hand Maces", "Two Hand Maces"],
    "onehandaxe": ["One Hand Axes"], "twohandaxe": ["Two Hand Axes"],
    "map": ["Maps"], "currency": ["Stackable Currency"],
    "divinationcard": ["Divination Cards"], "fragment": ["Map Fragments"],
    "gem": ["Skill Gems", "Support Gems"], "skillgem": ["Skill Gems"],
    "supportgem": ["Support Gems"], "tincture": ["Tinctures"],
    "relic": ["Relics"], "corpse": ["Corpses"], "viscera": ["Viscera"],
    "wombgift": ["Wombgifts"],
}

# Label styles and rule classification are shared with the automatic filter
# writer. Generated IPDs retain their ExValue tiers; hand-written files fall
# back to section/purpose styles when no price exists.

# Keep the untranslatable list small enough for the UI report.
_MAX_LISTED = 30


# The game's filter parser only knows these rarity words; anything else on a
# Rarity line could make the client reject the WHOLE filter, so unknown values
# are dropped (wider) instead of passed through.
_VALID_RARITIES = {"Normal", "Magic", "Rare", "Unique"}

# Characters a filter string can't carry: '#' starts a comment, '"' ends the
# string, and the syntax has no escaping. No real PoE2 item name contains
# either — a name that does is hand-crafted and simply can't be expressed.
_UNEXPRESSIBLE = ('"', "#")


# The embedded syntax guide's two documentation shapes: a worked "Example:" and
# the Special Flags legend ('[StashItem] == "true"  - Put item in stash'). Both
# are comments carrying a real action/type token, so the disabled-rule counter
# mistook them for rules someone had switched off.
_GUIDE_EXAMPLE_RE = re.compile(r'^\s*Example\s*:', re.I)
_GUIDE_LEGEND_RE = re.compile(r'^\s*\[\w+\]\s*==\s*"[^"]*"\s+-\s+\S')


def _is_guide_line(line: str) -> bool:
    """True for a syntax-guide comment (documentation), not a disabled rule.

    Deliberately narrow: it only strips the two shapes the guide actually
    writes. A genuinely commented-out rule — including one using [Salvage] or
    [StashUnid], or written without the '#' split, as hand-made and imported
    pickits do — still counts as disabled.
    """
    body = line.lstrip("/").strip()
    return bool(_GUIDE_EXAMPLE_RE.match(body) or _GUIDE_LEGEND_RE.match(body))


def _pickup_half(line: str) -> str:
    """Everything before the first '#' OUTSIDE quotes — the pickup conditions.
    A naive split('#') used to cut inside quoted names and silently lose them."""
    in_q = False
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if in_q and c == "\\" and i + 1 < n:
            i += 2
            continue
        if c == '"':
            in_q = not in_q
        elif c == "#" and not in_q:
            return line[:i]
        i += 1
    return line


def _parse_rule(cond_part: str, game: str = "poe2"):
    """Extract the filter-expressible pieces of one rule's pickup half."""
    poe1 = game == "poe1"
    names = [n.replace('\\"', '"') for n in gen._LF_TYPE_RE.findall(cond_part)]
    uniques = ([n.replace('\\"', '"') for n in _UNIQUE_NAME_RE.findall(cond_part)]
               if poe1 else [])
    mr = gen._LF_RARITY_RE.search(cond_part)
    mq = gen._LF_QUALITY_RE.search(cond_part)
    ms = gen._LF_SOCKETS_RE.search(cond_part)
    msg = gen._LF_SOCKETS_GT_RE.search(cond_part)
    mc = gen._LF_CATEGORY_RE.search(cond_part)
    sockets = None
    if ms:
        sockets = int(ms.group(1))
    elif msg:
        sockets = int(msg.group(1)) + 1
    mi = _ILVL_RE.search(cond_part)
    # WaystoneTier is PoE 2 only; MapTier is its PoE 1 counterpart.
    mw = None if poe1 else _WTIER_RE.search(cond_part)
    mt = _MTIER_RE.search(cond_part) if poe1 else None

    # A KNOWN token our regexes couldn't read is still a dropped condition, and
    # it used to vanish silently: "unknown" only collects tokens we don't
    # recognise, so a rule whose [ItemLevel] was written unquoted, or with an
    # operator we don't parse, was reported as "converted, 0 shown wider" while
    # the gate was gone from the filter. Every one of these widens the rule, so
    # the report has to say so — that honesty IS the feature.
    #
    # Two shapes count: the token is present but nothing parsed, and the token
    # appears more times than we took (e.g. an ItemLevel floor AND a ceiling —
    # .search only ever returns the first).
    present = _TOKEN_RE.findall(cond_part)
    seen: dict = {}
    for t in present:
        seen[t] = seen.get(t, 0) + 1
    # Type and Category belong here too. They are in _KNOWN_TOKENS, so an
    # unreadable one never reached "unknown" either, and fell through BOTH nets:
    # `[Category] != "Flask" && [Rarity] == "Rare"` emitted a bare `Rarity = Rare`
    # — every Rare item in the game — while reporting 0 shown wider. Same for a
    # two-word category the \w+ pattern can't read, and for `[Type] != ...`.
    parsed = {"ItemLevel": 1 if mi else 0,
              "WaystoneTier": 1 if mw else 0,
              "Quality": 1 if mq else 0,
              "Sockets": 1 if (ms or msg) else 0,
              "Rarity": 1 if mr else 0,
              "Type": len(names),
              "Category": 1 if mc else 0}
    if poe1:
        parsed.pop("WaystoneTier")
        parsed["MapTier"] = 1 if mt else 0
        parsed["UniqueName"] = len(uniques)
    unparsed = sorted(t for t, n in parsed.items() if seen.get(t, 0) > n)
    known = _KNOWN_TOKENS_POE1 if poe1 else _KNOWN_TOKENS

    return {
        "names": names,
        "rarity": mr.group(1) if mr else None,
        "quality": int(mq.group(1)) if mq else None,
        "sockets": sockets,
        "category": mc.group(1) if mc else None,
        # ready-to-emit filter fragments (or None) — exact translations
        "ilvl": f"ItemLevel {mi.group(1)} {mi.group(2)}" if mi else None,
        # one slot for the tier gate: WaystoneTier (PoE 2) or MapTier (PoE 1)
        "wtier": (f"WaystoneTier {mw.group(1)} {mw.group(2)}" if mw else
                  f"MapTier {mt.group(1)} {mt.group(2)}" if mt else None),
        "uniques": uniques,
        "unknown": sorted(set(present) - known),
        "unparsed": unparsed,
    }


def convert_pickit_text(text: str, hide_rest: bool = False,
                        source_name: str = "",
                        theme: str = gen.DEFAULT_FILTER_THEME,
                        game: str = "poe2",
                        unique_bases: dict | None = None) -> dict:
    """Parse pickit text and return ``{"ok", "filter_lines", "report"}``.

    ``game`` picks the filter language (``"poe1"`` or ``"poe2"``).
    ``unique_bases`` (PoE 1) maps a unique's name to its base type, so an
    Exiled Bot 1 ``[UniqueName] == "X"`` rule becomes ``Rarity Unique`` +
    ``BaseType`` — a filter cannot name a unique. A unique missing from it is
    still shown, through one wide "every unique" block, never dropped.

    Never raises on bad input — unreadable lines are counted and listed, and
    a file with no usable rules returns ``ok=False`` with the report intact.
    ``theme`` picks the label style set; unknown values fall back to the
    default theme inside the lookup.
    """
    # (visual kind, rarity, quality, sockets, ilvl, wtier) -> names — exact.
    named_groups: dict = {}
    generic: list = []        # (visual kind, conditions)

    rules = converted = widened = disabled = assumed_pickup = 0
    untranslatable: list = []
    untranslatable_total = 0
    poe1 = game == "poe1"
    cat_class = _CATEGORY_CLASS_POE1 if poe1 else _CATEGORY_CLASS
    ubases = unique_bases or {}
    unresolved_uniques: list = []   # PoE 1 uniques with no known base
    visual_counts: dict = {}
    visual_examples: dict = {}

    def _record_visual(kind, names):
        visual_counts[kind] = visual_counts.get(kind, 0) + 1
        bucket = visual_examples.setdefault(kind, [])
        for name in names:
            if name and name not in bucket and len(bucket) < 3:
                bucket.append(name)

    def _flag(no, line, reason):
        nonlocal untranslatable_total
        untranslatable_total += 1
        if len(untranslatable) < _MAX_LISTED:
            untranslatable.append({"line": no, "text": line[:160],
                                   "reason": reason})

    if not isinstance(text, str):
        text = ""
    text_lines = text.splitlines()
    divine_rate = extract_divine_rate(text_lines)
    section = None
    # The #1 real-world misuse: an in-game .filter renamed to .ipd (players
    # try to convert FilterBlade filters INTO pickits — this page goes the
    # other way). Detect the filter language so the UI can explain direction
    # instead of a generic "nothing converted".
    looks_like_filter = bool(
        re.search(r"^\s*(Show|Hide)\s*(#.*)?$", text, re.M)
        and re.search(r"^\s*(BaseType|Class|SetTextColor|SetFontSize)\b",
                      text, re.M))
    for no, raw in enumerate(text_lines, 1):
        line = raw.strip().lstrip("﻿")   # a BOM is not part of a comment marker
        if not line:
            continue
        heading = section_from_comment(line)
        if heading:
            section = heading
        if line.startswith("/"):
            # Only a commented-out RULE counts as disabled. Counting every "//"
            # line made the report claim 202 disabled rules for a file that had
            # none — those were all section headers and the banner.
            #
            # The embedded syntax guide (written into every generated .ipd since
            # v4.41.18) then reintroduced the same lie from the other side: its
            # worked examples and its Special Flags legend are comments that DO
            # carry an action/type, so a clean pickit reported "11 disabled"
            # when nothing was switched off. Those are documentation, not rules.
            if (not _is_guide_line(line)
                    and (gen._LF_ACTION_RE.search(line)
                         or gen._LF_TYPE_RE.search(line))):
                disabled += 1
            continue
        rules += 1
        cond_part = _pickup_half(line)
        if not gen._LF_ACTION_RE.search(line):
            # No recognised action — include it anyway. Showing an extra item
            # is harmless; hiding one the bot wanted is not.
            assumed_pickup += 1
        r = _parse_rule(cond_part, game)
        kind = classify_rule(line, section, divine_rate)
        # "wide": a check was dropped, so the filter shows MORE than the rule.
        # Counted only for rules that actually make it into the filter.
        # "unparsed" matters as much as "unknown": a condition we recognise but
        # could not read is just as gone from the output as one we never knew.
        wide = bool(r["unknown"] or r["unparsed"])
        rarity = r["rarity"]
        if rarity and rarity not in _VALID_RARITIES:
            rarity = None
            wide = True
        bad_names = [n for n in r["names"]
                     if any(ch in n for ch in _UNEXPRESSIBLE)]
        names = [n for n in r["names"] if n and n not in bad_names]
        if r["uniques"]:
            # Exiled Bot 1 names a unique; a filter can only match its base.
            # Other uniques share that base, so the label is wider than the
            # rule — counted as "shown wider", which is the honest word.
            rarity = "Unique"
            wide = True
            for u in r["uniques"]:
                base = ubases.get(u)
                if base and not any(ch in base for ch in _UNEXPRESSIBLE):
                    names.append(base)
                else:
                    unresolved_uniques.append(u)
            if not names:
                _record_visual(kind, r["uniques"])
                converted += 1
                widened += 1
                continue

        if bad_names:
            # The lost name can never be expressed — the rule counts as
            # untranslatable (so a Hide gets the loud warning), but any
            # expressible sibling names on the same line still get shown.
            if names:
                key = (kind, rarity, r["quality"], r["sockets"], r["ilvl"], r["wtier"])
                named_groups.setdefault(key, []).extend(names)
                _record_visual(kind, names)
            _flag(no, line, "an item name on this line contains '#' or '\"' — "
                            "a filter string can't carry that name")
            continue
        if names:
            key = (kind, rarity, r["quality"], r["sockets"], r["ilvl"], r["wtier"])
            named_groups.setdefault(key, []).extend(names)
            _record_visual(kind, names)
            converted += 1
            if wide:
                widened += 1
            continue
        conds = []
        if r["category"]:
            classes = cat_class.get(r["category"].lower())
            if classes:
                conds.append("Class == " + " ".join(f'"{c}"' for c in classes))
            else:
                wide = True   # category dropped — whatever remains shows wider
        if rarity:
            conds.append(f"Rarity = {rarity}")
        if r["sockets"] is not None:
            conds.append(f"Sockets >= {r['sockets']}")
        if r["quality"] is not None:
            conds.append(f"Quality >= {r['quality']}")
        if r["ilvl"]:
            conds.append(r["ilvl"])
        if r["wtier"]:
            conds.append(r["wtier"])
        if conds:
            generic.append((kind, conds))
            label = r["category"] or rarity or "Condition-only rule"
            _record_visual(kind, [label])
            converted += 1
            if wide:
                widened += 1
            continue
        reason = (f"category \"{r['category']}\" has no filter equivalent"
                  if r["category"] else "no conditions a filter can express")
        _flag(no, line, reason)

    # ok = something actually made it into the filter (a partially-translated
    # rule can emit sibling names without counting as converted).
    ok = bool(named_groups or generic or unresolved_uniques)
    # Hide means hide (owner's call): when requested it is always applied.
    # If rules couldn't be translated, their items may be hidden in game even
    # though the bot still picks them up — that risk is surfaced loudly in the
    # report and in the filter itself instead of refusing to hide.
    hide_applied = bool(hide_rest and ok)
    hide_risky = bool(hide_applied and untranslatable_total)

    src = source_name or "pickit"
    out: list = [
        f"# Path of Exile {'1' if poe1 else '2'} filter — made from {src} "
        "by Exiled Bot Pickit Generator",
        "# Shows every item the pickit could take (pickup conditions only).",
        "# Bot-only checks (mods, tiers, values) can't exist in a filter, so",
        "# those rules are shown a little wider — never narrower.",
        "# Appearance tiers are filter-only; they never change what the bot picks.",
        f"# Generated on: {time.strftime('%Y-%m-%dT%H:%M:%S')}",
        "",
    ]
    th = threshold_summary(divine_rate)
    u = "c" if poe1 else "ex"      # PoE 1 prices are Chaos, PoE 2 Exalted
    out += [
        f"# Value ladder: Mythic >= {th['mythic']:.2f} {u} | "
        f"Jackpot >= {th['jackpot']:.2f} {u} | High >= {th['high']:.2f} {u} | "
        f"Useful >= {th['useful']:.2f} {u} | Quiet below that",
        "",
    ]
    # Named rules translate EXACTLY: every recognised condition on the line
    # (rarity + quality + sockets, in any combination) rides along with the
    # names — nothing silently dropped.
    def _grp_key(k):
        kind, rar, q, s, il, wt = k
        return (visual_sort_key(kind), rar or "",
                -1 if q is None else q, -1 if s is None else s,
                il or "", wt or "")

    for key in sorted(named_groups, key=_grp_key):
        kind, rar, q, s, il, wt = key
        extra = []
        if rar:
            extra.append(f"Rarity = {rar}")
        if q is not None:
            extra.append(f"Quality >= {q}")
        if s is not None:
            extra.append(f"Sockets >= {s}")
        if il:
            extra.append(il)
        if wt:
            extra.append(wt)
        style = gen.filter_theme_style(theme, kind)
        out += gen._lf_show_blocks(named_groups[key], extra, style_lines=style)
    seen_generic = set()
    for kind, conds in sorted(generic, key=lambda row: visual_sort_key(row[0])):
        key = kind, tuple(conds)
        if not conds or key in seen_generic:
            continue
        seen_generic.add(key)
        out += gen._lf_styled_block(conds, gen.filter_theme_style(theme, kind))

    if unresolved_uniques:
        # Uniques whose base we could not look up (no cached poe.ninja
        # prices yet, or a hand-written name). Show every unique rather than
        # risk hiding one the bot wants: wider, never narrower. Placed after
        # the exact blocks so priced uniques keep their own tier look.
        out += ["# Uniques the pickit names but whose base type is unknown "
                f"({len(set(unresolved_uniques))}) — every unique is shown"]
        out += gen._lf_styled_block(["Rarity = Unique"],
                                    gen.filter_theme_style(theme, "unique"))

    if hide_applied:
        # Safety: gold must never be hidden — bots grab it regardless of the
        # pickit, and no player wants it invisible. BaseType verified against
        # NeverSink's live SOFT filter.
        out += gen._lf_gold_guard(gen.filter_theme_style(theme, "gold"))
        if hide_risky:
            out += [f"# WARNING: {untranslatable_total} pickit rule(s) couldn't be "
                    "translated — items only those rules match",
                    "# will be HIDDEN in game, even though the bot still picks them up.",
                    ""]
        out += ["# Hide everything else", "Hide", ""]

    return {
        "ok": ok,
        "filter_lines": out if ok else [],
        "report": {
            "looks_like_filter": looks_like_filter and not ok,
            "rules": rules,
            "converted": converted,
            "widened": widened,
            "disabled": disabled,
            "assumed_pickup": assumed_pickup,
            "untranslatable_total": untranslatable_total,
            "untranslatable": untranslatable,
            "hide_applied": hide_applied,
            "hide_risky": hide_risky,
            "game": "poe1" if poe1 else "poe2",
            "unresolved_uniques": len(set(unresolved_uniques)),
            "visual_tiers": visual_report(visual_counts, visual_examples),
            "visual_thresholds": th,
        },
    }
