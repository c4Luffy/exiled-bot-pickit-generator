"""Single source of truth for the app version."""
VERSION = "4.54.0"
# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• A category's value floor came from which poe.ninja endpoint it uses, not from what it is. The is_unique flag on a category answers "stash endpoint or exchange endpoint" — the Precursor Tablets entry says so in its own comment, "purely for endpoint routing: this is not a real unique category" — but effective_min() also used it to choose between the items floor and the unique floor. So eight ordinary categories sat behind the unique floor: Precursor Tablets, and in Path of Exile 1 skill gems, beasts, incubators, vials, cluster jewels, invitations and maps. Reported from a real setup: with a 100 ex unique floor, tablets worth 75-90 ex were written commented out while the Economy tab showed them kept. On that setup the fix takes tablets from 9 of 21 rules active to all 21.

• The floor is now chosen from the category key, which is the honest signal and the same test the Path of Exile 1 rule writer already uses to decide between [UniqueName] and [Type]. Real uniques are unaffected.

• Maps had a one-off workaround for exactly this, added when the same problem was noticed for them alone. It is gone — every stash-routed category now gets the right floor for free, and a new test fails if a future category is added with the same conflation.

Also in 4.53.0:

• Bot Activity now keeps a per-session history. The bot overwrites lastrun.log every time it starts, so what the previous session earned was gone the moment the next one began — the tab could only ever describe the session running now. Each session is snapshotted under its start timestamp and updated in place while it grows, giving a table of every session (items, sold, earned) and a career total beside the current one.

• A read taken before prices load can no longer erase what a session earned. The price lookup reads a cache that is empty until the Economy tab or a generate has warmed it, so an early read values every pickup at zero — and writing that over an already-recorded session wiped the figure. Seen live: a session recorded at 2.0c came back as 0.0c after one cold read. The earnings figure now only moves when the read actually had prices.

• The history is per game (the two are different bot installs), capped at 60 sessions so it cannot grow the config without bound, and an unchanged session does not rewrite the config on every visit to the tab.

• Honest about its limit, in the tab itself: a session is only captured while the app can still see it. If the app is closed for a whole session, that one cannot be recovered — the bot has already overwritten the file.
"""
