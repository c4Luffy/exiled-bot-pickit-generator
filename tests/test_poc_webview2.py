"""The WebView2 pre-flight guard in webui/poc.py.

Background: when the Edge WebView2 runtime is absent, pywebview does not raise
— it falls back to MSHTML (IE11) and webview.start() SUCCEEDS. The app then
renders app.html in an engine with no CSS custom properties and no arrow
functions, which produces a white/serif window whose league dropdown is stuck
on "Loading…" forever, with no error shown. Windows 11 bundles WebView2;
Windows 10 does not always have it, so this state is reachable in the wild.

These tests pin the guard that turns that silent failure into an instruction.
"""

import pytest

pytest.importorskip("webview")

from exilebot_pickit.webui import poc  # noqa: E402


def test_mshtml_is_refused_with_install_instructions(monkeypatch):
    """IE11 fallback must stop the launch and name the actual fix."""
    shown = []
    monkeypatch.setattr(poc, "_renderer", lambda: "mshtml")
    monkeypatch.setattr(poc, "_fatal", lambda msg: shown.append(msg))

    assert poc._require_webview2() is False, "MSHTML must not be allowed to launch"
    assert len(shown) == 1, "the user must be told exactly once"
    msg = shown[0]
    assert poc.WEBVIEW2_URL in msg, "the message must carry the download link"
    assert "WebView2" in msg
    # The old dialog called a missing runtime "rare on updated Windows", which
    # is backwards for the Windows 10 users who actually hit this.
    assert "rare" not in msg.lower()


def test_edgechromium_launches(monkeypatch):
    """The normal case must not be disturbed."""
    monkeypatch.setattr(poc, "_renderer", lambda: "edgechromium")
    monkeypatch.setattr(poc, "_fatal", lambda msg: pytest.fail(f"dialog shown: {msg}"))
    assert poc._require_webview2() is True


@pytest.mark.parametrize("renderer", [None, "cef"])
def test_unknown_renderer_is_allowed(monkeypatch, renderer):
    """Never block on a renderer we can't identify.

    _renderer() returns None off Windows or when pywebview's internals move.
    Guessing "broken" there would refuse to start a working app — the guard is
    only allowed to act on a positive MSHTML identification."""
    monkeypatch.setattr(poc, "_renderer", lambda: renderer)
    monkeypatch.setattr(poc, "_fatal", lambda msg: pytest.fail(f"dialog shown: {msg}"))
    assert poc._require_webview2() is True


def test_renderer_reads_pywebview_and_never_raises(monkeypatch):
    """_renderer() must be total — it runs before any error UI exists."""
    monkeypatch.setattr(poc.sys, "platform", "linux")
    assert poc._renderer() is None

    monkeypatch.setattr(poc.sys, "platform", "win32")
    import builtins
    real_import = builtins.__import__

    def boom(name, *a, **kw):
        # `from webview.platforms import winforms` imports the PACKAGE, so the
        # name to match is webview.platforms — not the submodule.
        if name.startswith("webview.platforms"):
            raise ImportError("pythonnet missing")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", boom)
    assert poc._renderer() is None, "an unimportable backend must not crash the launch"


def test_main_checks_before_building_the_window(monkeypatch):
    """The guard has to run BEFORE create_window, not after.

    Ordering is the whole point: past this line the app has already spent a
    config load and a watchdog thread on a launch that cannot work."""
    monkeypatch.setattr(poc, "_single_instance", lambda: True)
    monkeypatch.setattr(poc, "_renderer", lambda: "mshtml")
    monkeypatch.setattr(poc, "_fatal", lambda msg: None)
    monkeypatch.setattr(poc, "_start_freeze_watchdog",
                        lambda: pytest.fail("watchdog started for a doomed launch"))
    monkeypatch.setattr(poc.webview, "create_window",
                        lambda *a, **kw: pytest.fail("window built under IE11"))
    monkeypatch.setattr(poc, "_run_webview",
                        lambda *a, **kw: pytest.fail("webview started under IE11"))

    poc.main()   # must return quietly
