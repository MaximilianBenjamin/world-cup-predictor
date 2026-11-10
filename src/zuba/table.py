"""The Premier League table now, and where the model expects it to finish.

The current table is counted from this season's results. The predicted table
comes from playing out the rest of the season many times. Every fixture still
to be played (each pair of clubs meets home and away, so the remaining ones
are the pairs with no result yet) is priced by the same blended model the site
uses, and each simulated season draws a scoreline for every one of them from
that match's scoreline grid. Points, goal difference and goals scored then
order the table as the league does.

Two simplifications. Every remaining match is priced as if it were both clubs'
next game, from today's form and ratings; a club's rating does not move inside
a simulated season. And matches are drawn independently. Both make the
predicted table a little more certain than it should be.

`write()` saves both tables to data/live/table.json, which the API serves. It
is run by the daily refresh, so the tables change after every round of results.
"""

from __future__ import annotations

import datetime as dt
import itertools
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from zuba.data import load_club_matches
from zuba.data.fetch import current_season

logger = logging.getLogger(__name__)

TABLE_JSON = Path(__file__).resolve().parents[2] / "data" / "live" / "table.json"
SIMULATIONS = 20_000
_COUNTS = ("played", "won", "drawn", "lost", "goals_for", "goals_against")


def standings(played: pd.DataFrame, teams: list[str] | None = None) -> list[dict]:
    """The league table from finished matches, best first.

    played: home_team, away_team, home_goals, away_goals. Ordered by points,
    then goal difference, then goals scored, then name.
    """
    names = sorted(teams or set(played["home_team"]) | set(played["away_team"]))
    rows = {t: dict.fromkeys(_COUNTS, 0) for t in names}
    for m in played.itertuples(index=False):
        hg, ag = int(m.home_goals), int(m.away_goals)
        for team, scored, conceded in ((m.home_team, hg, ag), (m.away_team, ag, hg)):
            r = rows[team]
            r["played"] += 1
            r["goals_for"] += scored
            r["goals_against"] += conceded
            r["won" if scored > conceded else "drawn" if scored == conceded else "lost"] += 1
    table = [
        {"team": t, **r, "goal_difference": r["goals_for"] - r["goals_against"],
         "points": 3 * r["won"] + r["drawn"]}
        for t, r in rows.items()
    ]
    table.sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["team"]))
    for i, r in enumerate(table, start=1):
        r["position"] = i
    return table


def remaining_fixtures(played: pd.DataFrame, teams: list[str]) -> list[tuple[str, str]]:
    """Every (home, away) pair that has not been played yet this season."""
    done = set(zip(played["home_team"], played["away_team"], strict=True))
    return [pair for pair in itertools.permutations(sorted(teams), 2) if pair not in done]


def _rounds(fixtures: list[tuple[str, str]]) -> list[list[tuple[str, str]]]:
    """Split fixtures into groups in which no club appears twice.

    The feature table works out a club's form from the rows before each match,
    so a club with several unplayed rows would have later ones built on the
    earlier blanks. One row per club per group avoids that.
    """
    rounds: list[tuple[set[str], list[tuple[str, str]]]] = []
    for home, away in fixtures:
        for busy, group in rounds:
            if home not in busy and away not in busy:
                busy.update((home, away))
                group.append((home, away))
                break
        else:
            rounds.append(({home, away}, [(home, away)]))
    return [group for _, group in rounds]


def price_remaining(fixtures: list[tuple[str, str]],
                    today: dt.date) -> dict[tuple[str, str], np.ndarray]:
    """A scoreline grid (rows: home goals, columns: away goals) for each fixture."""
    from zuba.features import build_club_features
    from zuba.markets import reconcile_grid
    from zuba.stacks.premier_league import TRAIN_FROM, PremierLeague, load_weights

    played = load_club_matches()
    features = build_club_features(played)
    stack = PremierLeague(*load_weights()).fit(features[features["date"] >= TRAIN_FROM])

    grids = {}
    for group in _rounds(fixtures):
        todo = pd.DataFrame(group, columns=["home_team", "away_team"])
        todo["date"] = pd.Timestamp(today)
        todo["league"] = "epl"
        todo["season"] = current_season(today)
        table = build_club_features(pd.concat([played, todo], ignore_index=True))
        rows = table[table["home_goals"].isna()].reset_index(drop=True)
        preds = stack.predict(rows)
        for i, row in enumerate(rows.itertuples(index=False)):
            grid = stack.dixon_coles.grid(row.home_team, row.away_team).grid
            grids[(row.home_team, row.away_team)] = reconcile_grid(
                grid, preds.result[i], float(preds.over25[i]))
    return grids


def simulate(current: list[dict], grids: dict[tuple[str, str], np.ndarray],
             simulations: int = SIMULATIONS, seed: int = 0) -> list[dict]:
    """Play the remaining fixtures `simulations` times; summarise where each club ends up.

    current: rows from `standings`. Returns one row per club, ordered by
    expected points, with average final points and goals, the chance of
    finishing first, in the top four and in the bottom three, and the range of
    positions covering the middle 90% of simulations.
    """
    teams = [r["team"] for r in current]
    index = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    points = np.tile(np.array([r["points"] for r in current], dtype=np.int64), (simulations, 1))
    scored = np.tile(np.array([r["goals_for"] for r in current], dtype=np.int64), (simulations, 1))
    conceded = np.tile(np.array([r["goals_against"] for r in current], dtype=np.int64),
                       (simulations, 1))

    rng = np.random.default_rng(seed)
    for (home, away), grid in grids.items():
        p = np.asarray(grid, dtype=float).ravel()
        cells = rng.choice(p.size, size=simulations, p=p / p.sum())
        hg, ag = np.divmod(cells, grid.shape[1])
        h, a = index[home], index[away]
        scored[:, h] += hg
        conceded[:, h] += ag
        scored[:, a] += ag
        conceded[:, a] += hg
        points[:, h] += np.where(hg > ag, 3, np.where(hg == ag, 1, 0))
        points[:, a] += np.where(ag > hg, 3, np.where(hg == ag, 1, 0))

    # Order each simulated table by points, goal difference, goals scored; a
    # random draw settles anything still level.
    difference = scored - conceded
    key = (points * 1_000_000 + (difference + 500) * 1_000 + scored
           + rng.random((simulations, n)))
    position = np.empty((simulations, n), dtype=np.int64)
    order = np.argsort(-key, axis=1)
    np.put_along_axis(position, order, np.arange(1, n + 1)[None, :], axis=1)

    remaining = dict.fromkeys(teams, 0)
    for home, away in grids:
        remaining[home] += 1
        remaining[away] += 1

    rows = []
    for t, i in index.items():
        low, high = np.percentile(position[:, i], [5, 95])
        rows.append({
            "team": t,
            "current_position": current[i]["position"],
            "played": current[i]["played"] + remaining[t],
            "points": round(float(points[:, i].mean()), 1),
            "goals_for": round(float(scored[:, i].mean()), 1),
            "goals_against": round(float(conceded[:, i].mean()), 1),
            "goal_difference": round(float(difference[:, i].mean()), 1),
            "average_position": round(float(position[:, i].mean()), 2),
            "position_low": int(low),
            "position_high": int(high),
            "p_title": round(float((position[:, i] == 1).mean()), 4),
            "p_top4": round(float((position[:, i] <= 4).mean()), 4),
            "p_relegation": round(float((position[:, i] > n - 3).mean()), 4),
        })
    rows.sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["team"]))
    for i, r in enumerate(rows, start=1):
        r["position"] = i
    return rows


def build(today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    season = current_season(today)
    played = load_club_matches(leagues=("epl",))
    played = played[played["season"] == season]
    if played.empty:
        raise ValueError(f"no Premier League results for {season} yet")
    teams = sorted(set(played["home_team"]) | set(played["away_team"]))
    if len(teams) != 20:
        # Early in a season some clubs have not played; the table would be wrong.
        raise ValueError(f"expected 20 clubs in {season}, found {len(teams)}")

    current = standings(played, teams)
    fixtures = remaining_fixtures(played, teams)
    logger.info("%d matches played, %d to simulate", len(played), len(fixtures))
    grids = price_remaining(fixtures, today) if fixtures else {}
    return {
        "season": season,
        "results_to": played["date"].max().date().isoformat(),
        "matches_played": len(played),
        "matches_remaining": len(fixtures),
        "simulations": SIMULATIONS,
        "current": current,
        "predicted": simulate(current, grids),
    }


def write(path: Path = TABLE_JSON, today: dt.date | None = None) -> dict:
    table = build(today)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(table, indent=1) + "\n")
    return table


def read(path: Path = TABLE_JSON) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None
