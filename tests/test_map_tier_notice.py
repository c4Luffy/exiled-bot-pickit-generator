"""The run must SAY which map tiers it wrote.

Maps are the only category whose scope is a selection rather than a value
floor, and it defaults to tier 16 alone. A new user therefore generates, the
run reports a cheerful "OK, Maps", and their bot then walks past every T1-T15
map on the ground — which reads as "the app does not do maps".

The default is deliberate (the Maps tab argues that taking every map is the
single biggest cause of a full stash). Being silent about it is not.
"""
from __future__ import annotations

from exilebot_pickit.generators import assembly as asm


def _summary(tiers):
    """The phrasing the run log builds from a tier selection."""
    return asm.map_tier_summary(tiers) or "none"


def test_the_default_selection_is_a_single_tier():
    """If this ever stops being true, the notice below needs revisiting."""
    from exilebot_pickit.ui.config import DEFAULT_CONFIG
    assert DEFAULT_CONFIG["poe1_map_tiers"] == [16]


def test_default_reads_as_one_tier():
    assert _summary([16]) == "T16"


def test_neighbouring_tiers_collapse_into_a_run():
    assert _summary([16, 15, 14]) == "T14-T16"


def test_gaps_stay_separate():
    """Runs are listed low to high, each gap its own entry."""
    assert _summary([16, 14]) == "T14, T16"


def test_every_map_is_one_run():
    assert _summary(list(range(1, 17))) == "T1-T16"


def test_empty_selection_is_reported_as_none():
    assert _summary([]) == "none"


def test_narrow_selections_are_the_ones_worth_warning_about():
    """The run adds "only ..." for a selection this small — the silent case."""
    for tiers in ([16], [16, 15], [16, 15, 14]):
        assert len(asm.normalise_map_tiers(tiers)) <= 3
    assert len(asm.normalise_map_tiers(list(range(10, 17)))) > 3


# ── the notice must REACH the run log ────────────────────────────────────
def test_the_notice_is_wired_into_the_poe1_generate():
    """The bug this test exists for.

    v4.51.0 put this notice in ``_generate``, which returns to
    ``_generate_poe1`` on its second line for an economy-only game — and maps
    are PoE 1 only. The notice could never run. Every test passed, because they
    all checked the wording of a helper nobody called.
    """
    import inspect
    from exilebot_pickit.webui import api as webapi
    src = inspect.getsource(webapi.AppApi._generate_poe1)
    assert "map_tier_notice" in src, "the PoE 1 generate must emit the map notice"


def test_the_notice_wording_for_each_case():
    assert asm.map_tier_notice([16]).startswith("✓ Maps: T16 only")
    assert "every other tier is left on the ground" in asm.map_tier_notice([16])
    # a broad selection is not nagged at
    assert asm.map_tier_notice(list(range(1, 17))) == "✓ Maps: T1-T16"
    assert asm.map_tier_notice([]).startswith("⚠ Maps: no tiers selected")
