import numpy as np
import pandas as pd
import pytest

from zuba.data import load_club_matches
from zuba.features import ALL_FEATURES, build_club_features
from zuba.markets import board_probs, reconcile_grid
from zuba.ratings.gap import GAPRatings
from zuba.stacks.blend import blend, fit_weights


@pytest.fixture(scope="module")
def matches():
    return load_club_matches(min_date="2023-07-01", max_date="2025-07-01")


@pytest.fixture(scope="module")
def table(matches):
    return build_club_features(matches)


def test_features_are_all_present(table):
    assert set(ALL_FEATURES) <= set(table.columns)
    assert len(table) == table["date"].notna().sum()


def test_a_match_does_not_see_its_own_result(matches, table):
    """Rewriting one match's score and stats must leave its own features alone
    and change the features of that team's next game."""
    i = len(matches) // 2
    changed = matches.copy()
    stats = ["home_goals", "away_goals", "home_shots", "away_shots", "home_sot", "away_sot",
             "home_corners", "away_corners", "home_xg", "away_xg"]
    changed.loc[i, stats] = [9, 0, 40, 1, 20, 0, 15, 0, 6.0, 0.1]
    after = build_club_features(changed)

    same = (table["date"] == matches.loc[i, "date"]) & (table["home_team"] == matches.loc[i, "home_team"])
    row = table.index[same][0]
    pd.testing.assert_series_equal(table.loc[row, ALL_FEATURES], after.loc[row, ALL_FEATURES])

    team = matches.loc[i, "home_team"]
    plays = (table["home_team"] == team) | (table["away_team"] == team)
    later = table.index[(table.index > row) & plays][0]
    assert not table.loc[later, ALL_FEATURES].equals(after.loc[later, ALL_FEATURES])


def test_unplayed_fixtures_get_features_and_change_nothing(matches, table):
    fixture = pd.DataFrame([{"date": matches["date"].max() + pd.Timedelta(days=3), "league": "epl",
                             "season": "2025-26", "home_team": "Arsenal", "away_team": "Chelsea"}])
    with_fixture = build_club_features(pd.concat([matches, fixture], ignore_index=True))
    last = with_fixture.iloc[-1]
    assert pd.isna(last["home_goals"])
    assert last[["elo_home", "elo_away", "home_pts5", "away_sf10", "pi_diff_h"]].notna().all()
    pd.testing.assert_frame_equal(with_fixture.iloc[:-1][ALL_FEATURES], table[ALL_FEATURES])


def test_form_is_the_average_of_earlier_games(table):
    arsenal = table[(table["home_team"] == "Arsenal") | (table["away_team"] == "Arsenal")]
    points = np.where(
        arsenal["home_goals"] == arsenal["away_goals"], 1,
        np.where((arsenal["home_team"] == "Arsenal")
                 == (arsenal["home_goals"] > arsenal["away_goals"]), 3, 0),
    )
    last = arsenal.iloc[-1]
    side = "home" if last["home_team"] == "Arsenal" else "away"
    assert last[f"{side}_pts5"] == pytest.approx(points[-6:-1].mean())


def test_blend_weights_favour_the_better_model():
    rng = np.random.default_rng(0)
    truth = rng.dirichlet([4, 3, 3], size=4000)
    y = np.array([rng.choice(3, p=p) for p in truth])
    probs = {"good": truth, "noise": rng.dirichlet([1, 1, 1], size=4000)}
    w = fit_weights(probs, y)
    assert w["good"] > 0.9 and sum(w.values()) == pytest.approx(1)
    assert blend(probs, w).sum(axis=1) == pytest.approx(1)


def test_blend_skips_models_with_no_prediction():
    a = np.array([[0.6, 0.2, 0.2], [np.nan, np.nan, np.nan]])
    b = np.array([[0.2, 0.2, 0.6], [0.5, 0.3, 0.2]])
    out = blend({"a": a, "b": b})
    assert out[0] == pytest.approx([0.4, 0.2, 0.4])
    assert out[1] == pytest.approx([0.5, 0.3, 0.2])
    assert blend({"a": np.array([0.4, np.nan]), "b": np.array([0.6, 0.7])}) == pytest.approx([0.5, 0.7])


def _poisson_grid(mu_home: float, mu_away: float, size: int = 11) -> np.ndarray:
    from scipy.stats import poisson
    return np.outer(poisson.pmf(range(size), mu_home), poisson.pmf(range(size), mu_away))


def test_reconciled_grid_hits_both_targets():
    target, over = np.array([0.5, 0.2, 0.3]), 0.62
    M = reconcile_grid(_poisson_grid(1.4, 1.1), target, over)
    home, away = np.indices(M.shape)
    assert M.sum() == pytest.approx(1)
    got = [M[home > away].sum(), M[home == away].sum(), M[home < away].sum()]
    assert got == pytest.approx(target, abs=1e-6)
    assert M[home + away > 2.5].sum() == pytest.approx(over, abs=1e-6)


def test_board_markets_agree_with_each_other():
    p = board_probs(_poisson_grid(1.6, 0.9), np.array([0.55, 0.25, 0.20]), 0.48)
    assert p["home_win_p"] + p["draw_p"] + p["away_win_p"] == pytest.approx(1)
    assert p["over_2_5_p"] == pytest.approx(0.48, abs=1e-6)
    assert p["h_o25_p"] + p["h_u25_p"] == pytest.approx(p["home_win_p"])
    assert p["dc1x_o25_p"] + p["a_o25_p"] == pytest.approx(p["over_2_5_p"])
    assert p["over_0_5_p"] > p["over_1_5_p"] > p["over_2_5_p"] > p["over_3_5_p"]
    assert p["exp_home_goals"] > p["exp_away_goals"]


def test_gap_rates_a_team_that_shoots_more_as_stronger(matches):
    gap = GAPRatings("shots").fit(matches)
    idx = gap._team_index
    shots = gap._expected(np.array([idx["Man City"], idx["Sheffield United"]]),
                          np.array([idx["Sheffield United"], idx["Man City"]]))
    assert shots[0, 0] > shots[0, 1] and shots[1, 1] > shots[1, 0]
    assert 0 < gap.predict("Man City", "Sheffield United")["over_2_5"] < 1
    with pytest.raises(ValueError):
        GAPRatings("passes")
