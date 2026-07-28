"""Single source of truth for the app version."""
VERSION = "4.52.0"
# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• It has its own tab now, instead of a card buried under History's charts. The session's value leads — a single large figure with what made it up underneath — then the "is the bot running your pickit" verdict, then four tiles (picked up / sold / pickit rules loaded / map rules loaded), then the itemised list. Before the bot has ever run it explains itself and offers the Settings button rather than showing a blank tab. ### From the full audit

• Concurrent writes could fail outright, and a unique temp name was only half the fix. Five places still swapped through a shared <target>.tmp — the pickit and map runner copied into the bot folder, the bot's config.ini, the remote game-data cache. Worse, reproducing the collision showed os.replace itself raises PermissionError on Windows when a second writer holds the destination for an instant, so even the paths that already used unique temps (the .ipd, the price cache) could silently not be written. Every writer now uses a unique temp and retries the swap. Five tests reproduce the race with concurrent threads instead of trusting the fix.

• Verified clean and unchanged: quote escaping on every rule builder that interpolates a poe.ninja name, no type-less [StashItem] rule in a full generate, the anchored backup-name matcher at all seven call sites, save_config reporting the real outcome, game_data.json against the code, and the stat ids and weights against the live patch.

• CLAUDE.md's page list was stale again — the file that warns "this list has gone stale before" was missing p-maps and p-bot.

Also in 4.51.2:

• The pickup list priced gems at their best variant, not the one that dropped. v4.50.0 fixed this for the rules but the History panel kept its own lookup, which took poe.ninja's first row per name — and poe.ninja sorts dearest-first. So a Stormbind the bot scooped off the ground was reported at 124.10c, the value of the single listed level-21/quality-23 corrupted copy, while the rule beside it correctly said 1c. A real session's haul read 134.1c when it was worth 2c.

• There is now one definition of "what is this worth as it drops" (drop_value_index), used both to write the rules and to show the prices, so the two can no longer disagree. A test asserts they match. Categories that list one row per name are unaffected.
"""
