"""Turn model output into the probabilities the site shows, and store them.

Every number for a fixture is read off one grid of scoreline probabilities.
Dixon-Coles supplies the grid; it is then rescaled so that its home/draw/away
totals and its over/under 2.5 split equal the blended figures from the whole
model stack (`reconcile_grid`). Because everything comes from the same grid,
the markets agree with each other: the three "home win and over/under" pairs
add up to the home-win probability, and so on.

"Result and over/under" pairs (e.g. home win AND over 2.5) are summed directly
from the grid. Multiplying the two separate probabilities would be wrong,
because a home win and lots of goals are correlated.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import sqlite3

import numpy as np
import pandas as pd

from zuba.db import get_connection
from zuba.ensemble import Ensemble

logger = logging.getLogger(__name__)

MODEL_VERSION = "2.0"
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


def reconcile_grid(grid: np.ndarray, result: np.ndarray, over25: float,
                   rounds: int = 100) -> np.ndarray:
    """Rescale a scoreline grid to given result and over/under 2.5 probabilities.

    result: [P(home win), P(draw), P(away win)]. The grid's shape (which
    scorelines are likely within a home win, say) is kept; only the totals
    move. The two targets are matched in turn until both hold, which is
    iterative proportional fitting.
    """
    M = np.asarray(grid, dtype=float).copy()
    M /= M.sum()
    home, away = np.indices(M.shape)
    outcomes = [home > away, home == away, home < away]
    over = home + away > 2.5
    for _ in range(rounds):
        for mask, target in zip(outcomes, result, strict=True):
            M[mask] *= target / M[mask].sum()
        M[over] *= over25 / M[over].sum()
        M[~over] *= (1 - over25) / M[~over].sum()
        if max(abs(M[m].sum() - t) for m, t in zip(outcomes, result, strict=True)) < 1e-9:
            break
    return M


def board_probs(grid: np.ndarray, result: np.ndarray, over25: float) -> dict[str, float]:
    """Every probability the site shows for one fixture."""
    M = reconcile_grid(grid, result, over25)
    home, away = np.indices(M.shape)
    p_home, p_draw, p_away = (float(M[home > away].sum()), float(M[home == away].sum()),
                              float(M[home < away].sum()))
    return {
        "home_win_p": p_home, "draw_p": p_draw, "away_win_p": p_away,
        "dc_1x_p": p_home + p_draw, "dc_12_p": p_home + p_away, "dc_x2_p": p_draw + p_away,
        "exp_home_goals": float((M * home).sum()),
        "exp_away_goals": float((M * away).sum()),
        **grid_markets(M),
    }


def fixture_probs(model: Ensemble, home: str, away: str, neutral: bool = True) -> dict | None:
    """All probabilities for one international fixture, or None if Dixon-Coles
    can't price it."""
    if not {home, away} <= model.dixon_coles.teams:
        return None
    pred = model.predict(home, away, neutral=neutral)
    grid = model.dixon_coles.grid(home, away, neutral)
    return board_probs(grid.grid, pred.probs, pred.p_over25)


def _world_cup_probs(fixtures: list[sqlite3.Row]) -> dict[int, dict]:
    model = Ensemble().fit()
    out = {}
    for f in fixtures:
        probs = fixture_probs(model, f["home_team"], f["away_team"], bool(f["neutral"]))
        if probs is None:
            logger.warning("skipping %s vs %s: team not in training data",
                           f["home_team"], f["away_team"])
        else:
            out[f["match_id"]] = probs
    return out


def _premier_league_probs(fixtures: list[sqlite3.Row]) -> dict[int, dict]:
    from zuba.data import load_club_matches
    from zuba.stacks.premier_league import price_fixtures

    known = set(load_club_matches()["home_team"])
    priceable = []
    for f in fixtures:
        if {f["home_team"], f["away_team"]} <= known:
            priceable.append(dict(f))
        else:
            logger.warning("skipping %s vs %s: team not in training data",
                           f["home_team"], f["away_team"])
    if not priceable:
        return {}

    rows, preds, stack = price_fixtures(pd.DataFrame(priceable))
    by_teams = {(f["home_team"], f["away_team"], f["date"]): f["match_id"] for f in priceable}
    out = {}
    for i, row in enumerate(rows.itertuples(index=False)):
        match_id = by_teams[(row.home_team, row.away_team, row.date.date().isoformat())]
        grid = stack.dixon_coles.grid(row.home_team, row.away_team)
        out[match_id] = board_probs(grid.grid, preds.result[i], float(preds.over25[i]))
    return out


def predict_upcoming(competition: str = "epl", conn: sqlite3.Connection | None = None) -> int:
    """Price every unplayed fixture of one competition. Returns how many were saved."""
    conn = conn or get_connection()
    fixtures = conn.execute(
        "SELECT match_id, date, home_team, away_team, neutral FROM matches "
        "WHERE completed = 0 AND competition = ?", (competition,)
    ).fetchall()
    if not fixtures:
        return 0

    price = _premier_league_probs if competition == "epl" else _world_cup_probs
    now = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
    priced = price(fixtures)
    conn.executemany(
        "INSERT OR REPLACE INTO predictions (match_id, generated_at, model_version, probs) "
        "VALUES (?, ?, ?, ?)",
        [(match_id, now, MODEL_VERSION, json.dumps(probs)) for match_id, probs in priced.items()],
    )
    conn.commit()
    return len(priced)
