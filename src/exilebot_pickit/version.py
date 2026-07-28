"""Single source of truth for the app version."""
VERSION = "4.51.0"
# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• Map tiers default to T16 alone, and nothing said so. Maps are the one category whose scope is a selection rather than a value floor, so a new user generated, saw a cheerful ✓ Maps in the run log, and their bot then walked past every T1-T15 map on the ground — which reads as "the app does not do maps". The run now names the tiers it actually wrote (✓ Maps: T16), and when the selection is narrow enough to look like nothing it adds that every other tier is left on the ground and where to change it. An empty selection says so outright instead of passing silently.

• The default itself is unchanged. It is deliberate — the Maps tab argues that "tier 1 and up" is the single biggest cause of a full stash — so the fix is to stop being silent about it, not to flip it.

Also in 4.50.2:

• The in-app "What's new" showed every release ever. It was prepended by hand each time and never pruned, so it had reached 53,000 characters and 63 "Also in" sections reaching back to v4.38.0 — all of it compiled into the exe and poured into one dialog. Its ordering had drifted too (v4.48.4 sat above v4.50.0). It now shows the two most recent releases, generated from the CHANGELOG by tools/build_highlights.py as part of the release, so it is correct by construction and cannot grow again. 53,695 characters to 2,327.

• The repo offered four issue templates. A YAML form and a legacy markdown template existed for both bug and feature, so filing an issue showed two "Bug" choices and two "Feature" choices. The markdown pair is gone, and a config.yml now points questions at Discord instead of the tracker.

• The bug template gave instructions that do not work. It said to find your version under "Help → About", which the app does not have, and suggested v2.6.21 as an example while the app is on v4.50.x. It now points at the sidebar, notes that the .exe filename deliberately never changes, and its reproduction example uses tabs that still exist. Audited but found current: game_data.json (the drift checker reports 0 critical / 0 advisory against the live patch), and both runtime dependency ranges, which already admit the newest requests and pywebview.
"""
