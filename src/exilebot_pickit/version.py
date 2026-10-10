"""Single source of truth for the app version."""
VERSION = "4.57.3"
# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• Cards and controls fit the window more cleanly. Generate presets use an even grid; Craft, Settings, and the rule category rails give their content more room at the normal window size. The Preview rule viewer and Magic & Rare strictness controls stack when the window narrows.

• Economy rows are readable again. An HTML price fragment was inserted into the “under floor” button's tooltip, breaking its shape and spilling text across the table. The tooltip now uses plain text; narrow layouts also give item names and values more space.

• These are presentation changes. Generated pickit rules and saved settings are unchanged.

Also in 4.57.2:

• Without the Edge WebView2 runtime the app opened, drew, and did nothing — with no error at all. pywebview does not fail when WebView2 is absent: it falls back to MSHTML (Internet Explorer 11), so webview.start() succeeds and the existing "couldn't start its window" dialog never fired. The app then rendered app.html in a 2013 engine, which broke it two ways at once. IE11 has no CSS custom properties, so every var(--bg) / var(--text) / var(--font) resolved to nothing — a white, black and serif window whose plain flex and padding rules still applied, so it looked half-styled rather than obviously broken. And IE11's ES5-only parser rejects the page's arrow functions outright, killing the entire script — which is why the league dropdown sat on its hardcoded "Loading…" option forever and the version label stayed blank.

• The app now checks which renderer pywebview will use before it builds the window. If the answer is IE11 it shows the real fix — install the WebView2 runtime, with the download link — and exits, instead of spending a config load and a watchdog thread on a launch that cannot work. The check reads the renderer out of pywebview itself rather than re-implementing its registry probe, so it cannot drift from the decision it is predicting, and it acts only on a positive MSHTML identification — an unrecognised renderer is always allowed to start.

• Who this was hitting: Windows 10. Windows 11 bundles WebView2. On Windows 10 it normally arrives with Microsoft Edge, but it is missing on fresh, LTSC, N and debloated installs — so the app was reported as "just showing a white page" by users whose PCs were fine and only needed a 2 MB runtime.

• The start-failure dialog stopped misleading people. It described a missing WebView2 runtime as "rare on updated Windows" — precisely backwards for the people reading it. A missing runtime now has its own message, so that dialog is left with the causes it can still be: an old copy still running, an unwritable folder, or a runtime that is installed but won't start.
"""
