"""CatBoost on pi-ratings: match result probabilities.

Berrar, Lopes & Dubitzky (2024, Machine Learning 113) won the 2023 Soccer
Prediction Challenge with this setup and found that adding features beyond the
pi-ratings gave almost nothing extra.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from penaltyblog.ratings import PiRatingSystem

from zuba.ratings.pi import PI_FEATURES, build_pi_features, pi_row

_LABELS = {"H": 0, "D": 1, "A": 2}


class CatBoostPi:
    def __init__(self, iterations: int = 500, depth: int = 6, learning_rate: float = 0.05):
        self._model = CatBoostClassifier(
            iterations=iterations,
            depth=depth,
            learning_rate=learning_rate,
            loss_function="MultiClass",
            random_seed=42,
            verbose=False,
        )
        self.pi: PiRatingSystem | None = None

    def fit(self, matches: pd.DataFrame) -> CatBoostPi:
        """matches: date, home_team, away_team, home_goals, away_goals, result."""
        df, self.pi = build_pi_features(matches)
        self._model.fit(df[PI_FEATURES].to_numpy(float), df["result"].map(_LABELS).to_numpy())
        return self

    def predict(self, home_team: str, away_team: str) -> np.ndarray:
        """[P(home win), P(draw), P(away win)] from the latest ratings."""
        row = pi_row(self.pi, home_team, away_team)
        X = np.array([[row[c] for c in PI_FEATURES]], dtype=float)
        return self._model.predict_proba(X)[0]
