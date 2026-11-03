"""Score the models on past World Cups they never saw.

For each tournament, every model is trained only on matches played before the
opening game, then asked to predict the group stage. Knockout games are left
out because recorded scores include extra time, which a 90-minute result model
isn't trying to predict.

Metrics (lower is better for the first two):
    log loss   -mean log P(actual result)
    Brier      mean squared error over the three outcomes (0 = perfect, 2 = worst)
    accuracy   share of games where the most likely result happened
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from zuba.data import load_international_results
from zuba.ensemble import Ensemble

# Opening day and last group-stage day of each tournament.
WORLD_CUPS = {
    2018: ("2018-06-14", "2018-06-28"),
    2022: ("2022-11-20", "2022-12-02"),
    2026: ("2026-06-11", "2026-06-27"),
}
_OUTCOME = {"H": 0, "D": 1, "A": 2}


def _scores(probs: np.ndarray, outcomes: np.ndarray) -> dict[str, float]:
    probs = np.clip(probs, 1e-12, 1.0)
    onehot = np.eye(probs.shape[1])[outcomes]
    return {
        "log_loss": float(-np.mean(np.log(probs[np.arange(len(outcomes)), outcomes]))),
        "brier": float(np.mean(np.sum((probs - onehot) ** 2, axis=1))),
        "accuracy": float(np.mean(probs.argmax(axis=1) == outcomes)),
    }


def predict_tournament(year: int) -> pd.DataFrame:
    """One row per group-stage match with each model's probabilities."""
    start, end = WORLD_CUPS[year]
    games = load_international_results(min_date=start, max_date=end + " 23:59")
    games = games[games["tournament"] == "FIFA World Cup"]
    model = Ensemble().fit(max_date=start)

    rows = []
    for g in games.itertuples(index=False):
        pred = model.predict(g.home_team, g.away_team, neutral=g.neutral)
        row = {"year": year, "home_team": g.home_team, "away_team": g.away_team,
               "result": g.result, "goals": g.home_goals + g.away_goals,
               "ensemble": pred.probs, "ensemble_over25": pred.p_over25}
        row.update(pred.result_models)
        row.update({f"{k}_over25": v for k, v in pred.goals_models.items()})
        rows.append(row)
    return pd.DataFrame(rows)


def summarise(preds: pd.DataFrame) -> pd.DataFrame:
    """Result-model scores per tournament and overall, against a 1/3-each baseline."""
    models = ["ensemble", "dixon_coles", "catboost_pi", "elo_lgbm", "zeileis_groll"]
    out = []
    for label, part in [*preds.groupby("year"), ("all", preds)]:
        outcomes = part["result"].map(_OUTCOME).to_numpy()
        out.append({"tournament": label, "model": "baseline (1/3 each)", "games": len(part),
                     **_scores(np.full((len(part), 3), 1 / 3), outcomes)})
        for m in models:
            ok = part[m].notna()
            probs = np.vstack(part.loc[ok, m].to_numpy())
            out.append({"tournament": label, "model": m, "games": int(ok.sum()),
                        **_scores(probs, outcomes[ok.to_numpy()])})
    return pd.DataFrame(out)


def summarise_goals(preds: pd.DataFrame) -> pd.DataFrame:
    """Over/under 2.5 goals scores across all tournaments."""
    over = (preds["goals"] > 2.5).astype(int).to_numpy()
    out = [{"model": "baseline (50/50)", **_scores(np.full((len(over), 2), 0.5), over)}]
    for m in ["ensemble", "dixon_coles", "gap"]:
        p = preds[f"{m}_over25"].to_numpy(float)
        out.append({"model": m, **_scores(np.column_stack([1 - p, p]), over)})
    return pd.DataFrame(out)


def run(years: list[int] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    preds = pd.concat([predict_tournament(y) for y in (years or list(WORLD_CUPS))],
                      ignore_index=True)
    return summarise(preds), summarise_goals(preds)
