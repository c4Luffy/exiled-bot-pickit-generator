"""Single source of truth for the app version."""
VERSION = "4.55.0"
# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• Charts are picked up. Path of Exile 1's Fathomless Depths mechanic — item class DeepwaterChart, brought to Valerie to explore the Depths and combined on the Voyage Board. Three bases: Coral Forest Chart, Coral Reef Chart, Sandy Seabed Chart, all confirmed drop-enabled in the game's own item table. poe.ninja does not price this category — there is no Chart type on its PoE 1 economy API, and none of the 28 categories the app fetches carries one — so unlike every other section these cannot be valued or floored. They are taken on sight, and the file says so above the rules. When poe.ninja starts pricing them this becomes a normal priced category.

• The map-tier notice from v4.51.0 never ran. It was written into _generate, which hands off to _generate_poe1 on its second line for an economy-only game — and maps are Path of Exile 1 only. So the notice sat in code that game never reaches, and every test passed because they all checked the wording of a helper nothing called. It now lives in the PoE 1 path where maps actually are, and a test asserts it is wired in rather than merely well-worded.

Also in 4.54.0:

• A category's value floor came from which poe.ninja endpoint it uses, not from what it is. The is_unique flag on a category answers "stash endpoint or exchange endpoint" — the Precursor Tablets entry says so in its own comment, "purely for endpoint routing: this is not a real unique category" — but effective_min() also used it to choose between the items floor and the unique floor. So eight ordinary categories sat behind the unique floor: Precursor Tablets, and in Path of Exile 1 skill gems, beasts, incubators, vials, cluster jewels, invitations and maps. Reported from a real setup: with a 100 ex unique floor, tablets worth 75-90 ex were written commented out while the Economy tab showed them kept. On that setup the fix takes tablets from 9 of 21 rules active to all 21.

• The floor is now chosen from the category key, which is the honest signal and the same test the Path of Exile 1 rule writer already uses to decide between [UniqueName] and [Type]. Real uniques are unaffected.

• Maps had a one-off workaround for exactly this, added when the same problem was noticed for them alone. It is gone — every stash-routed category now gets the right floor for free, and a new test fails if a future category is added with the same conflation.
"""
