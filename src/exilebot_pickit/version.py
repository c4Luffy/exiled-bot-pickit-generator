"""Single source of truth for the app version."""
VERSION = "4.56.0"
# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• The Charts category was buried. Its key is _charts, and the Economy sidebar groups by an _ap_ prefix — so it fell through to "General" and landed 29 entries down, below the fold of the rail, while the section it belongs to did not appear at all. Confirmed by querying the running UI rather than reasoning about it: the sidebar read GENERAL 22 | EQUIPMENT 7 with Charts as General's last row.

• "Always pick" now sits first. It used to be last, after poe.ninja's three sections, on the reasoning that it is this app's own addition rather than theirs. But it is also the smallest group and the one nothing else points at, so it was the hardest to reach. poe.ninja's General / Equipment / Atlas keep their exact order after it.

• Charts have their real item art, embedded in the exe like every other icon so it works offline. poe.ninja carries no Chart category, so there is no payload icon to fall back on and the rows had been drawing a generic emoji.

Also in 4.55.1:

• Charts had nowhere in the app to see or switch them. v4.55.0 wrote the three rules into the pickit and stopped there, so the only way to find them was to search Preview, and the only way to turn one off was to edit the file. Every visible surface in this app is driven by poe.ninja prices and Charts have none — but "no price" is a poor reason for "invisible".

• They are now their own Charts category in the Economy sidebar, the same always-pick shape PoE 2 uses for its unpriced groups: each chart is a row reading "No price · always kept", and switching one off comments that rule out of the pickit like any other.

• The always-pick machinery was PoE 2-only in three places (the sidebar build, the category-enabled map, and the disabled-name walk), so a Path of Exile 1 group could be defined and still never appear — or appear and have its switches ignored. All three now use the active game's groups, with a test for the toggle actually reaching the written rules.
"""
