import pytest

from zuba.api.board import build_board, build_game_summary, combine, probability

MATCH = {
    "match_id": 1, "date": "2026-06-20", "kickoff_ts": "2026-06-20T19:00:00+00:00",
    "home_team": "Spain", "away_team": "Japan", "completed": 0,
    "home_score": None, "away_score": None,
}
PROBS = {
    "home_win_p": 0.6, "draw_p": 0.25, "away_win_p": 0.15,
    "dc_1x_p": 0.85, "dc_12_p": 0.75, "dc_x2_p": 0.4,
    "over_2_5_p": 0.55, "h_o25_p": 0.4,
    "exp_home_goals": 1.9, "exp_away_goals": 0.8,
}


def test_probability_lookups():
    assert probability(PROBS, "1x2", "draw") == 0.25
    assert probability(PROBS, "ou_2_5", "under") == pytest.approx(0.45)
    assert probability(PROBS, "ou_9_5", "over") is None
    assert probability(PROBS, "1x2", "nonsense") is None


def test_board_skips_lines_without_a_probability():
    board = build_board(MATCH, PROBS)
    markets = {p.market for p in board.prices}
    assert markets == {"1x2", "dc", "ou_2_5"}
    home = next(p for p in board.prices if p.selection == "home")
    assert home.selection_label == "Spain"
    assert home.fair_odds == pytest.approx(1 / 0.6)


def test_summary_picks_the_most_likely_result():
    s = build_game_summary(MATCH, PROBS)
    assert s.pick_selection == "home" and s.pick_label == "Spain"
    assert not build_game_summary(MATCH, None).has_prediction


def test_same_match_result_and_goals_uses_the_joint_probability():
    res = combine([(1, "1x2", "home"), (1, "ou_2_5", "over")], {1: MATCH}, {1: PROBS})
    assert res.combined_p == pytest.approx(0.4)  # not 0.6 * 0.55
    assert not res.correlated_warning


def test_same_match_without_a_joint_is_flagged():
    res = combine([(1, "1x2", "draw"), (1, "ou_2_5", "over")], {1: MATCH}, {1: PROBS})
    assert res.combined_p == pytest.approx(0.25 * 0.55)
    assert res.correlated_warning


def test_unknown_match_is_rejected():
    with pytest.raises(ValueError):
        combine([(2, "1x2", "home")], {1: MATCH}, {1: PROBS})
