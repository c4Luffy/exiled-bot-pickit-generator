"""Translate Exiled Bot 1 pickup conditions to Path of Exile filter conditions."""

import re

from exilebot_pickit.data.poe1_unique_bases import UNIQUE_BASES

_RULE = re.compile(r'\s*\[(\w+)\]\s*(==|!=|>=|<=|>|<|=)\s*"((?:[^"\\]|\\.)*)"\s*')
_MAP_ACTION = re.compile(r"\[(?:RunMap|IgnoreMap|UpgradeMapTier|UpgradeToRare|UpgradeToMagic|UpgradeQuality)\]", re.I)
_NUMBER = {
    "itemlevel": "ItemLevel", "quality": "Quality", "sockets": "Sockets",
    "linked": "LinkedSockets", "maptier": "MapTier", "gemlevel": "GemLevel",
    "stacksize": "StackSize",
}
_CLASS = {
    "map": "Maps", "helmet": "Helmets", "bodyarmour": "Body Armours",
    "gloves": "Gloves", "boots": "Boots", "ring": "Rings", "amulet": "Amulets",
    "belt": "Belts", "jewel": "Jewels", "quiver": "Quivers", "shield": "Shields",
    "wand": "Wands", "staff": "Staves", "bow": "Bows", "sceptre": "Sceptres",
}
_RARITIES = {"normal": "Normal", "magic": "Magic", "rare": "Rare", "unique": "Unique"}


def pickup_conditions(line, pickup, unique_bases):
    """Return (names, filter conditions, widened, error) for one pickup rule."""
    if _MAP_ACTION.search(line[len(pickup):].split("//", 1)[0]):
        return [], [], False, "map-runner actions do not describe loot pickups"

    tests = []
    pos = 0
    while True:
        match = _RULE.match(pickup, pos)
        if not match:
            return [], [], False, "unsupported condition syntax"
        key, op, value = match.groups()
        tests.append((key.casefold(), op, value))
        pos = match.end()
        if pos == len(pickup) or pickup.startswith("//", pos):
            break
        if pickup[pos:pos + 2] != "&&":
            return [], [], False, "unsupported condition grouping or OR"
        pos += 2

    names, conditions = [], []
    wide = False
    # Work out explicit base constraints before resolving a unique name.
    for key, op, value in sorted(tests, key=lambda test: test[0] != "type"):
        equal = op in ("==", "=")
        filter_op = "=" if equal else op
        if key == "type" and equal:
            if not value or any(ch in value for ch in '#"\\'):
                return [], [], False, "item name cannot be written in a filter"
            else:
                if names and value not in names:
                    return [], [], False, "multiple different base names joined by AND"
                names = [value]
        elif key == "uniquename" and equal:
            key_name = value.casefold()
            bases = set(UNIQUE_BASES.get(key_name, ())) | set(unique_bases.get(key_name, ()))
            if not bases:
                return [], [], False, f'unknown PoE1 unique base for "{value}"'
            names = sorted(name for name in bases if not names or name in names)
            if not names:
                return [], [], False, f'base name conflicts with unique "{value}"'
            conditions.append("Rarity = Unique")
            wide = True  # the client can show other uniques on the same base
        elif key == "category" and equal and value.casefold() in _CLASS:
            conditions.append(f'Class == "{_CLASS[value.casefold()]}"')
        elif key == "rarity" and value.casefold() in _RARITIES:
            conditions.append(f"Rarity {filter_op} {_RARITIES[value.casefold()]}")
        elif key in _NUMBER and value.isascii() and value.isdecimal():
            conditions.append(f"{_NUMBER[key]} {filter_op} {value}")
        elif key in ("identified", "corrupted") and equal and value.casefold() in ("true", "false"):
            conditions.append(f"{key.title()} {value.title()}")
        else:
            wide = True
    return names, list(dict.fromkeys(conditions)), wide, ""
