"""Single source of truth for the app version."""
VERSION = "4.55.1"
# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• Charts had nowhere in the app to see or switch them. v4.55.0 wrote the three rules into the pickit and stopped there, so the only way to find them was to search Preview, and the only way to turn one off was to edit the file. Every visible surface in this app is driven by poe.ninja prices and Charts have none — but "no price" is a poor reason for "invisible".

• They are now their own Charts category in the Economy sidebar, the same always-pick shape PoE 2 uses for its unpriced groups: each chart is a row reading "No price · always kept", and switching one off comments that rule out of the pickit like any other.

• The always-pick machinery was PoE 2-only in three places (the sidebar build, the category-enabled map, and the disabled-name walk), so a Path of Exile 1 group could be defined and still never appear — or appear and have its switches ignored. All three now use the active game's groups, with a test for the toggle actually reaching the written rules.

Also in 4.55.0:

• Charts are picked up. Path of Exile 1's Fathomless Depths mechanic — item class DeepwaterChart, brought to Valerie to explore the Depths and combined on the Voyage Board. Three bases: Coral Forest Chart, Coral Reef Chart, Sandy Seabed Chart, all confirmed drop-enabled in the game's own item table. poe.ninja does not price this category — there is no Chart type on its PoE 1 economy API, and none of the 28 categories the app fetches carries one — so unlike every other section these cannot be valued or floored. They are taken on sight, and the file says so above the rules. When poe.ninja starts pricing them this becomes a normal priced category.

• The map-tier notice from v4.51.0 never ran. It was written into _generate, which hands off to _generate_poe1 on its second line for an economy-only game — and maps are Path of Exile 1 only. So the notice sat in code that game never reaches, and every test passed because they all checked the wording of a helper nothing called. It now lives in the PoE 1 path where maps actually are, and a test asserts it is wired in rather than merely well-worded.
"""
