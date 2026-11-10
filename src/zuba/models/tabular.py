"""Gradient-boosted trees on a table of pre-match features.

Two models share one training routine:

    ResultBooster   match result -> [P(home win), P(draw), P(away win)]
    GoalsBooster    each side's expected goals -> P(total goals over a line)

Both stop adding trees when they stop helping. The most recent 15% of the
training matches are held back, trees are added until the loss on those matches
hasn't improved for 50 rounds, and the model is then refitted on everything
with that many trees. Without this the boosters memorise their training set:
a football result is mostly noise and a few hundred shallow trees are plenty.

Missing values (no expected goals before 2014, a promoted side's first games)
are passed through as NaN, which all three libraries split on directly.
"""

from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb
from catboost import CatBoostClassifier
from scipy.stats import poisson

LABELS = {"H": 0, "D": 1, "A": 2}
MAX_TREES = 1500
PATIENCE = 50
HOLDOUT = 0.15
SEED = 42


def _catboost(trees: int) -> CatBoostClassifier:
    return CatBoostClassifier(iterations=trees, depth=4, learning_rate=0.03, l2_leaf_reg=5.0,
                              loss_function="MultiClass", random_seed=SEED, verbose=False,
                              allow_writing_files=False, thread_count=4)


def _lightgbm(trees: int) -> lgb.LGBMClassifier:
    return lgb.LGBMClassifier(n_estimators=trees, learning_rate=0.03, num_leaves=8,
                              min_child_samples=60, subsample=0.8, subsample_freq=1,
                              colsample_bytree=0.8, reg_lambda=5.0, objective="multiclass",
                              random_state=SEED, verbose=-1, n_jobs=4)


def _xgboost(trees: int) -> xgb.XGBClassifier:
    return xgb.XGBClassifier(n_estimators=trees, learning_rate=0.03, max_depth=3,
                             min_child_weight=20, subsample=0.8, colsample_bytree=0.6,
                             reg_lambda=5.0, objective="multi:softprob", eval_metric="mlogloss",
                             random_state=SEED, verbosity=0, n_jobs=4)


def _xgboost_poisson(trees: int) -> xgb.XGBRegressor:
    return xgb.XGBRegressor(n_estimators=trees, learning_rate=0.03, max_depth=3,
                            min_child_weight=20, subsample=0.8, colsample_bytree=0.6,
                            reg_lambda=5.0, objective="count:poisson",
                            eval_metric="poisson-nloglik", random_state=SEED, verbosity=0,
                            n_jobs=4)


_MAKERS = {"catboost": _catboost, "lightgbm": _lightgbm, "xgboost": _xgboost,
           "xgboost_poisson": _xgboost_poisson}


def _best_tree_count(kind: str, X: np.ndarray, y: np.ndarray) -> int:
    """How many trees to use, judged on the most recent part of the data.
    X must be in date order."""
    cut = int(len(X) * (1 - HOLDOUT))
    train, held = (X[:cut], y[:cut]), (X[cut:], y[cut:])
    model = _MAKERS[kind](MAX_TREES)
    if kind == "catboost":
        model.fit(*train, eval_set=held, early_stopping_rounds=PATIENCE)
        best = model.get_best_iteration()
    elif kind == "lightgbm":
        model.fit(*train, eval_X=held[0], eval_y=held[1],
                  callbacks=[lgb.early_stopping(PATIENCE, verbose=False)])
        best = model.best_iteration_
    else:
        model.set_params(early_stopping_rounds=PATIENCE)
        model.fit(*train, eval_set=[held], verbose=False)
        best = model.best_iteration
    return max(int(best or 0) + 1, 20)


def _fit(kind: str, X: np.ndarray, y: np.ndarray):
    trees = _best_tree_count(kind, X, y)
    return _MAKERS[kind](trees).fit(X, y), trees


class ResultBooster:
    """kind: "catboost", "lightgbm" or "xgboost". features: columns to read."""

    def __init__(self, kind: str, features: list[str]):
        self.kind = kind
        self.features = features
        self.trees = 0
        self._model = None

    def fit(self, matches: pd.DataFrame) -> ResultBooster:
        """matches: played games in date order, with the feature columns and `result`."""
        X = matches[self.features].to_numpy(float)
        y = matches["result"].map(LABELS).to_numpy(int)
        self._model, self.trees = _fit(self.kind, X, y)
        return self

    def predict(self, matches: pd.DataFrame) -> np.ndarray:
        """(N, 3) array of [P(home win), P(draw), P(away win)]."""
        return np.asarray(self._model.predict_proba(matches[self.features].to_numpy(float)))


class GoalsBooster:
    """Expected goals for each side from Poisson-loss trees. The total is treated
    as Poisson with the two means added, which gives a probability for any line."""

    def __init__(self, features: list[str]):
        self.features = features
        self._home = None
        self._away = None

    def fit(self, matches: pd.DataFrame) -> GoalsBooster:
        X = matches[self.features].to_numpy(float)
        self._home, _ = _fit("xgboost_poisson", X, matches["home_goals"].to_numpy(float))
        self._away, _ = _fit("xgboost_poisson", X, matches["away_goals"].to_numpy(float))
        return self

    def expected_goals(self, matches: pd.DataFrame) -> np.ndarray:
        """(N, 2) array of expected home and away goals."""
        X = matches[self.features].to_numpy(float)
        return np.column_stack([self._home.predict(X), self._away.predict(X)])

    def predict_over(self, matches: pd.DataFrame, line: float = 2.5) -> np.ndarray:
        """P(total goals > line) for each match."""
        total = self.expected_goals(matches).sum(axis=1)
        return poisson.sf(np.floor(line), total)
