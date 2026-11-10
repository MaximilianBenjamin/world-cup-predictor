"""Historical international results (martj42/international_results, 1872 onwards).

Every model trains on this one file. `max_date` cuts history off before a given
day, which is how the backtest makes sure a model never sees the matches it is
being scored on.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RESULTS_CSV = Path(__file__).resolve().parents[2] / "data" / "international_results.csv"

# Tournament finals, used as a match-importance feature by the Zeileis-Groll model.
MAJOR_TOURNAMENTS = {
    "FIFA World Cup", "UEFA Euro", "Copa América",
    "African Cup of Nations", "AFC Asian Cup", "UEFA Nations League",
}


def load_international_results(
    min_date: str | None = None,
    max_date: str | None = None,
) -> pd.DataFrame:
    """Played international matches, oldest first.

    Columns: date, home_team, away_team, home_goals, away_goals, result (H/D/A),
    tournament, city, country, neutral, competitive, major.

    min_date keeps matches on or after that day; max_date keeps matches strictly
    before it. Fixtures without a score (future or abandoned games) are dropped.
    """
    df = pd.read_csv(RESULTS_CSV)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.rename(columns={"home_score": "home_goals", "away_score": "away_goals"})
    df = df.dropna(subset=["date", "home_goals", "away_goals"])
    df["home_goals"] = df["home_goals"].astype(int)
    df["away_goals"] = df["away_goals"].astype(int)
    df["neutral"] = df["neutral"].astype(str).str.strip().str.lower() == "true"

    diff = df["home_goals"] - df["away_goals"]
    df["result"] = np.select([diff > 0, diff < 0], ["H", "A"], default="D")
    df["competitive"] = df["tournament"] != "Friendly"
    df["major"] = df["tournament"].isin(MAJOR_TOURNAMENTS)

    if min_date:
        df = df[df["date"] >= pd.Timestamp(min_date)]
    if max_date:
        df = df[df["date"] < pd.Timestamp(max_date)]
    return df.sort_values("date", kind="stable").reset_index(drop=True)
