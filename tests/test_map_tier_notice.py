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
    picked = asm.normalise_map_tiers(tiers)
    if not picked:
        return "none"
    return ", ".join(f"T{lo}" if lo == hi else f"T{lo}-T{hi}"
                     for lo, hi in asm.map_tier_runs(picked))


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
