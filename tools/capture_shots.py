"""Capture a 1920x1009 screenshot of every app tab, for both games.

The landing page shows one frame per tab, per game. Taking those by hand is why
they went stale — three PoE 1 captures ended up inside the PoE 2 tour, all
labelled with a version none of them were taken on. This drives the REAL app
(same AppApi, same config, same WebView2 window as ``python -m exilebot_pickit``)
from a worker thread: switch game -> run a real generate -> click each visible
sidebar tab -> grab the window rect.

    python tools/capture_shots.py                     # all 22, into docs/shots
    CAP_GAMES=poe1 CAP_PAGES=gen python tools/capture_shots.py    # just one
    CAP_GENERATE=0 python tools/capture_shots.py      # skip the generate run

Output is ``<game>-NN-<slug>-v<VERSION>.png``, the names docs/index.html expects.
Windows only (WebView2), and it takes over the screen while it runs: the window
is pinned to 0,0 and captured off the desktop, so don't cover it.

Environment:
  CAP_GAMES     comma list, default "poe2,poe1"
  CAP_PAGES     comma list of page ids to limit to (default: every visible one)
  CAP_GENERATE  "0" to skip the generate run (tabs then show the previous run)
  CAP_OUT       output directory, default docs/shots
"""
import ctypes
import os
import sys
import time

try:                                     # match the app's own DPI handling so a
    ctypes.windll.shcore.SetProcessDpiAwareness(2)   # scaled display still gives
except Exception:                        # us true 1920x1009 pixels
    pass

import webview
from PIL import ImageGrab

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from exilebot_pickit.version import VERSION          # noqa: E402
from exilebot_pickit.webui.api import AppApi         # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("CAP_OUT") or os.path.join(ROOT, "docs", "shots")
SUFFIX = "v" + VERSION.replace(".", "")

W, H = 1920, 1009
DO_GENERATE = os.environ.get("CAP_GENERATE", "1") == "1"
ONLY_GAMES = [g for g in os.environ.get("CAP_GAMES", "poe2,poe1").split(",") if g]
ONLY_PAGES = [p for p in os.environ.get("CAP_PAGES", "").split(",") if p]

# Sidebar order in app.html. g2only tabs are hidden in PoE 1, so PoE 1 numbering
# closes the gaps — poe1-03 is Create your filter, not Item Check.
PAGES = [
    ("gen",      "generate",           True),
    ("prev",     "preview",            True),
    ("item",     "item-check",         False),
    ("mypk",     "create-your-filter", False),   # PoE 2 only: PoE 1 has no filter
    ("hist",     "history",            True),
    ("eco",      "economy",            True),
    ("maps",     "maps",               True),     # PoE 1 only (g1only)
    ("chance",   "chance",             False),
    ("craft",    "craft",              False),
    ("exc",      "exceptional",        False),
    ("fracture", "fracture",           False),
    ("rare",     "magic-rare",         False),
    ("guide",    "setup-guide",        True),
    ("set",      "settings",           True),
    ("dbg",      "debug",              True),
]


# The console this runs on is often cp1252, and item names carry glyphs it can't
# encode (the keep pill's bullet killed a run mid-capture). Same fix the headless
# --cli/--regenerate modes already carry: wrap stdout as UTF-8 so an exotic glyph
# degrades instead of aborting the run.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def log(*a):
    print(*a, flush=True)


def js(window, code, default=None):
    try:
        return window.evaluate_js(code)
    except Exception as e:
        log("   js error:", e)
        return default


def _hwnd(window):
    try:
        return window.native.Handle.ToInt64()
    except Exception:
        return None


def place(window):
    """Pin the native window to (0,0) at exactly W x H so every shot lines up."""
    try:
        hwnd = _hwnd(window)
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, W, H, 0x0040)  # SWP_SHOWWINDOW
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception as e:
        log("!! could not place the window:", e)


def _focus(window, tries=6):
    """Make sure OUR window is the one on screen before grabbing.

    ImageGrab reads the desktop, so anything that steals focus mid-run (an
    editor, a notification) gets captured instead — silently, since the shot is
    still 1920x1009 and looks fine to the script. Assert the foreground window
    is ours and retry; give up loudly rather than saving someone else's screen.
    """
    u, k = ctypes.windll.user32, ctypes.windll.kernel32
    hwnd = _hwnd(window)
    if not hwnd:
        return True                      # can't verify; caller still grabs
    for _ in range(tries):
        fg = u.GetForegroundWindow()
        if fg == hwnd:
            return True
        # Windows refuses SetForegroundWindow from a process that doesn't own
        # the foreground — which is exactly our case when the run is started
        # from a terminal. Attaching to the foreground window's input thread
        # lifts that restriction for the call.
        tid = u.GetWindowThreadProcessId(fg, None) if fg else 0
        cur = k.GetCurrentThreadId()
        attached = bool(tid and tid != cur and u.AttachThreadInput(tid, cur, True))
        try:
            u.ShowWindow(hwnd, 9)        # SW_RESTORE
            u.BringWindowToTop(hwnd)
            u.SetForegroundWindow(hwnd)
        finally:
            if attached:
                u.AttachThreadInput(tid, cur, False)
        time.sleep(0.6)
    return u.GetForegroundWindow() == hwnd


def grab(window, name):
    if not _focus(window):
        log(f"!! {name}: the app is not the foreground window — SKIPPED "
            "(don't click away while this runs)")
        return
    b = window.native.Bounds
    u = ctypes.windll.user32
    vx, vy = u.GetSystemMetrics(76), u.GetSystemMetrics(77)   # virtual-screen origin
    img = ImageGrab.grab(all_screens=True).crop(
        (b.X - vx, b.Y - vy, b.X - vx + b.Width, b.Y - vy + b.Height))
    if img.size != (W, H):
        log(f"   (resizing {img.size} -> {(W, H)})")
        img = img.resize((W, H), 3)
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, f"{name}.png"), optimize=True)
    log(f"   saved {name}.png")


def wait_ready(window, timeout=90):
    end = time.time() + timeout
    while time.time() < end:
        if js(window, "!!(document.getElementById('league') && "
                      "document.getElementById('league').options.length)"):
            return True
        time.sleep(1.5)
    return False


def wait_prices(window, timeout=120):
    """Only meaningful once Economy is open: its table fills when the tab renders.
    Poll so the shot isn't of 'Loading prices...'."""
    end = time.time() + timeout
    while time.time() < end:
        n = js(window, "document.querySelectorAll('#ecoBody tr').length", 0) or 0
        if n > 5:
            log(f"   economy rows: {n}")
            return True
        time.sleep(3)
    log("   economy rows never arrived (offline?) — continuing")
    return False


def close_modals(window, rounds=3):
    """The "Updated to vX — what's new" dialog opens over the whole app on the
    first launch after an update, and would sit in the middle of every capture.
    Click its real close button (so the app records the version as seen), then
    force any leftover overlay shut."""
    for _ in range(rounds):
        n = js(window, """(function(){
          var open=document.querySelectorAll('.modal.on'), n=0;
          open.forEach(function(m){
            var b=m.querySelector('.modal-ft .primary')||m.querySelector('.modal-ft button');
            if(b){try{b.click();}catch(e){}}
            m.classList.remove('on'); n++;});
          document.querySelectorAll('.toast').forEach(function(t){t.classList.remove('on');});
          return n;})()""", 0) or 0
        if n:
            log(f"   dismissed {n} modal(s)")
        time.sleep(1.5)


def run_generate(window, timeout=240):
    """Press the real Generate button and wait for the run, so Generate/Preview/
    History show a completed run instead of 'Ready to run'."""
    if not js(window, """(function(){
          var b=document.getElementById('go');
          if(!b||b.disabled)return false; b.click(); return true;})()""", False):
        log("   generate button unavailable — skipping")
        return False
    end = time.time() + timeout
    time.sleep(4)
    while time.time() < end:
        if not js(window, "(function(){var b=document.getElementById('go');"
                          "return !!(b&&b.disabled);})()", False):
            time.sleep(4)
            log("   generate finished")
            return True
        time.sleep(3)
    log("   generate timed out")
    return False


def switch_game(window, game, timeout=60):
    """Switch games and CONFIRM it took effect.

    A fixed sleep was not enough: one run captured the whole 'poe2' pass while
    the app was still in PoE 1 — Item Check missing, the PoE1-only Maps tab
    shot under a poe2 name — and nothing noticed. ECON_ONLY is the app's own
    flag for 'this game is economy-only' (true for PoE 1), so poll that.
    """
    # Check the SIDEBAR, not a JS variable: ECON_ONLY starts life as false
    # ("poe2") and only becomes true once the saved game is applied, so polling
    # it passed instantly at launch while the app was still becoming PoE 1 —
    # and the whole "poe2" pass was captured in PoE 1.
    probe = "maps" if game == "poe1" else "chance"
    check = (f"""(function(){{var b=document.querySelector('.nav-btn[data-p="{probe}"]');"""
             "return !!(b && b.offsetParent !== null);})()")
    end = time.time() + timeout
    while time.time() < end:
        js(window, f'setGame("{game}")')
        time.sleep(4)
        if js(window, check) is True:
            time.sleep(4)               # let lists reload and the toast fade
            return True
    log(f"!! could not switch to {game} — the pass would capture the wrong game")
    return False


def do_game(window, game):
    log(f"== {game} ==")
    if not switch_game(window, game):
        return 0
    wait_ready(window)
    close_modals(window)
    if DO_GENERATE:
        run_generate(window)
        close_modals(window)

    n = 0
    for pid, slug, in_poe1 in PAGES:
        if game == "poe1" and not in_poe1:
            continue
        n += 1
        if ONLY_PAGES and pid not in ONLY_PAGES:
            continue
        state = js(window, f"""(function(){{
          var b=document.querySelector('.nav-btn[data-p="{pid}"]');
          if(!b) return 'missing';
          if(getComputedStyle(b).display==='none') return 'hidden';
          b.click(); return 'ok';}})()""", "error")
        if state != "ok":
            log(f"-- {pid}: {state} (skipped)")
            n -= 1
            continue
        time.sleep(6 if pid in ("eco", "chance", "exc", "prev", "mypk") else 3.5)
        if pid == "eco":
            wait_prices(window)
        close_modals(window, rounds=1)
        # Pages scroll INSIDE their own container, so window.scrollTo alone left
        # shots starting halfway down a long page (the Maps page did).
        js(window, "if(document.activeElement)document.activeElement.blur();"
                   "window.scrollTo(0,0);"
                   "document.querySelectorAll('main,.page.on,.page.on *')"
                   ".forEach(function(e){if(e.scrollTop)e.scrollTop=0;});")
        time.sleep(1.2)
        log(f"-- {pid}")
        grab(window, f"{game}-{n:02d}-{slug}-{SUFFIX}")
    return n


def worker(window):
    try:
        ctypes.windll.user32.SetCursorPos(1910, 1075)      # cursor out of frame
    except Exception:
        pass
    time.sleep(6)
    place(window)
    time.sleep(2)
    if not wait_ready(window):
        log("!! the UI never became ready")
        window.destroy()
        return
    total = 0
    for game in ONLY_GAMES:
        place(window)
        total += do_game(window, game)
    log(f"DONE: {total} shots in {OUT}")
    time.sleep(1)
    window.destroy()


def main():
    api = AppApi()
    html = os.path.join(ROOT, "src", "exilebot_pickit", "webui", "app.html")
    window = webview.create_window(
        "Exiled Bot Pickit Generator", html, js_api=api,
        width=W, height=H, x=0, y=0,
        background_color="#0e0f12", frameless=False,
    )
    from exilebot_pickit.ui.config import PRICE_CACHE_DIR
    storage = os.path.join(os.path.dirname(PRICE_CACHE_DIR), "webview_profile")
    os.makedirs(storage, exist_ok=True)
    webview.start(worker, window, storage_path=storage)
    return 0


if __name__ == "__main__":
    sys.exit(main())
