"""World Football Elo Ratings — computed from match results (eloratings.net method).

Rather than scraping eloratings.net (which exposes only current snapshots, not the
leak-free point-in-time pre-match ratings a model needs), we replicate the published
formula and roll it forward over the full international match history. Each fixture is
stamped with both teams' Elo *as of kickoff* (before the result is applied), giving a
clean, reproducible, no-leakage feature series.

Method (https://www.eloratings.net/about):
  K-factor by competition weight (tournament importance)
  G goal-difference multiplier
  home advantage of +100 to the non-neutral host
  R' = R + K * G * (W - E)
"""

from __future__ import annotations

import re

import pandas as pd

from zuba.data import load_international_results

DEFAULT_RATING = 1500.0
HOME_ADVANTAGE = 100.0

# K-factor (match weight) by competition importance, eloratings.net scheme.
K_WORLD_CUP = 60.0
K_CONTINENTAL_FINAL = 50.0
K_QUALIFIER = 40.0
K_MINOR_TOURNAMENT = 30.0
K_FRIENDLY = 20.0

# Continental championship finals (not qualifiers) — K=50.
_CONTINENTAL_FINALS = {
    "UEFA Euro", "Copa América", "African Cup of Nations",
    "AFC Asian Cup", "CONCACAF Championship", "Gold Cup",
    "UEFA Nations League", "OFC Nations Cup",
}

_QUALIFIER_RE = re.compile(r"qualif", re.IGNORECASE)


def _k_factor(tournament: str) -> float:
    t = tournament or ""
    if t == "FIFA World Cup":
        return K_WORLD_CUP
    if _QUALIFIER_RE.search(t):
        return K_QUALIFIER
    if t in _CONTINENTAL_FINALS:
        return K_CONTINENTAL_FINAL
    if t == "Friendly":
        return K_FRIENDLY
    return K_MINOR_TOURNAMENT


def _goal_diff_multiplier(goal_diff: int) -> float:
    """eloratings.net goal-difference weighting G."""
    d = abs(goal_diff)
    if d <= 1:
        return 1.0
    if d == 2:
        return 1.5
    return (11.0 + d) / 8.0


def _expected(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


class InternationalElo:
    """Rolling Elo over international fixtures.

    Usage:
        elo = InternationalElo()
        rated = elo.run(df)          # df: date, home_team, away_team,
                                     #     home_goals, away_goals, tournament, neutral
        # rated adds: elo_home, elo_away, elo_diff (all PRE-match, leak-free)
        elo.ratings["Brazil"]        # final rating after run
    """

    def __init__(self, default_rating: float = DEFAULT_RATING) -> None:
        self.default_rating = default_rating
        self.ratings: dict[str, float] = {}

    def _get(self, team: str) -> float:
        return self.ratings.get(team, self.default_rating)

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process fixtures chronologically, stamping pre-match Elo on each row."""
        df = df.sort_values("date").reset_index(drop=True)
        elo_home = []
        elo_away = []

        for row in df.itertuples(index=False):
            h, a = row.home_team, row.away_team
            r_h, r_a = self._get(h), self._get(a)

            # Stamp PRE-match ratings (no leakage).
            elo_home.append(r_h)
            elo_away.append(r_a)

            neutral = bool(getattr(row, "neutral", False))
            ha = 0.0 if neutral else HOME_ADVANTAGE
            e_h = _expected(r_h + ha, r_a)

            gd = int(row.home_goals) - int(row.away_goals)
            if gd > 0:
                w_h = 1.0
            elif gd < 0:
                w_h = 0.0
            else:
                w_h = 0.5

            k = _k_factor(getattr(row, "tournament", "")) * _goal_diff_multiplier(gd)
            delta = k * (w_h - e_h)
            self.ratings[h] = r_h + delta
            self.ratings[a] = r_a - delta

        out = df.copy()
        out["elo_home"] = elo_home
        out["elo_away"] = elo_away
        out["elo_diff"] = out["elo_home"] - out["elo_away"]
        return out


def build_international_elo(
    min_date: str | None = None,
    max_date: str | None = None,
) -> tuple[pd.DataFrame, InternationalElo]:
    """Rate every international match before `max_date`, then return the rows
    from `min_date` on.

    Ratings are always warmed up on the full history back to 1872, so teams
    don't start the modelling window at the default 1500.
    """
    full = load_international_results(max_date=max_date)
    elo = InternationalElo()
    rated = elo.run(full)
    if min_date:
        rated = rated[rated["date"] >= pd.Timestamp(min_date)].reset_index(drop=True)
    return rated, elo


# ---- clubs ------------------------------------------------------------------

CLUB_K = 20.0
CLUB_HOME_ADVANTAGE = 60.0
# A club first seen in the second tier starts lower than one first seen in the top flight.
CLUB_START = {"epl": 1500.0, "championship": 1350.0}


def add_club_elo(df: pd.DataFrame, k: float = CLUB_K,
                 home_advantage: float = CLUB_HOME_ADVANTAGE) -> pd.DataFrame:
    """Add pre-match elo_home, elo_away and elo_diff to club matches.

    df needs date, league, home_team, away_team, home_goals, away_goals, already
    in date order. Rows without a score (fixtures not yet played) get ratings
    but don't change them.

    The Premier League and the Championship are rated in one pool. The two only
    meet through promotion and relegation, so a promoted side's rating overstates
    it against top-flight teams; models that use these ratings also get a count
    of each side's recent top-flight games to correct for that.
    """
    ratings: dict[str, float] = {}
    elo_home, elo_away = [], []
    for row in df.itertuples(index=False):
        start = CLUB_START.get(row.league, DEFAULT_RATING)
        r_h = ratings.setdefault(row.home_team, start)
        r_a = ratings.setdefault(row.away_team, start)
        elo_home.append(r_h)
        elo_away.append(r_a)
        if pd.isna(row.home_goals) or pd.isna(row.away_goals):
            continue
        gd = int(row.home_goals) - int(row.away_goals)
        won = 1.0 if gd > 0 else 0.0 if gd < 0 else 0.5
        delta = k * _goal_diff_multiplier(gd) * (won - _expected(r_h + home_advantage, r_a))
        ratings[row.home_team] = r_h + delta
        ratings[row.away_team] = r_a - delta

    out = df.copy()
    out["elo_home"] = elo_home
    out["elo_away"] = elo_away
    out["elo_diff"] = out["elo_home"] - out["elo_away"]
    return out
