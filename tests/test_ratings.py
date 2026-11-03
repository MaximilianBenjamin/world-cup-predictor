import pandas as pd
import pytest

from zuba.models.elo_lgbm import add_form
from zuba.ratings.elo import InternationalElo
from zuba.ratings.pi import build_pi_features

MATCHES = pd.DataFrame({
    "date": pd.to_datetime(["2020-01-01", "2020-02-01", "2020-03-01"]),
    "home_team": ["A", "B", "A"],
    "away_team": ["B", "C", "C"],
    "home_goals": [3, 0, 1],
    "away_goals": [0, 0, 2],
    "result": ["H", "D", "A"],
    "tournament": ["Friendly"] * 3,
    "neutral": [True] * 3,
})


def test_elo_is_stamped_before_the_match():
    rated = InternationalElo().run(MATCHES)
    assert rated.loc[0, "elo_home"] == rated.loc[0, "elo_away"] == 1500
    assert rated.loc[1, "elo_home"] < 1500  # B lost the first game
    assert rated.loc[2, "elo_home"] > 1500  # A won it


def test_elo_is_zero_sum():
    elo = InternationalElo()
    elo.run(MATCHES)
    assert sum(elo.ratings.values()) == pytest.approx(1500 * 3)


def test_pi_ratings_use_goal_difference():
    df, system = build_pi_features(MATCHES)
    assert df.loc[0, "pi_home_h"] == 0  # nothing known before the first game
    # A beat B 3-0, then lost 1-2 to C at home: one big positive update, one small negative.
    assert system.team_ratings["A"]["home"] > 0
    assert system.team_ratings["B"]["away"] < 0


def test_form_ignores_the_current_match():
    df = add_form(MATCHES)
    assert pd.isna(df.loc[0, "form3_home"])          # A's first game
    assert df.loc[2, "form3_home"] == pytest.approx(3)  # A won its only earlier game
    assert df.loc[2, "form3_away"] == pytest.approx(1)  # C drew its only earlier game
