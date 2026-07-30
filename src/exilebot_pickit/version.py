"""Single source of truth for the app version."""
VERSION = "4.57.0"
# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• Rare jewels are now scored like every other slot. Magic & Rare gains an 18th slot, Jewel, covering the three droppable bases — Sapphire, Emerald and Ruby — with a 14-stat WeightedSum: max Energy Shield, Triggered Spell Damage, Elemental / Spell / Lightning / Projectile Damage, Ailment Magnitude, Projectile Speed, Crit Damage Bonus, Spell Crit Damage, chance to Pierce, Crit Chance, Spell Crit Chance and Cast Speed. Every id and every T1 max-roll was read from the live GGPK mod dump, not a wiki.

• Jewels carry no [ItemTier], so the Jewel slot writes no tier gate. Every other slot gates on [ItemTier] >= "4"; emitting that against a property the item does not have is the silent way to write a rule that never matches, so item_tier is now optional and the tab shows "—" for it.

• The game-data checker was blind to jewels entirely. Jewel affixes and jewel bases live in the GGPK's misc domain, and the checker filtered on domain == "item" — so the moment the Jewel recipe landed it reported the three real bases as "isn't in the game at all" and two ordinary jewel prefixes as removed. Twelve more stat ids had been passing only because the same id also rolls on equipment. It now indexes jewel-domain mods and bases, and reports 0 critical / 0 advisory again.

• Two dead stat ids corrected on the way in: projectile_speed_+% does not exist in the game (the real id is base_projectile_speed_+%), and recover_%_maximum_mana_on_kill is real but never rolls on a jewel. Both score zero forever with no error — the exact failure mode this repo's checker exists to catch.

• The embedded syntax guide now documents [UniqueName]. It is read after the # (the name is only known once the item is identified), which the guide never said. It also documents the disenchant idiom from Exiled Bot's own default.ipd: [Rarity] == "Unique" # [UniqueName] == "PICK ME AND DISENCHANT ME" uses a name that can never match on purpose — the pickup half takes every unique, nothing is stashed by that rule, and any unique no other rule kept is left to disenchant for Chance Shards. Both new lines are written as Example: comments — the disabled-rule counter only exempts that exact prefix, so any other wording would have shown up as rules you had switched off.

Also in 4.56.0:

• The Charts category was buried. Its key is _charts, and the Economy sidebar groups by an _ap_ prefix — so it fell through to "General" and landed 29 entries down, below the fold of the rail, while the section it belongs to did not appear at all. Confirmed by querying the running UI rather than reasoning about it: the sidebar read GENERAL 22 | EQUIPMENT 7 with Charts as General's last row.

• "Always pick" now sits first. It used to be last, after poe.ninja's three sections, on the reasoning that it is this app's own addition rather than theirs. But it is also the smallest group and the one nothing else points at, so it was the hardest to reach. poe.ninja's General / Equipment / Atlas keep their exact order after it.

• Charts have their real item art, embedded in the exe like every other icon so it works offline. poe.ninja carries no Chart category, so there is no payload icon to fall back on and the rows had been drawing a generic emoji.
"""
