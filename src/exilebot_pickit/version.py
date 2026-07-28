"""Single source of truth for the app version."""
VERSION = "4.51.1"
# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• The value columns showed a dash on every visible row. The list was sorted by how many of each item the bot took, so a real session opened with ten Portal Scrolls and four Orbs of Alteration — none of which poe.ninja prices — while the single Stormbind carrying 124 of the run's 134 chaos sat below the fold. The two columns added last release therefore looked broken, and fairly so. Sorted by what the pickups were worth now, so the rows that paid for the session are the ones you see.

• An unpriced item shows a dash, not 0.00. A column of zeroes reads as a broken table rather than "poe.ninja does not price Portal Scrolls". Anything real but under a hundredth now reads <0.01 instead of rounding itself away to nothing.

• The line above the table says the order and what a dash means.

Also in 4.51.0:

• Map tiers default to T16 alone, and nothing said so. Maps are the one category whose scope is a selection rather than a value floor, so a new user generated, saw a cheerful ✓ Maps in the run log, and their bot then walked past every T1-T15 map on the ground — which reads as "the app does not do maps". The run now names the tiers it actually wrote (✓ Maps: T16), and when the selection is narrow enough to look like nothing it adds that every other tier is left on the ground and where to change it. An empty selection says so outright instead of passing silently.

• The default itself is unchanged. It is deliberate — the Maps tab argues that "tier 1 and up" is the single biggest cause of a full stash — so the fix is to stop being silent about it, not to flip it.
"""
