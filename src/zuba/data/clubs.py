"""English club matches from football-data.co.uk, one CSV per league and season.

`data/clubs/` holds the Premier League and the Championship from 2008-09 on.
The Championship is there so that promoted teams arrive in the Premier League
with a rating history instead of starting from nothing.

Each file carries the result, shots, shots on target, corners and bookmaker
odds. Column names changed several times over the years; this module maps them
onto one set. Expected goals (xG) come from two places: the files themselves
from 2026-27 on, and a separate Understat-derived file for Premier League
matches from August 2014 to January 2025. Matches outside both have no xG.

The odds are kept only as a yardstick for the backtest. No model reads them.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

CLUBS_DIR = Path(__file__).resolve().parents[3] / "data" / "clubs"
XG_CSV = CLUBS_DIR / "epl_xg_2014-2025.csv"

LEAGUES = {"epl": "E0", "championship": "E1"}  # our name -> football-data code

_STATS = {
    "fthg": "home_goals", "ftag": "away_goals",
    "hs": "home_shots", "as": "away_shots",
    "hst": "home_sot", "ast": "away_sot",
    "hc": "home_corners", "ac": "away_corners",
    "hxg": "home_xg", "axg": "away_xg",
}

# Market-average odds, best source first: closing average, Pinnacle closing,
# then the pre-match average (all that exists before 2019-20).
_ODDS = {
    "odds_h": ("avgch", "psch", "avgh", "bbavh", "b365h"),
    "odds_d": ("avgcd", "pscd", "avgd", "bbavd", "b365d"),
    "odds_a": ("avgca", "psca", "avga", "bbava", "b365a"),
    "odds_over": ("avgc>2.5", "pc>2.5", "avg>2.5", "bbav>2.5", "b365>2.5"),
    "odds_under": ("avgc<2.5", "pc<2.5", "avg<2.5", "bbav<2.5", "b365<2.5"),
}

COLUMNS = [
    "date", "season", "league", "home_team", "away_team",
    "home_goals", "away_goals", "result",
    "home_shots", "away_shots", "home_sot", "away_sot",
    "home_corners", "away_corners", "home_xg", "away_xg",
    *_ODDS,
]

_FILE = re.compile(r"^(?P<league>[a-z]+)_(?P<season>\d{4}-\d{2})$")


def season_path(league: str, season: str) -> Path:
    """data/clubs/epl_2026-27.csv for ("epl", "2026-27")."""
    return CLUBS_DIR / f"{league}_{season}.csv"


def _read_season(path: Path, league: str, season: str) -> pd.DataFrame:
    raw = pd.read_csv(path, encoding="utf-8-sig", encoding_errors="replace", low_memory=False)
    raw.columns = [c.strip().lower() for c in raw.columns]
    raw = raw.dropna(subset=["hometeam", "awayteam", "fthg", "ftag"])

    df = pd.DataFrame({
        # Two-digit years up to 2017-18, four-digit after; both day first.
        "date": pd.to_datetime(raw["date"], format="mixed", dayfirst=True, errors="coerce"),
        "season": season,
        "league": league,
        "home_team": raw["hometeam"].str.strip(),
        "away_team": raw["awayteam"].str.strip(),
    })
    for src, dst in _STATS.items():
        df[dst] = pd.to_numeric(raw[src], errors="coerce") if src in raw else np.nan
    for dst, sources in _ODDS.items():
        col = pd.Series(np.nan, index=raw.index)
        for src in sources:
            if src in raw:
                col = col.fillna(pd.to_numeric(raw[src], errors="coerce"))
        df[dst] = col

    df = df.dropna(subset=["date"])
    df[["home_goals", "away_goals"]] = df[["home_goals", "away_goals"]].astype(int)
    diff = df["home_goals"] - df["away_goals"]
    df["result"] = np.select([diff > 0, diff < 0], ["H", "A"], default="D")
    return df[COLUMNS]


def _add_understat_xg(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing xG from the Understat file.

    Understat dates are local kickoff days and occasionally sit a day either
    side of football-data's, so a match is looked up on its own date first and
    then one day earlier and later.
    """
    if not XG_CSV.exists():
        return df
    xg = pd.read_csv(XG_CSV, parse_dates=["date"]).dropna(subset=["home_xg", "away_xg"])
    lookup = xg.set_index(["date", "home_team", "away_team"])[["home_xg", "away_xg"]]
    lookup = lookup[~lookup.index.duplicated()]

    for shift in (0, -1, 1):
        missing = df["home_xg"].isna()
        if not missing.any():
            break
        keys = pd.MultiIndex.from_arrays([
            df.loc[missing, "date"] + pd.Timedelta(days=shift),
            df.loc[missing, "home_team"], df.loc[missing, "away_team"],
        ])
        found = lookup.reindex(keys)
        df.loc[missing, ["home_xg", "away_xg"]] = found.to_numpy()
    return df


def load_club_matches(
    leagues: tuple[str, ...] = ("epl", "championship"),
    min_date: str | None = None,
    max_date: str | None = None,
) -> pd.DataFrame:
    """Played club matches, oldest first.

    Columns: date, season ("2026-27"), league ("epl" or "championship"),
    home_team, away_team, home_goals, away_goals, result (H/D/A), home/away
    shots, sot (shots on target), corners and xg, and market-average decimal
    odds (odds_h, odds_d, odds_a, odds_over, odds_under for 2.5 goals).
    Anything a file doesn't have is NaN.

    min_date keeps matches on or after that day; max_date keeps matches
    strictly before it.
    """
    frames = []
    for path in sorted(CLUBS_DIR.glob("*.csv")):
        m = _FILE.match(path.stem)
        if m and m["league"] in leagues:
            frames.append(_read_season(path, m["league"], m["season"]))
    if not frames:
        raise FileNotFoundError(f"no league files for {leagues} in {CLUBS_DIR}")

    df = pd.concat(frames, ignore_index=True)
    df = _add_understat_xg(df)
    if min_date:
        df = df[df["date"] >= pd.Timestamp(min_date)]
    if max_date:
        df = df[df["date"] < pd.Timestamp(max_date)]
    return df.sort_values(["date", "league", "home_team"], kind="stable").reset_index(drop=True)
