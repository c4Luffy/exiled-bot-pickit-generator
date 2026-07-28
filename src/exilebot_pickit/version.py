"""Single source of truth for the app version."""
VERSION = "4.53.0"
# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• Bot Activity now keeps a per-session history. The bot overwrites lastrun.log every time it starts, so what the previous session earned was gone the moment the next one began — the tab could only ever describe the session running now. Each session is snapshotted under its start timestamp and updated in place while it grows, giving a table of every session (items, sold, earned) and a career total beside the current one.

• A read taken before prices load can no longer erase what a session earned. The price lookup reads a cache that is empty until the Economy tab or a generate has warmed it, so an early read values every pickup at zero — and writing that over an already-recorded session wiped the figure. Seen live: a session recorded at 2.0c came back as 0.0c after one cold read. The earnings figure now only moves when the read actually had prices.

• The history is per game (the two are different bot installs), capped at 60 sessions so it cannot grow the config without bound, and an unchanged session does not rewrite the config on every visit to the tab.

• Honest about its limit, in the tab itself: a session is only captured while the app can still see it. If the app is closed for a whole session, that one cannot be recovered — the bot has already overwritten the file.

Also in 4.52.0:

• It has its own tab now, instead of a card buried under History's charts. The session's value leads — a single large figure with what made it up underneath — then the "is the bot running your pickit" verdict, then four tiles (picked up / sold / pickit rules loaded / map rules loaded), then the itemised list. Before the bot has ever run it explains itself and offers the Settings button rather than showing a blank tab. ### From the full audit

• Concurrent writes could fail outright, and a unique temp name was only half the fix. Five places still swapped through a shared <target>.tmp — the pickit and map runner copied into the bot folder, the bot's config.ini, the remote game-data cache. Worse, reproducing the collision showed os.replace itself raises PermissionError on Windows when a second writer holds the destination for an instant, so even the paths that already used unique temps (the .ipd, the price cache) could silently not be written. Every writer now uses a unique temp and retries the swap. Five tests reproduce the race with concurrent threads instead of trusting the fix.

• Verified clean and unchanged: quote escaping on every rule builder that interpolates a poe.ninja name, no type-less [StashItem] rule in a full generate, the anchored backup-name matcher at all seven call sites, save_config reporting the real outcome, game_data.json against the code, and the stat ids and weights against the live patch.

• CLAUDE.md's page list was stale again — the file that warns "this list has gone stale before" was missing p-maps and p-bot.
"""
