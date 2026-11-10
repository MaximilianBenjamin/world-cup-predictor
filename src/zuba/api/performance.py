"""How the Premier League model has done: the backtest, and this season so far.

The season record pairs every finished match with the probabilities the model
gave before kickoff. Those come from two places. The backtest file holds a
walk-forward prediction for every match played before it was last run. The
database holds the prediction that was on the site when each later match
kicked off: predictions are only ever rewritten for unplayed fixtures, so once
a match is finished its row is what the model said beforehand.
"""

from __future__ import annotations

import json
import math
import sqlite3

import pandas as pd

from zuba.data.fetch import current_season
from zuba.evaluate.report import PREDICTIONS_CSV, REPORT_JSON
from zuba.evaluate.walkforward import result_columns


def backtest_report() -> dict | None:
    return json.loads(REPORT_JSON.read_text()) if REPORT_JSON.exists() else None


def _game(date: str, home: str, away: str, home_score: int, away_score: int,
          probs: tuple[float, float, float]) -> dict:
    happened = 0 if home_score > away_score else 1 if home_score == away_score else 2
    return {
        "date": date, "home_team": home, "away_team": away,
        "home_score": home_score, "away_score": away_score,
        "p_home": probs[0], "p_draw": probs[1], "p_away": probs[2],
        "p_result": probs[happened],
        "correct": max(range(3), key=probs.__getitem__) == happened,
    }


def season_record(conn: sqlite3.Connection, season: str | None = None) -> dict:
    season = season or current_season()
    games: dict[tuple[str, str], dict] = {}   # (home, away) is unique within a season

    if PREDICTIONS_CSV.exists():
        past = pd.read_csv(PREDICTIONS_CSV)
        past = past[past["season"] == season].dropna(subset=result_columns("blend"))
        scores = _scores(season)
        for row in past.itertuples(index=False):
            key = (row.home_team, row.away_team)
            if key in scores:
                games[key] = _game(str(row.date)[:10], *key, *scores[key],
                                   (row.blend_h, row.blend_d, row.blend_a))

    start = f"{season[:4]}-07-01"
    rows = conn.execute(
        "SELECT m.date, m.home_team, m.away_team, m.home_score, m.away_score, p.probs "
        "FROM matches m JOIN predictions p USING (match_id) "
        "WHERE m.competition = 'epl' AND m.completed = 1 AND m.home_score IS NOT NULL "
        "AND m.date >= ?", (start,),
    )
    for r in rows:
        key = (r["home_team"], r["away_team"])
        if key not in games:
            p = json.loads(r["probs"])
            games[key] = _game(r["date"], *key, r["home_score"], r["away_score"],
                               (p["home_win_p"], p["draw_p"], p["away_win_p"]))

    ordered = sorted(games.values(), key=lambda g: g["date"], reverse=True)
    n = len(ordered)
    return {
        "season": season, "matches": n,
        "correct": sum(g["correct"] for g in ordered),
        "log_loss": -sum(math.log(max(g["p_result"], 1e-12)) for g in ordered) / n if n else None,
        "games": ordered,
    }


def _scores(season: str) -> dict[tuple[str, str], tuple[int, int]]:
    from zuba.data import load_club_matches

    played = load_club_matches(leagues=("epl",), min_date=f"{season[:4]}-07-01")
    played = played[played["season"] == season]
    return {(r.home_team, r.away_team): (int(r.home_goals), int(r.away_goals))
            for r in played.itertuples(index=False)}
