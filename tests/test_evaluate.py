import numpy as np
import pandas as pd
import pytest

from zuba.evaluate import market
from zuba.evaluate.metrics import (
    calibration_table,
    ece,
    log_loss_gap,
    score,
    score_with_intervals,
)
from zuba.evaluate.walkforward import add_blends, result_columns, summarise
from zuba.stacks.premier_league import GOALS_MODELS, RESULT_MODELS


def test_scores_on_a_hand_worked_example():
    probs = np.array([[0.5, 0.3, 0.2], [0.2, 0.2, 0.6]])
    s = score(probs, np.array([0, 1]))
    assert s["log_loss"] == pytest.approx(-(np.log(0.5) + np.log(0.2)) / 2)
    assert s["brier"] == pytest.approx(((0.25 + 0.09 + 0.04) + (0.04 + 0.64 + 0.36)) / 2)
    # RPS: cumulative [0.5, 0.8] against [1, 1], then [0.2, 0.4] against [0, 1].
    assert s["rps"] == pytest.approx(((0.25 + 0.04) / 2 + (0.04 + 0.36) / 2) / 2)
    assert s["accuracy"] == pytest.approx(0.5)


def test_rps_punishes_a_far_miss_more_than_a_near_one():
    away_win = np.array([2])
    near = score(np.array([[0.0, 1.0, 0.0]]), away_win)["rps"]   # said draw
    far = score(np.array([[1.0, 0.0, 0.0]]), away_win)["rps"]    # said home win
    assert far > near > 0


def test_a_perfectly_calibrated_forecast_has_no_calibration_error():
    rng = np.random.default_rng(1)
    probs = rng.dirichlet([2, 2, 2], size=40000)
    outcomes = np.array([rng.choice(3, p=p) for p in probs])
    assert ece(probs, outcomes) < 0.01
    overconfident = probs ** 3 / (probs ** 3).sum(axis=1, keepdims=True)
    assert ece(overconfident, outcomes) > 0.05
    assert sum(row["count"] for row in calibration_table(probs, outcomes)) == probs.size


def test_intervals_contain_the_value_and_gaps_are_paired():
    rng = np.random.default_rng(2)
    truth = rng.dirichlet([3, 2, 2], size=1500)
    outcomes = np.array([rng.choice(3, p=p) for p in truth])
    s = score_with_intervals(truth, outcomes, draws=300)["log_loss"]
    assert s["low"] < s["value"] < s["high"]

    worse = 0.8 * truth + 0.2 / 3
    gap = log_loss_gap(worse, truth, outcomes, draws=300)
    assert gap["low"] > 0                       # clearly worse, despite overlapping intervals
    assert log_loss_gap(truth, truth, outcomes, draws=50)["value"] == 0


def test_margin_is_removed_from_odds():
    p = market.result_probs(np.array([[2.1, 3.4, 3.6], [np.nan, 3.0, 3.0], [1.2, 6.5, 13.0]]))
    assert p[0].sum() == pytest.approx(1) and p[2].sum() == pytest.approx(1)
    assert np.isnan(p[1]).all()
    # Shin takes more of the margin from the long shot than plain scaling does.
    plain = (1 / 13.0) / (1 / 1.2 + 1 / 6.5 + 1 / 13.0)
    assert p[2, 2] < plain
    assert market.over_probs(np.array([1.9]), np.array([1.9])) == pytest.approx([0.5])


def _fake_predictions(n_per_season: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    frames = []
    for season in ("2015-16", "2016-17", "2017-18"):
        truth = rng.dirichlet([4, 3, 3], size=n_per_season)
        result = np.array(list("HDA"))[[rng.choice(3, p=p) for p in truth]]
        df = pd.DataFrame({"season": season, "result": result,
                           "date": pd.Timestamp(f"{season[:4]}-09-01"),
                           "total_goals": rng.poisson(2.7, n_per_season)})
        for i, m in enumerate(RESULT_MODELS):
            noisy = truth if i == 0 else rng.dirichlet([1, 1, 1], size=n_per_season)
            df[result_columns(m)] = noisy
        for m in GOALS_MODELS:
            df[f"{m}_over"] = rng.uniform(0.4, 0.6, n_per_season)
        margin = 1.05
        df[["odds_h", "odds_d", "odds_a"]] = 1 / (truth * margin)
        df["odds_over"], df["odds_under"] = 1.9, 1.9
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def test_blend_weights_come_from_earlier_seasons_only():
    preds = _fake_predictions()
    blended, weights = add_blends(preds)
    first = blended["season"] == "2015-16"
    # No earlier season to learn from: the blend is the plain average.
    np.testing.assert_allclose(blended.loc[first, result_columns("blend")],
                               blended.loc[first, result_columns("mean")])
    assert weights["result"][RESULT_MODELS[0]] > 0.9

    # Wrecking a later season must not change an earlier season's blend.
    wrecked = preds.copy()
    last = wrecked["season"] == "2017-18"
    wrecked.loc[last, "result"] = "A"
    again, _ = add_blends(wrecked)
    middle = blended["season"] == "2016-17"
    np.testing.assert_allclose(again.loc[middle, result_columns("blend")],
                               blended.loc[middle, result_columns("blend")])


def test_summary_scores_only_the_requested_seasons():
    blended, _ = add_blends(_fake_predictions())
    report = summarise(blended, first_scored="2017-18")
    assert report["matches"] == 300
    assert set(report["result"]) == {*RESULT_MODELS, "mean", "blend", "market", "baseline"}
    assert report["result"]["blend"]["log_loss"]["value"] < report["result"]["mean"]["log_loss"]["value"]
    assert report["result_vs_market"]["blend"]["value"] == pytest.approx(0, abs=0.02)
    assert [row["season"] for row in report["by_season"]] == ["2017-18"]
