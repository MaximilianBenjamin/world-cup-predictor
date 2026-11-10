import numpy as np
import pandas as pd

from zuba.table import _rounds, remaining_fixtures, simulate, standings


def _played(rows):
    return pd.DataFrame(rows, columns=["home_team", "away_team", "home_goals", "away_goals"])


def test_standings_order_and_counts():
    table = standings(_played([("A", "B", 2, 0), ("B", "C", 1, 1), ("C", "A", 0, 0)]))
    assert [r["team"] for r in table] == ["A", "C", "B"]       # C and B: goal difference
    a = table[0]
    assert (a["played"], a["won"], a["drawn"], a["lost"]) == (2, 1, 1, 0)
    assert (a["goals_for"], a["goals_against"], a["goal_difference"], a["points"]) == (2, 0, 2, 4)
    assert [r["position"] for r in table] == [1, 2, 3]


def test_remaining_fixtures_are_the_unplayed_pairs():
    played = _played([("A", "B", 1, 0), ("B", "C", 0, 0)])
    left = remaining_fixtures(played, ["A", "B", "C"])
    assert sorted(left) == [("A", "C"), ("B", "A"), ("C", "A"), ("C", "B")]
    for group in _rounds(left):
        clubs = [club for pair in group for club in pair]
        assert len(clubs) == len(set(clubs))                   # no club twice in a group
    assert sorted(pair for group in _rounds(left) for pair in group) == sorted(left)


def test_simulation_follows_the_scoreline_grids():
    current = standings(_played([("A", "B", 1, 0), ("B", "C", 0, 0)]), ["A", "B", "C"])
    home_wins_2_0 = np.zeros((4, 4))
    home_wins_2_0[2, 0] = 1.0
    grids = dict.fromkeys(remaining_fixtures(_played([("A", "B", 1, 0), ("B", "C", 0, 0)]),
                                             ["A", "B", "C"]), home_wins_2_0)
    table = simulate(current, grids, simulations=200)
    by_team = {r["team"]: r for r in table}
    # Certain results: A beats C, loses at B and at C. C wins both home games, loses at A.
    assert by_team["A"]["points"] == 6.0 and by_team["C"]["points"] == 7.0
    assert by_team["B"]["points"] == 4.0
    assert [r["team"] for r in table] == ["C", "A", "B"]
    assert by_team["C"]["p_title"] == 1.0 and by_team["C"]["played"] == 4
    assert by_team["A"]["goals_for"] == 3.0 and by_team["A"]["goals_against"] == 4.0
    assert by_team["A"]["current_position"] == 1 and by_team["A"]["position"] == 2
