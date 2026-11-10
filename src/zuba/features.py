"""Pre-match features for club games.

`build_club_features` takes every match in date order and adds, for each one,
what was known before kickoff: both sides' Elo and pi-ratings, their averages
over the last 5 and 10 games (points, goals, shots, shots on target, corners
and expected goals, for and against), days of rest, and how many of their last
38 league games were in the top flight.

Fixtures that haven't been played go through the same function as rows with no
score. They pick up features from the games before them and change nothing, so
the backtest and the live site compute features with the same code.
"""

from __future__ import annotations

import pandas as pd

from zuba.ratings.elo import add_club_elo
from zuba.ratings.pi import PI_FEATURES, build_pi_features

WINDOWS = (5, 10)
# name in the feature -> (column when the team is at home, column when away)
_FOR_AGAINST = {
    "gf": ("home_goals", "away_goals"), "ga": ("away_goals", "home_goals"),
    "sf": ("home_shots", "away_shots"), "sa": ("away_shots", "home_shots"),
    "sotf": ("home_sot", "away_sot"), "sota": ("away_sot", "home_sot"),
    "cf": ("home_corners", "away_corners"), "ca": ("away_corners", "home_corners"),
    "xgf": ("home_xg", "away_xg"), "xga": ("away_xg", "home_xg"),
}
_ROLLED = ["pts", *_FOR_AGAINST]
MAX_REST_DAYS = 21

ELO_FEATURES = ["elo_home", "elo_away", "elo_diff"]
TOP_FLIGHT_FEATURES = ["home_top38", "away_top38"]
FORM_FEATURES = [f"{side}_pts{w}" for side in ("home", "away") for w in WINDOWS]
STAT_FEATURES = [f"{side}_{stat}{w}" for side in ("home", "away")
                 for stat in _FOR_AGAINST for w in WINDOWS]
REST_FEATURES = ["home_rest", "away_rest"]
ALL_FEATURES = [*ELO_FEATURES, *PI_FEATURES, *TOP_FLIGHT_FEATURES, *FORM_FEATURES,
                *STAT_FEATURES, *REST_FEATURES]


def _team_rows(df: pd.DataFrame, side: str) -> pd.DataFrame:
    """One row per match from one side's point of view."""
    home = side == "home"
    gf = df["home_goals"] if home else df["away_goals"]
    ga = df["away_goals"] if home else df["home_goals"]
    pts = (gf > ga) * 3.0 + (gf == ga) * 1.0
    out = pd.DataFrame({
        "match": df.index, "side": side, "date": df["date"],
        "team": df[f"{side}_team"],
        "pts": pts.where(gf.notna()),
        "top": (df["league"] == "epl").astype(float),
    })
    for name, (when_home, when_away) in _FOR_AGAINST.items():
        out[name] = df[when_home if home else when_away]
    return out


def build_club_features(matches: pd.DataFrame) -> pd.DataFrame:
    """Add every column in ALL_FEATURES to club matches.

    matches: the columns of `load_club_matches`, played or not. Returned in
    date order with a fresh index.
    """
    df = matches.sort_values("date", kind="stable").reset_index(drop=True)
    df = add_club_elo(df)
    df, _ = build_pi_features(df)

    long = pd.concat([_team_rows(df, "home"), _team_rows(df, "away")], ignore_index=True)
    long = long.sort_values(["team", "date", "match"], kind="stable")
    by_team = long.groupby("team", sort=False)

    # shift(1) drops the current match, so each average covers earlier games only.
    for col in _ROLLED:
        before = by_team[col].shift(1)
        for w in WINDOWS:
            long[f"{col}{w}"] = (before.groupby(long["team"], sort=False)
                                 .rolling(w, min_periods=1).mean()
                                 .reset_index(level=0, drop=True))
    long["top38"] = (by_team["top"].shift(1).groupby(long["team"], sort=False)
                     .rolling(38, min_periods=1).sum()
                     .reset_index(level=0, drop=True)).fillna(0.0)
    long["rest"] = by_team["date"].diff().dt.days.clip(upper=MAX_REST_DAYS)

    per_team = [f"{col}{w}" for col in _ROLLED for w in WINDOWS] + ["top38", "rest"]
    for side in ("home", "away"):
        part = long[long["side"] == side].set_index("match")[per_team]
        df = df.join(part.add_prefix(f"{side}_"))
    return df
