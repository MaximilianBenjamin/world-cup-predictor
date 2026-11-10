"""Walk-forward backtest of the Premier League stack.

The season is replayed one week at a time. Before each week the models are
fitted on matches played before it and asked for that week's games, so every
prediction is made the way it would have been at the time. Dixon-Coles and GAP
are refitted every week; the boosted models, which change little from one week
to the next, on the first match week of each month.

Blend weights get the same treatment: the blend for a season uses weights
fitted on the predictions for earlier seasons only. Two seasons are replayed
before the first scored one to give those weights something to learn from.

    preds = walk_forward()             # one row per match, every model's numbers
    report = summarise(preds)          # scores, intervals, model against market
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from zuba.data import load_club_matches
from zuba.evaluate import market
from zuba.evaluate.metrics import calibration_table, log_loss_gap, score_with_intervals
from zuba.features import build_club_features
from zuba.stacks.blend import blend, fit_weights
from zuba.stacks.premier_league import GOALS_MODELS, RESULT_MODELS, TRAIN_FROM, PremierLeague

logger = logging.getLogger(__name__)

FIRST_REPLAYED = "2015-16"   # predictions start here, to train the blend weights
FIRST_SCORED = "2017-18"     # scores are reported from here
_OUTCOME = {"H": 0, "D": 1, "A": 2}
_SIDES = ("h", "d", "a")


def result_columns(model: str) -> list[str]:
    return [f"{model}_{s}" for s in _SIDES]


def walk_forward(first: str = FIRST_REPLAYED, last: str | None = None) -> pd.DataFrame:
    """Out-of-sample predictions for every Premier League match from season
    `first` to `last` (default: the latest in the data).

    Columns: date, season, home_team, away_team, result, total_goals, the
    market's odds, <model>_h/_d/_a for each result model and <model>_over for
    each goals model.
    """
    table = build_club_features(load_club_matches())
    table = table[table["date"] >= TRAIN_FROM]
    test = table[(table["league"] == "epl") & (table["season"] >= first)]
    if last:
        test = test[test["season"] <= last]

    stack = PremierLeague()
    out, month = [], None
    weeks = test["date"].dt.to_period("W-THU")   # a match week runs Friday to Thursday
    for week, block in test.groupby(weeks, sort=True):
        start = block["date"].min()
        played = table[table["date"] < start]
        if (start.year, start.month) != month:
            month = (start.year, start.month)
            stack.fit_boosters(played)
            logger.info("%s: boosters refitted on %d matches", week, len(played))
        stack.fit_team_models(played)

        preds = stack.predict(block)
        rows = block[["date", "season", "home_team", "away_team", "result",
                      "odds_h", "odds_d", "odds_a", "odds_over", "odds_under"]].copy()
        rows["total_goals"] = block["home_goals"] + block["away_goals"]
        for name, probs in preds.result_models.items():
            rows[result_columns(name)] = probs
        for name, probs in preds.goals_models.items():
            rows[f"{name}_over"] = probs
        out.append(rows)
    return pd.concat(out, ignore_index=True)


def _result_probs(preds: pd.DataFrame, models=RESULT_MODELS) -> dict[str, np.ndarray]:
    return {m: preds[result_columns(m)].to_numpy(float) for m in models}


def _goals_probs(preds: pd.DataFrame, models=GOALS_MODELS) -> dict[str, np.ndarray]:
    return {m: preds[f"{m}_over"].to_numpy(float) for m in models}


def add_blends(preds: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Add mean_* (plain average) and blend_* (weighted) columns.

    A season's blend uses weights fitted on earlier seasons only; the first
    replayed season has none to learn from and falls back to the plain average.
    Also returns the weights fitted on every season, for use on live fixtures.
    """
    preds = preds.copy()
    y = preds["result"].map(_OUTCOME).to_numpy()
    over = (preds["total_goals"] > 2.5).astype(int).to_numpy()
    preds[result_columns("mean")] = blend(_result_probs(preds))
    preds["mean_over"] = blend(_goals_probs(preds))

    for season in sorted(preds["season"].unique()):
        now = (preds["season"] == season).to_numpy()
        before = (preds["season"] < season).to_numpy()
        w_result = w_goals = None
        if before.any():
            w_result = fit_weights(_result_probs(preds[before]), y[before])
            w_goals = fit_weights(_goals_probs(preds[before]), over[before])
        preds.loc[now, result_columns("blend")] = blend(_result_probs(preds[now]), w_result)
        preds.loc[now, "blend_over"] = blend(_goals_probs(preds[now]), w_goals)

    final = {"result": fit_weights(_result_probs(preds), y),
             "goals": fit_weights(_goals_probs(preds), over)}
    return preds, final


def summarise(preds: pd.DataFrame, first_scored: str = FIRST_SCORED) -> dict:
    """Scores for every model, the two blends and the market, on the seasons
    from `first_scored`. preds: the output of add_blends."""
    scored = preds[preds["season"] >= first_scored].reset_index(drop=True)
    y = scored["result"].map(_OUTCOME).to_numpy()
    over = (scored["total_goals"] > 2.5).astype(int).to_numpy()

    result = {**_result_probs(scored, (*RESULT_MODELS, "mean", "blend")),
              "market": market.result_probs(scored[["odds_h", "odds_d", "odds_a"]].to_numpy()),
              "baseline": np.tile(np.bincount(y, minlength=3) / len(y), (len(y), 1))}
    goals = {**_goals_probs(scored, (*GOALS_MODELS, "mean", "blend")),
             "market": market.over_probs(scored["odds_over"], scored["odds_under"]),
             "baseline": np.full(len(over), over.mean())}
    goals = {name: np.column_stack([1 - p, p]) for name, p in goals.items()}

    report = {
        "seasons": [first_scored, scored["season"].max()],
        "matches": int(len(scored)),
        "result": {m: score_with_intervals(p, y) for m, p in result.items()},
        "goals": {m: score_with_intervals(p, over) for m, p in goals.items()},
        "result_vs_market": {m: log_loss_gap(result[m], result["market"], y)
                             for m in (*RESULT_MODELS, "mean", "blend")},
        "goals_vs_market": {m: log_loss_gap(goals[m], goals["market"], over)
                            for m in (*GOALS_MODELS, "mean", "blend")},
        "calibration": {"blend": calibration_table(result["blend"], y),
                        "market": calibration_table(result["market"], y)},
        "by_season": [],
    }
    for season, part in scored.groupby("season"):
        idx = part.index.to_numpy()
        report["by_season"].append({
            "season": season, "matches": int(len(idx)),
            "blend": float(-np.mean(np.log(result["blend"][idx, y[idx]]))),
            "market": float(-np.mean(np.log(result["market"][idx, y[idx]]))),
        })
    return report
