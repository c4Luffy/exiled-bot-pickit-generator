"""Single source of truth for the app version."""
VERSION = "4.59.0"
# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• Create your filter is back in PoE 1, and now writes a real PoE 1 filter. It was hidden in v4.47.0 because the converter only spoke PoE 2. It now writes Path of Exile 1's own vocabulary: PoE 1 item classes, MapTier instead of WaystoneTier, and Chaos prices on the value ladder. Every class and condition it can write was checked against NeverSink's live PoE 1 filter.

• Exiled Bot 1's [UniqueName] rules get a label. A loot filter cannot name a unique, only its base, so each unique is matched as Rarity Unique + its base type, read from the cached poe.ninja prices. Other uniques on the same base get the label too, and the report counts those rules as "shown wider". A unique with no cached base is still shown, through one "every unique" block — never dropped.

• Saving starts in the PoE 1 filter folder ("My Games/Path of Exile").

• Converting a real generated PoE 1 pickit: 2,958 of 2,958 rules translated, none untranslatable, every unique's base found. PoE 2 conversion is unchanged.

Also in 4.58.1:

• Charts are no longer always picked. Coral Forest, Coral Reef and Sandy Seabed Charts (Fathomless Depths) were removed from Path of Exile 1, so generated PoE 1 pickits no longer write rules for them, and the Economy tab's PoE 1 "Always pick → Charts" group is gone. PoE 2 is unchanged.
"""
