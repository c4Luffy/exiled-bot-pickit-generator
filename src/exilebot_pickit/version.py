"""Single source of truth for the app version."""
VERSION = "4.57.2"
# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• On a PC without the Edge WebView2 runtime, the app opened a dead window instead of saying so. pywebview does not fail when WebView2 is missing — it quietly falls back to Internet Explorer 11, and starting succeeds, so no error was ever shown. The app then rendered in a 2013 engine: white and serif because IE11 has no CSS variables, with the whole script rejected at the first arrow function, which is why the league dropdown sat on "Loading…" forever and the version label was blank.

• It now checks the renderer before building the window and, if it would be IE11, shows the actual fix — install the WebView2 runtime, with the link — and exits. Windows 11 already includes WebView2; on Windows 10 it normally arrives with Microsoft Edge but is absent on fresh, LTSC, N and debloated installs, which is who this was happening to.

• The start-failure dialog stopped misleading people too. It listed a missing WebView2 runtime as "rare on updated Windows" — backwards for exactly the users hitting it. A missing runtime now has its own message, so that dialog covers only the causes it can still be.

Also in 4.57.1:

• Magic & Rare told you it had 17 slot recipes while listing 18. Adding the Jewel slot in v4.57.0 left the count hardcoded in six places — three code comments, the README feature list, and two hints on the Magic & Rare page itself, one of them directly above the rail that now shows eighteen entries.

• The two in-app hints now read the count from the API instead of the markup, so the nineteenth slot cannot reintroduce this. The number in the HTML is only the pre-script fallback.

Also in 4.57.0:

• Rare jewels are now scored like every other slot. Magic & Rare gains an 18th slot, Jewel, covering the three droppable bases — Sapphire, Emerald and Ruby — with a 14-stat WeightedSum: max Energy Shield, Triggered Spell Damage, Elemental / Spell / Lightning / Projectile Damage, Ailment Magnitude, Projectile Speed, Crit Damage Bonus, Spell Crit Damage, chance to Pierce, Crit Chance, Spell Crit Chance and Cast Speed. Every id and every T1 max-roll was read from the live GGPK mod dump, not a wiki.

• Jewels carry no [ItemTier], so the Jewel slot writes no tier gate. Every other slot gates on [ItemTier] >= "4"; emitting that against a property the item does not have is the silent way to write a rule that never matches, so item_tier is now optional and the tab shows "—" for it.

• Two dead stat ids corrected on the way in: projectile_speed_+% does not exist in the game (the real id is base_projectile_speed_+%), and recover_%_maximum_mana_on_kill is real but never rolls on a jewel. Both score zero forever with no error — the exact failure mode this repo's checker exists to catch.

• The embedded syntax guide now documents [UniqueName], including the disenchant idiom from Exiled Bot's own default.ipd, where a deliberately impossible name picks up every unique so anything no other rule keeps is left to disenchant for Chance Shards.
"""
