"""Single source of truth for the app version."""
VERSION = "4.51.2"
# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• The pickup list priced gems at their best variant, not the one that dropped. v4.50.0 fixed this for the rules but the History panel kept its own lookup, which took poe.ninja's first row per name — and poe.ninja sorts dearest-first. So a Stormbind the bot scooped off the ground was reported at 124.10c, the value of the single listed level-21/quality-23 corrupted copy, while the rule beside it correctly said 1c. A real session's haul read 134.1c when it was worth 2c.

• There is now one definition of "what is this worth as it drops" (drop_value_index), used both to write the rules and to show the prices, so the two can no longer disagree. A test asserts they match. Categories that list one row per name are unaffected.

Also in 4.51.1:

• The value columns showed a dash on every visible row. The list was sorted by how many of each item the bot took, so a real session opened with ten Portal Scrolls and four Orbs of Alteration — none of which poe.ninja prices — while the single Stormbind carrying 124 of the run's 134 chaos sat below the fold. The two columns added last release therefore looked broken, and fairly so. Sorted by what the pickups were worth now, so the rows that paid for the session are the ones you see.

• An unpriced item shows a dash, not 0.00. A column of zeroes reads as a broken table rather than "poe.ninja does not price Portal Scrolls". Anything real but under a hundredth now reads <0.01 instead of rounding itself away to nothing.

• The line above the table says the order and what a dash means.
"""
