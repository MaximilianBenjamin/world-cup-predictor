"""LightGBM on Elo and recent form: match result probabilities.

Features for each match: both teams' pre-match Elo, the gap between them, each
side's average points over its last 3 and last 5 games, and whether the venue
is neutral. All are known before kickoff, so the model never sees the result
it is predicting. The number of trees is set by early stopping (see
`zuba.models.tabular`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from zuba.models.tabular import ResultBooster

FEATURES = [
    "elo_home", "elo_away", "elo_diff",
    "form3_home", "form5_home", "form3_away", "form5_away",
    "neutral",
]
_POINTS_HOME = {"H": 3, "D": 1, "A": 0}
_POINTS_AWAY = {"A": 3, "D": 1, "H": 0}


def add_form(rated: pd.DataFrame) -> pd.DataFrame:
    """Add each side's average points over its previous 3 and 5 matches.

    Results are stacked into one row per (team, match) so home and away games
    count towards the same run of form, then shifted by one so the current
    match is excluded.
    """
    df = rated.sort_values("date").reset_index(drop=True)
    long = pd.concat([
        pd.DataFrame({"idx": df.index, "team": df["home_team"], "side": "home",
                      "pts": df["result"].map(_POINTS_HOME)}),
        pd.DataFrame({"idx": df.index, "team": df["away_team"], "side": "away",
                      "pts": df["result"].map(_POINTS_AWAY)}),
    ]).sort_values(["idx", "side"], kind="stable").reset_index(drop=True)
    past = long.groupby("team")["pts"].shift(1)
    for n in (3, 5):
        long[f"form{n}"] = past.groupby(long["team"]).transform(
            lambda s, n=n: s.rolling(n, min_periods=1).mean()
        )
    for side in ("home", "away"):
        part = long[long["side"] == side].set_index("idx")
        df[f"form3_{side}"] = part["form3"]
        df[f"form5_{side}"] = part["form5"]
    return df


def recent_form(rated: pd.DataFrame) -> dict[str, list[int]]:
    """team -> points from every match in `rated`, oldest first."""
    form: dict[str, list[int]] = {}
    for r in rated.sort_values("date").itertuples(index=False):
        form.setdefault(r.home_team, []).append(_POINTS_HOME[r.result])
        form.setdefault(r.away_team, []).append(_POINTS_AWAY[r.result])
    return form


class EloLGBM:
    def __init__(self) -> None:
        self._model = ResultBooster("lightgbm", FEATURES)
        self._form: dict[str, list[int]] = {}

    def fit(self, rated: pd.DataFrame) -> EloLGBM:
        """rated: output of build_international_elo (needs elo_*, neutral and result)."""
        self._model.fit(add_form(rated))
        self._form = recent_form(rated)
        return self

    def _form_avg(self, team: str, n: int) -> float:
        pts = self._form.get(team)
        return float(np.mean(pts[-n:])) if pts else np.nan

    def predict(self, home_team: str, away_team: str, elo_home: float, elo_away: float,
                neutral: bool = True) -> np.ndarray:
        """[P(home win), P(draw), P(away win)]. A team with no earlier games has
        missing form, which the trees handle directly."""
        row = pd.DataFrame([{
            "elo_home": elo_home, "elo_away": elo_away, "elo_diff": elo_home - elo_away,
            "form3_home": self._form_avg(home_team, 3), "form5_home": self._form_avg(home_team, 5),
            "form3_away": self._form_avg(away_team, 3), "form5_away": self._form_avg(away_team, 5),
            "neutral": neutral,
        }])
        return self._model.predict(row)[0]
