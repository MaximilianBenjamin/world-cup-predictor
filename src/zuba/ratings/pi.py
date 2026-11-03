"""Pi-ratings (Constantinou & Fenton 2013), computed match by match.

Each team carries a home rating and an away rating, measured in expected goal
difference. They are updated after every result, and the features for a match
are the ratings as they stood before kickoff, so nothing leaks from the result.
The CatBoost model uses them as its inputs.
"""

from __future__ import annotations

import contextlib

import pandas as pd
from penaltyblog.ratings import PiRatingSystem

PI_FEATURES = [
    "pi_home_h", "pi_home_a", "pi_away_h", "pi_away_a",
    "pi_diff_h", "pi_diff_a",
]


def pi_row(system: PiRatingSystem, home_team: str, away_team: str) -> dict[str, float]:
    """Feature values for one fixture from the system's current ratings."""
    h = system.team_ratings.get(home_team, {"home": 0.0, "away": 0.0})
    a = system.team_ratings.get(away_team, {"home": 0.0, "away": 0.0})
    return {
        "pi_home_h": h["home"], "pi_home_a": h["away"],
        "pi_away_h": a["home"], "pi_away_a": a["away"],
        "pi_diff_h": h["home"] - a["away"],  # expected goal difference
        "pi_diff_a": a["home"] - h["away"],
    }


def build_pi_features(df: pd.DataFrame) -> tuple[pd.DataFrame, PiRatingSystem]:
    """Add pre-match pi features to every row of df (sorted by date).

    Returns the frame and the rating system after the last match, which is
    what predictions for upcoming games should use.
    """
    df = df.sort_values("date").reset_index(drop=True)
    system = PiRatingSystem()
    rows = []
    for r in df.itertuples(index=False):
        rows.append(pi_row(system, r.home_team, r.away_team))
        # The third argument is the goal difference, not home goals.
        with contextlib.suppress(ValueError, KeyError):
            system.update_ratings(r.home_team, r.away_team, int(r.home_goals - r.away_goals))
    return pd.concat([df, pd.DataFrame(rows)], axis=1), system
