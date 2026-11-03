"""LightGBM on Elo and recent form: match result probabilities.

Features for each match: both teams' pre-match Elo, the gap between them, and
each side's average points over its last 3 and last 5 games. Both are computed
before kickoff, so the model never sees the result it is predicting.
"""

from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd

FEATURES = [
    "elo_home", "elo_away", "elo_diff",
    "form3_home", "form5_home", "form3_away", "form5_away",
]
_LABELS = {"H": 0, "D": 1, "A": 2}
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
    def __init__(self, n_estimators: int = 500, learning_rate: float = 0.05, num_leaves: int = 31):
        self._model = lgb.LGBMClassifier(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            num_leaves=num_leaves,
            objective="multiclass",
            random_state=42,
            verbose=-1,
        )
        self._medians: pd.Series | None = None
        self._form: dict[str, list[int]] = {}

    def fit(self, rated: pd.DataFrame) -> EloLGBM:
        """rated: output of build_international_elo (needs elo_* and result)."""
        df = add_form(rated)
        X = df[FEATURES]
        self._medians = X.median()
        self._model.fit(X.fillna(self._medians), df["result"].map(_LABELS))
        self._form = recent_form(rated)
        return self

    def _form_avg(self, team: str, n: int) -> float:
        pts = self._form.get(team)
        return float(np.mean(pts[-n:])) if pts else np.nan

    def predict(self, home_team: str, away_team: str, elo_home: float, elo_away: float) -> np.ndarray:
        """[P(home win), P(draw), P(away win)]. Missing form uses training medians."""
        row = pd.DataFrame([{
            "elo_home": elo_home, "elo_away": elo_away, "elo_diff": elo_home - elo_away,
            "form3_home": self._form_avg(home_team, 3), "form5_home": self._form_avg(home_team, 5),
            "form3_away": self._form_avg(away_team, 3), "form5_away": self._form_avg(away_team, 5),
        }])[FEATURES]
        return self._model.predict_proba(row.fillna(self._medians))[0]
