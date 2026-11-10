"""Dixon-Coles scoreline model (Dixon & Coles 1997, Applied Statistics).

A Poisson model for each side's goals, with a correction for the low scores
(0-0, 1-0, 0-1, 1-1) that independent Poissons get wrong. It produces a full
grid of scoreline probabilities, so every goals-based market (result, over/under
at any line, result and over/under together) is a sum over part of that grid.

Wraps penaltyblog's DixonColesGoalModel. Older matches are down-weighted with
exp(-xi * days_ago).

The model has one home-advantage term. Matches at neutral venues are flagged so
that they don't feed it, and a prediction for a neutral venue leaves it out.
Without that, whichever team is listed first at a World Cup is treated as if it
were playing at home.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from penaltyblog.models import DixonColesGoalModel, FootballProbabilityGrid


class DixonColes:
    def __init__(self, xi: float = 0.001, max_goals: int = 10):
        # National teams play rarely, so xi is lower (slower decay) than the
        # 0.0018 commonly used for club leagues.
        self.xi = xi
        self.max_goals = max_goals
        self._model: DixonColesGoalModel | None = None
        self.teams: set[str] = set()

    def fit(self, df: pd.DataFrame) -> DixonColes:
        """df needs date, home_team, away_team, home_goals, away_goals, and
        optionally neutral (taken as False when absent)."""
        neutral = df["neutral"].to_numpy(bool).astype(int) if "neutral" in df else None
        days_ago = (df["date"].max() - df["date"]).dt.days.to_numpy()
        self._model = DixonColesGoalModel(
            goals_home=df["home_goals"].to_numpy(int),
            goals_away=df["away_goals"].to_numpy(int),
            teams_home=df["home_team"].to_numpy(),
            teams_away=df["away_team"].to_numpy(),
            weights=np.exp(-self.xi * days_ago),
            neutral_venue=neutral,
        )
        self._model.fit()
        self.teams = set(df["home_team"]) | set(df["away_team"])
        return self

    def grid(self, home_team: str, away_team: str, neutral: bool = False) -> FootballProbabilityGrid:
        """Scoreline probability grid. Both teams must have been in the training data."""
        if self._model is None:
            raise RuntimeError("Call fit() before grid().")
        return self._model.predict(home_team, away_team, max_goals=self.max_goals,
                                   neutral_venue=neutral)

    def predict(self, home_team: str, away_team: str,
                neutral: bool = False) -> tuple[np.ndarray, float]:
        """([P(home win), P(draw), P(away win)], P(over 2.5 goals))."""
        g = self.grid(home_team, away_team, neutral)
        # penaltyblog's totals(line) returns (under, push, over), in that order.
        # Reading it the other way round silently swaps over and under.
        _, _, over = g.totals(2.5)
        return np.array([g.home_win, g.draw, g.away_win]), float(over)
