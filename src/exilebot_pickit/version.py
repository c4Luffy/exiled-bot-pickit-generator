"""Single source of truth for the app version."""
VERSION = "4.50.2"
# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• The in-app "What's new" showed every release ever. It was prepended by hand each time and never pruned, so it had reached 53,000 characters and 63 "Also in" sections reaching back to v4.38.0 — all of it compiled into the exe and poured into one dialog. Its ordering had drifted too (v4.48.4 sat above v4.50.0). It now shows the two most recent releases, generated from the CHANGELOG by tools/build_highlights.py as part of the release, so it is correct by construction and cannot grow again. 53,695 characters to 2,327.

• The repo offered four issue templates. A YAML form and a legacy markdown template existed for both bug and feature, so filing an issue showed two "Bug" choices and two "Feature" choices. The markdown pair is gone, and a config.yml now points questions at Discord instead of the tracker.

• The bug template gave instructions that do not work. It said to find your version under "Help → About", which the app does not have, and suggested v2.6.21 as an example while the app is on v4.50.x. It now points at the sidebar, notes that the .exe filename deliberately never changes, and its reproduction example uses tabs that still exist. Audited but found current: game_data.json (the drift checker reports 0 critical / 0 advisory against the live patch), and both runtime dependency ranges, which already admit the newest requests and pywebview.

Also in 4.50.1:

• The bot-activity table headers were a puzzle. "Times / Each / Worth" left you guessing — "each" reads just as naturally as the count as it does as the unit price. They are now How many (shown as ×10), Price each and Total, with the currency named once in the header so the cells stay clean, and a line above the table saying what it is. The haul tile names its unit too, instead of hardcoding "chaos" in a dual-game app.
"""
