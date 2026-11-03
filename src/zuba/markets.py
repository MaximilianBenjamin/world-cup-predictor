"""Turn model output into the probabilities the site shows, and store them.

For each fixture:
  - match result and double chance come from the ensemble average;
  - over/under at 0.5 to 4.5 goals and expected goals come from the
    Dixon-Coles scoreline grid;
  - "result and over/under" pairs (e.g. home win AND over 2.5) are summed
    directly from the same grid. Multiplying the two separate probabilities
    would be wrong, because a home win and lots of goals are correlated.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import sqlite3

import numpy as np

from zuba.db import get_connection
from zuba.ensemble import Ensemble

logger = logging.getLogger(__name__)

MODEL_VERSION = "1.0"
OU_LINES = {"0_5": 0.5, "1_5": 1.5, "2_5": 2.5, "3_5": 3.5, "4_5": 4.5}
JOINT_LINES = {"15": 1.5, "25": 2.5, "35": 3.5}


def grid_markets(grid: np.ndarray) -> dict[str, float]:
    """Over/under and result-and-over/under probabilities from a scoreline grid,
    where grid[i, j] = P(home scores i, away scores j)."""
    M = np.asarray(grid, dtype=float)
    home, away = np.indices(M.shape)
    total = home + away
    outcome = {"h": home > away, "a": home < away, "dc1x": home >= away, "dcx2": home <= away}

    out = {f"over_{k}_p": float(M[total > line].sum()) for k, line in OU_LINES.items()}
    for prefix, mask in outcome.items():
        for k, line in JOINT_LINES.items():
            out[f"{prefix}_o{k}_p"] = float(M[mask & (total > line)].sum())
            out[f"{prefix}_u{k}_p"] = float(M[mask & (total < line)].sum())
    return out


def fixture_probs(model: Ensemble, home: str, away: str, neutral: bool = True) -> dict | None:
    """All probabilities for one fixture, or None if Dixon-Coles can't price it."""
    if not {home, away} <= model.dixon_coles.teams:
        return None
    pred = model.predict(home, away, neutral=neutral)
    grid = model.dixon_coles.grid(home, away)
    return {
        "home_win_p": pred.p_home, "draw_p": pred.p_draw, "away_win_p": pred.p_away,
        "dc_1x_p": pred.p_home + pred.p_draw,
        "dc_12_p": pred.p_home + pred.p_away,
        "dc_x2_p": pred.p_draw + pred.p_away,
        "exp_home_goals": float(grid.home_goal_expectation),
        "exp_away_goals": float(grid.away_goal_expectation),
        **grid_markets(grid.grid),
    }


def predict_upcoming(conn: sqlite3.Connection | None = None, model: Ensemble | None = None) -> int:
    """Price every unplayed fixture in the database. Returns how many were saved."""
    conn = conn or get_connection()
    fixtures = conn.execute(
        "SELECT match_id, home_team, away_team, neutral FROM matches WHERE completed = 0"
    ).fetchall()
    if not fixtures:
        return 0

    model = model or Ensemble().fit()
    now = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
    saved = 0
    for f in fixtures:
        probs = fixture_probs(model, f["home_team"], f["away_team"], bool(f["neutral"]))
        if probs is None:
            logger.warning("skipping %s vs %s: team not in training data",
                           f["home_team"], f["away_team"])
            continue
        conn.execute(
            "INSERT OR REPLACE INTO predictions (match_id, generated_at, model_version, probs) "
            "VALUES (?, ?, ?, ?)",
            (f["match_id"], now, MODEL_VERSION, json.dumps(probs)),
        )
        saved += 1
    conn.commit()
    return saved
