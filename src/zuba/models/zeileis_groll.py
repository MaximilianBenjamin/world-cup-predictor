"""Zeileis/Groll-style covariate ensemble: match result probabilities.

Based on Groll, Ley, Schauberger & Van Eetvelde (2019, Journal of Quantitative
Analysis in Sports). Instead of recent form, it predicts from team strength and
match context, so it still works for two sides that have rarely met.

Covariates: Elo of both teams and the gap between them, neutral venue, host
nation, major tournament, competitive match, and each side's confederation.

Three classifiers (L1 logistic regression, random forest, XGBoost) are averaged,
then each outcome's probability is recalibrated with isotonic regression.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from zuba.ratings.confederations import confederation_of

_LABELS = {"H": 0, "D": 1, "A": 2}
_CONFEDERATIONS = ["UEFA", "CONMEBOL", "CAF", "AFC", "CONCACAF", "OFC", "Other"]
FEATURES = (
    ["elo_diff", "elo_home", "elo_away", "neutral", "host", "major", "competitive"]
    + [f"confh_{c}" for c in _CONFEDERATIONS]
    + [f"confa_{c}" for c in _CONFEDERATIONS]
)


def build_features(rated: pd.DataFrame) -> pd.DataFrame:
    """Covariate matrix for rows carrying elo_home, elo_away, neutral, major,
    competitive, home_team and away_team."""
    df = pd.DataFrame(index=rated.index)
    df["elo_home"] = rated["elo_home"]
    df["elo_away"] = rated["elo_away"]
    df["elo_diff"] = rated["elo_home"] - rated["elo_away"]
    df["neutral"] = rated["neutral"].astype(bool)
    df["major"] = rated["major"].astype(bool)
    df["competitive"] = rated["competitive"].astype(bool)
    # A home side at a non-neutral tournament game is the host nation.
    df["host"] = df["major"] & ~df["neutral"]
    home_conf = rated["home_team"].map(confederation_of)
    away_conf = rated["away_team"].map(confederation_of)
    for c in _CONFEDERATIONS:
        df[f"confh_{c}"] = home_conf == c
        df[f"confa_{c}"] = away_conf == c
    return df[FEATURES].astype(float)


class ZeileisGroll:
    def __init__(self, random_state: int = 42):
        self._scaler = StandardScaler()
        self._logit = LogisticRegression(
            l1_ratio=1.0, solver="saga", C=1.0, max_iter=5000, random_state=random_state
        )
        self._rf = RandomForestClassifier(
            n_estimators=400, max_depth=8, min_samples_leaf=20,
            random_state=random_state, n_jobs=-1,
        )
        self._xgb = xgb.XGBClassifier(
            n_estimators=400, max_depth=4, learning_rate=0.05,
            objective="multi:softprob", eval_metric="mlogloss",
            random_state=random_state, verbosity=0,
        )
        self._calibrators: list[IsotonicRegression] = []

    def _raw(self, X: np.ndarray) -> np.ndarray:
        """Average of the three classifiers' probabilities."""
        p_logit = self._logit.predict_proba(self._scaler.transform(X))
        return (p_logit + self._rf.predict_proba(X) + self._xgb.predict_proba(X)) / 3.0

    def fit(self, rated: pd.DataFrame) -> ZeileisGroll:
        X = build_features(rated).to_numpy()
        y = rated["result"].map(_LABELS).to_numpy()
        self._logit.fit(self._scaler.fit_transform(X), y)
        self._rf.fit(X, y)
        self._xgb.fit(X, y)

        raw = self._raw(X)
        self._calibrators = [
            IsotonicRegression(out_of_bounds="clip").fit(raw[:, k], (y == k).astype(int))
            for k in range(3)
        ]
        return self

    def predict_proba(self, rated: pd.DataFrame) -> np.ndarray:
        """(N, 3) array of [P(home win), P(draw), P(away win)]."""
        raw = self._raw(build_features(rated).to_numpy())
        cal = np.column_stack([c.predict(raw[:, k]) for k, c in enumerate(self._calibrators)])
        return cal / cal.sum(axis=1, keepdims=True)
