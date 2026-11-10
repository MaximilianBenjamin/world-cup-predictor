"""Fit every model on international history, then predict any fixture.

Match result (home / draw / away) is the average of:
    Dixon-Coles, CatBoost on pi-ratings, LightGBM on Elo and form,
    the Zeileis/Groll ensemble, and (away from neutral venues) raw pi-ratings.
Over/under 2.5 goals is the average of Dixon-Coles and GAP.

A model that can't price a fixture (Dixon-Coles has never seen one of the
teams, say) is left out of that average.

    predictor = Ensemble().fit()                      # about a minute
    print(predictor.predict("Brazil", "Morocco"))

    Ensemble().fit(max_date="2022-11-20")             # only data before Qatar 2022
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from zuba.data import MAJOR_TOURNAMENTS
from zuba.models.catboost_pi import CatBoostPi
from zuba.models.dixon_coles import DixonColes
from zuba.models.elo_lgbm import EloLGBM
from zuba.models.zeileis_groll import ZeileisGroll
from zuba.ratings.elo import InternationalElo, build_international_elo
from zuba.ratings.gap import GAPRatings

logger = logging.getLogger(__name__)

# Models train on matches from this date on. Elo still uses the full history.
TRAIN_FROM = "2006-01-01"


@dataclass
class Prediction:
    home_team: str
    away_team: str
    neutral: bool
    p_home: float
    p_draw: float
    p_away: float
    p_over25: float
    result_models: dict[str, np.ndarray] = field(default_factory=dict)
    goals_models: dict[str, float] = field(default_factory=dict)

    @property
    def probs(self) -> np.ndarray:
        return np.array([self.p_home, self.p_draw, self.p_away])

    def __str__(self) -> str:
        venue = " (neutral)" if self.neutral else ""
        return (
            f"{self.home_team} vs {self.away_team}{venue}\n"
            f"  {self.home_team} {self.p_home:.1%}  Draw {self.p_draw:.1%}  "
            f"{self.away_team} {self.p_away:.1%}   [{len(self.result_models)} models]\n"
            f"  Over 2.5 {self.p_over25:.1%}  Under 2.5 {1 - self.p_over25:.1%}"
            f"   [{len(self.goals_models)} models]"
        )


class Ensemble:
    def __init__(self) -> None:
        self.elo: InternationalElo | None = None
        self.dixon_coles = DixonColes()
        self.catboost = CatBoostPi()
        self.lgbm = EloLGBM()
        self.zeileis = ZeileisGroll()
        self.gap = GAPRatings()

    def fit(self, max_date: str | None = None) -> Ensemble:
        """Train on matches before max_date (default: everything played so far)."""
        rated, self.elo = build_international_elo(min_date=TRAIN_FROM, max_date=max_date)
        logger.info("training on %d matches (%s to %s)",
                    len(rated), rated["date"].min().date(), rated["date"].max().date())
        self.dixon_coles.fit(rated)
        self.catboost.fit(rated)
        self.lgbm.fit(rated)
        self.zeileis.fit(rated)
        self.gap.fit(rated)
        return self

    def _elo(self, team: str) -> float:
        return self.elo.ratings.get(team, self.elo.default_rating)

    def predict(
        self,
        home_team: str,
        away_team: str,
        neutral: bool = True,
        tournament: str = "FIFA World Cup",
    ) -> Prediction:
        if self.elo is None:
            raise RuntimeError("Call fit() before predict().")
        result: dict[str, np.ndarray] = {}
        goals: dict[str, float] = {}
        elo_home, elo_away = self._elo(home_team), self._elo(away_team)

        if {home_team, away_team} <= self.dixon_coles.teams:
            result["dixon_coles"], goals["dixon_coles"] = self.dixon_coles.predict(
                home_team, away_team, neutral)

        result["catboost_pi"] = self.catboost.predict(home_team, away_team, neutral)
        result["elo_lgbm"] = self.lgbm.predict(home_team, away_team, elo_home, elo_away, neutral)
        result["zeileis_groll"] = self.zeileis.predict_proba(pd.DataFrame([{
            "home_team": home_team, "away_team": away_team,
            "elo_home": elo_home, "elo_away": elo_away, "neutral": neutral,
            "major": tournament in MAJOR_TOURNAMENTS, "competitive": tournament != "Friendly",
        }]))[0]

        # penaltyblog's pi-rating probabilities include a fixed home advantage,
        # which would favour whichever team is listed first at a neutral venue.
        if not neutral:
            p = self.catboost.pi.calculate_match_probabilities(home_team, away_team)
            result["pi_ratings"] = np.array([p["home_win"], p["draw"], p["away_win"]])

        goals["gap"] = self.gap.predict(home_team, away_team)["over_2_5"]

        mean = np.mean(list(result.values()), axis=0)
        mean = mean / mean.sum()
        return Prediction(
            home_team=home_team, away_team=away_team, neutral=neutral,
            p_home=float(mean[0]), p_draw=float(mean[1]), p_away=float(mean[2]),
            p_over25=float(np.mean(list(goals.values()))),
            result_models=result, goals_models=goals,
        )
