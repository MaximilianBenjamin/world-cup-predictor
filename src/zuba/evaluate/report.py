"""Run the Premier League backtest and write its results.

Three files come out of a run:

    data/backtest_epl_predictions.csv   every out-of-sample prediction
    data/blend_epl.json                 blend weights for live fixtures
    docs/backtest_epl.json              the scores, for the site and the README
"""

from __future__ import annotations

import json
from pathlib import Path

from zuba.evaluate.walkforward import add_blends, summarise, walk_forward
from zuba.stacks.premier_league import WEIGHTS_JSON

_ROOT = Path(__file__).resolve().parents[3]
PREDICTIONS_CSV = _ROOT / "data" / "backtest_epl_predictions.csv"
REPORT_JSON = _ROOT / "docs" / "backtest_epl.json"

_NAMES = {
    "blend": "Weighted blend", "mean": "Plain average", "market": "Bookmakers (closing)",
    "baseline": "Baseline (long-run frequencies)", "dixon_coles": "Dixon-Coles",
    "catboost_pi": "CatBoost on pi-ratings", "elo_lgbm": "LightGBM on Elo and form",
    "form_xgb": "XGBoost on form and shots", "gap_shots": "GAP on shots",
    "gap_sot": "GAP on shots on target", "gap_corners": "GAP on corners",
    "goals_xgb": "Poisson XGBoost",
}


def run_premier_league() -> dict:
    preds, weights = add_blends(walk_forward())
    report = summarise(preds)
    report["weights"] = weights

    preds.round(4).to_csv(PREDICTIONS_CSV, index=False)
    WEIGHTS_JSON.write_text(json.dumps(weights, indent=2) + "\n")
    REPORT_JSON.write_text(json.dumps(report, indent=2) + "\n")
    return report


def _table(scores: dict, gaps: dict) -> str:
    lines = [f"{'':34s} {'log loss':>20s} {'RPS':>7s} {'Brier':>7s} {'ECE':>6s} {'right':>6s}"
             f"   {'log loss minus market':>24s}"]
    for name in sorted(scores, key=lambda m: scores[m]["log_loss"]["value"]):
        s = scores[name]
        ll = s["log_loss"]
        row = (f"{_NAMES[name]:34s} {ll['value']:.4f} ({ll['low']:.3f}-{ll['high']:.3f}) "
               f"{s['rps']['value']:7.4f} {s['brier']['value']:7.4f} {s['ece']['value']:6.3f} "
               f"{s['accuracy']['value']:6.1%}")
        if name in gaps:
            g = gaps[name]
            row += f"   {g['value']:+.4f} ({g['low']:+.4f} to {g['high']:+.4f})"
        lines.append(row)
    return "\n".join(lines)


def print_report(report: dict) -> None:
    first, last = report["seasons"]
    print(f"\nPremier League {first} to {last}, {report['matches']} matches, "
          "each predicted from earlier matches only\n")
    print("Match result\n")
    print(_table(report["result"], report["result_vs_market"]))
    print("\nOver/under 2.5 goals\n")
    print(_table(report["goals"], report["goals_vs_market"]))
    print("\nBlend weights for live fixtures")
    for kind, weights in report["weights"].items():
        print(f"  {kind}: " + ", ".join(f"{_NAMES[m]} {w:.0%}" for m, w in weights.items() if w))
    print("\nResult log loss by season (blend / market)")
    for row in report["by_season"]:
        print(f"  {row['season']}  {row['blend']:.4f} / {row['market']:.4f}   {row['matches']} matches")
