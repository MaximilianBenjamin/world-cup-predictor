"""Premier League model stack.

Match result (home / draw / away):
    dixon_coles   scoreline model fitted to goals
    catboost_pi   CatBoost on pi-ratings
    elo_lgbm      LightGBM on Elo and recent points
    form_xgb      XGBoost on everything: ratings plus 5- and 10-game averages of
                  goals, shots, shots on target, corners and expected goals

Over/under 2.5 goals:
    dixon_coles   from the same scoreline grid
    gap_shots, gap_sot, gap_corners
                  GAP ratings built on shots, shots on target and corners
    goals_xgb     Poisson-loss XGBoost for each side's goals

The stack works on the table from `build_club_features`. The boosted models
learn from every match in it. Dixon-Coles and GAP hold one set of numbers per
team, so they are fitted on recent seasons only.

    table = build_club_features(load_club_matches())
    stack = PremierLeague().fit(table[table["date"] < "2026-11-10"])
    stack.predict(fixtures)          # rows of the same table, played or not
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from zuba.data.clubs import CLUBS_DIR, load_club_matches
from zuba.data.fetch import current_season
from zuba.features import (
    ALL_FEATURES,
    ELO_FEATURES,
    FORM_FEATURES,
    TOP_FLIGHT_FEATURES,
    build_club_features,
)
from zuba.models.dixon_coles import DixonColes
from zuba.models.tabular import GoalsBooster, ResultBooster
from zuba.ratings.gap import GAPRatings
from zuba.ratings.pi import PI_FEATURES
from zuba.stacks.blend import blend

logger = logging.getLogger(__name__)

RESULT_MODELS = ("dixon_coles", "catboost_pi", "elo_lgbm", "form_xgb")
GOALS_MODELS = ("dixon_coles", "gap_shots", "gap_sot", "gap_corners", "goals_xgb")

# Dixon-Coles and GAP see this much history. Older games say little about a
# squad that has since changed.
TEAM_MODEL_YEARS = 4
# Per day. Refitting weekly over 2017-2026 (3,420 matches), result log loss was
# 0.976 at 0.001, 0.972 at 0.0018 and 0.971 at 0.003: flat, so the usual club
# value stays. Fitting on the Premier League alone scored 0.975.
DIXON_COLES_DECAY = 0.0018


@dataclass
class Predictions:
    """Per-model and blended probabilities for a set of fixtures, in row order."""

    result: np.ndarray                      # (N, 3) blended [home, draw, away]
    over25: np.ndarray                      # (N,) blended P(over 2.5 goals)
    result_models: dict[str, np.ndarray] = field(default_factory=dict)
    goals_models: dict[str, np.ndarray] = field(default_factory=dict)


class PremierLeague:
    def __init__(self, result_weights: dict[str, float] | None = None,
                 goals_weights: dict[str, float] | None = None):
        """Weights for blending the models; None means a plain average."""
        self.result_weights = result_weights
        self.goals_weights = goals_weights
        self.dixon_coles = DixonColes(xi=DIXON_COLES_DECAY)
        self.catboost_pi = ResultBooster("catboost", [*PI_FEATURES, *TOP_FLIGHT_FEATURES])
        self.elo_lgbm = ResultBooster(
            "lightgbm", [*ELO_FEATURES, *FORM_FEATURES, *TOP_FLIGHT_FEATURES])
        self.form_xgb = ResultBooster("xgboost", ALL_FEATURES)
        self.goals_xgb = GoalsBooster(ALL_FEATURES)
        self.gap = {m: GAPRatings(m) for m in ("shots", "sot", "corners")}

    # ---- fitting ------------------------------------------------------------

    def fit_boosters(self, played: pd.DataFrame) -> PremierLeague:
        """Fit the tree models. played: finished matches in date order."""
        for model in (self.catboost_pi, self.elo_lgbm, self.form_xgb, self.goals_xgb):
            model.fit(played)
        return self

    def fit_team_models(self, played: pd.DataFrame) -> PremierLeague:
        """Fit Dixon-Coles and GAP on the last few seasons of `played`."""
        start = played["date"].max() - pd.DateOffset(years=TEAM_MODEL_YEARS)
        recent = played[played["date"] > start]
        self.dixon_coles.fit(recent)
        for model in self.gap.values():
            model.fit(recent)
        return self

    def fit(self, played: pd.DataFrame) -> PremierLeague:
        logger.info("training on %d matches (%s to %s)", len(played),
                    played["date"].min().date(), played["date"].max().date())
        return self.fit_boosters(played).fit_team_models(played)

    # ---- predicting ---------------------------------------------------------

    def predict(self, fixtures: pd.DataFrame) -> Predictions:
        """fixtures: rows of the feature table. A model that can't price a row
        (a team Dixon-Coles has never seen) gives NaN there and is left out of
        that row's blend."""
        n = len(fixtures)
        pairs = list(zip(fixtures["home_team"], fixtures["away_team"], strict=True))

        dc_result = np.full((n, 3), np.nan)
        dc_over = np.full(n, np.nan)
        for i, (home, away) in enumerate(pairs):
            if {home, away} <= self.dixon_coles.teams:
                dc_result[i], dc_over[i] = self.dixon_coles.predict(home, away)

        result = {
            "dixon_coles": dc_result,
            "catboost_pi": self.catboost_pi.predict(fixtures),
            "elo_lgbm": self.elo_lgbm.predict(fixtures),
            "form_xgb": self.form_xgb.predict(fixtures),
        }
        goals = {"dixon_coles": dc_over}
        for measure, model in self.gap.items():
            known = model.teams
            goals[f"gap_{measure}"] = np.array([
                model.predict(home, away)["over_2_5"] if {home, away} <= known else np.nan
                for home, away in pairs
            ])
        goals["goals_xgb"] = self.goals_xgb.predict_over(fixtures, 2.5)

        return Predictions(
            result=blend(result, self.result_weights),
            over25=blend(goals, self.goals_weights),
            result_models=result, goals_models=goals,
        )


# ---- pricing fixtures that haven't been played -------------------------------

WEIGHTS_JSON = CLUBS_DIR.parent / "blend_epl.json"
TRAIN_FROM = "2009-08-01"  # the first season in the data only warms up the ratings


def load_weights() -> tuple[dict[str, float] | None, dict[str, float] | None]:
    """Blend weights written by the backtest, or (None, None) if it hasn't been run."""
    if not WEIGHTS_JSON.exists():
        return None, None
    saved = json.loads(WEIGHTS_JSON.read_text())
    return saved.get("result"), saved.get("goals")


def price_fixtures(fixtures: pd.DataFrame) -> tuple[pd.DataFrame, Predictions, PremierLeague]:
    """Fit on every played match and predict `fixtures`.

    fixtures: date, home_team, away_team for Premier League games not yet
    played, with club names as football-data.co.uk spells them. Returns the
    fixtures (in date order, with their features), the predictions in the same
    order, and the fitted stack.
    """
    played = load_club_matches()
    todo = fixtures[["date", "home_team", "away_team"]].copy()
    todo["date"] = pd.to_datetime(todo["date"])
    unknown = (set(todo["home_team"]) | set(todo["away_team"])) - set(played["home_team"])
    if unknown:
        raise ValueError(f"teams not in the training data: {sorted(unknown)}")
    todo["league"] = "epl"
    todo["season"] = current_season(todo["date"].min().date())

    table = build_club_features(pd.concat([played, todo], ignore_index=True))
    is_fixture = table["home_goals"].isna()
    train = table[~is_fixture & (table["date"] >= TRAIN_FROM)]
    stack = PremierLeague(*load_weights()).fit(train)
    rows = table[is_fixture].reset_index(drop=True)
    return rows, stack.predict(rows), stack
