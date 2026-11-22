"""Single source of truth for the app version."""
VERSION = "4.58.1"
# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• Charts are no longer always picked. Coral Forest, Coral Reef and Sandy Seabed Charts (Fathomless Depths) were removed from Path of Exile 1, so generated PoE 1 pickits no longer write rules for them, and the Economy tab's PoE 1 "Always pick → Charts" group is gone. PoE 2 is unchanged.

Also in 4.58.0:

• Fourteen priced PoE 1 categories were never fetched. Checked against poe.ninja's own PoE 1 sidebar (Covens league, 2026-11-23): Djinn Coins, Ducats, Enshrouding Crystals, Astrolabes, Threads, Wombgifts, Corpses, Viscera, Temples, Memories, Scrying Orbs, Forbidden Jewels, Shrine Belts and Unique Tinctures had no rule at any floor — a 3,560c Perfect Forest Tiger corpse, a 333c Merrick's Ducat and every ~160c temple were walked past.

• Variant-priced categories use one median rule. Temples (84 room layouts, one "Chronicle of Atzoatl" base), Scrying Orbs, Forbidden Flame/Flesh (165 passives each), Viscera, Wombgifts and Shrine Belts are priced per variant the bot cannot read, so each base or unique gets one rule at the median of its variants — the same rule cluster jewels use — and the Economy tab lists those same names and prices.

• Left out on purpose: Imbued Gems (the gem name is already a Skill Gems rule), Blighted / Blight-ravaged Maps (same "Map (Tier N)" base, covered by the Maps tiers), Valdo Maps (made in your inventory, never dropped) and Base Types / Flasks (priced by item level and influence — one name rule would pick up every white copy).

• Turning off currency pickup keeps prices for everything else. Other categories still get their Divine rate and values when Currency is off.

• The game switch explains itself. While a generate or price lookup runs it says why it is unavailable, and if the new choice cannot be saved the current game stays selected instead of half-switching.

• Scheduled runs use the selected game's league and currency, older PoE 1 map-tier selections carry forward, and startup keeps existing latest.ipd files.

• Generate and Economy recover from failures. Generate gives its controls back when a request fails or its status cannot be read, and Economy offers a retry when prices fail to start loading.
"""
