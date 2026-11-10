"""CatBoost on pi-ratings: match result probabilities.

Berrar, Lopes & Dubitzky (2024, Machine Learning 113) won the 2023 Soccer
Prediction Challenge with this setup and found that adding features beyond the
pi-ratings gave almost nothing extra. The one addition here is a neutral-venue
flag: pi-ratings keep separate home and away ratings, and at a World Cup neither
side is at home. The number of trees is set by early stopping (see
`zuba.models.tabular`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from penaltyblog.ratings import PiRatingSystem

from zuba.models.tabular import ResultBooster
from zuba.ratings.pi import PI_FEATURES, build_pi_features, pi_row

FEATURES = [*PI_FEATURES, "neutral"]


class CatBoostPi:
    def __init__(self) -> None:
        self._model = ResultBooster("catboost", FEATURES)
        self.pi: PiRatingSystem | None = None

    def fit(self, matches: pd.DataFrame) -> CatBoostPi:
        """matches: date, home_team, away_team, home_goals, away_goals, neutral, result."""
        df, self.pi = build_pi_features(matches)
        self._model.fit(df)
        return self

    def predict(self, home_team: str, away_team: str, neutral: bool = True) -> np.ndarray:
        """[P(home win), P(draw), P(away win)] from the latest ratings."""
        row = {**pi_row(self.pi, home_team, away_team), "neutral": neutral}
        return self._model.predict(pd.DataFrame([row]))[0]
