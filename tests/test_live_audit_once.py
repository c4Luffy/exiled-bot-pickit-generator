import sys

import pytest

from exilebot_pickit import generator as gen


@pytest.mark.parametrize("game_id", ["poe1", "poe2"])
@pytest.mark.skipif(sys.version_info[:2] != (3, 12), reason="Single live probe")
def test_live_generation_categories(game_id, capsys):
    game = gen.get_game(game_id)
    leagues = gen.fetch_live_leagues(game)
    assert leagues
    league = next((name for name, _, _ in leagues
                   if name.lower() not in ("standard", "hardcore")
                   and "hardcore" not in name.lower()), leagues[0][0])
    categories = [c for c in game.all_categories if c[0] != "waystones"]
    results = gen.fetch_all_payloads(league, categories, game=game,
                                     use_cache=False, offline_fallback=False)
    with capsys.disabled():
        for key, _, _, _ in categories:
            p = results.get(key)
            print("LIVE", game_id, league, key,
                  len(p.get("lines", [])) if isinstance(p, dict) else repr(p), flush=True)
    gen.require_price_payloads(categories, results)
    assert results["currency"].get("lines")
