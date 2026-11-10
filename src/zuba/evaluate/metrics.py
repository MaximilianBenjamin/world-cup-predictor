"""Scores for probability forecasts, with bootstrap confidence intervals.

All take `probs`, an (N, K) array whose rows sum to one, and `outcomes`, the
index of what happened in each row. Lower is better except for accuracy.

    log loss   -log of the probability given to what happened, averaged
    Brier      squared error against the 0/1 outcome, summed over the K classes
    RPS        ranked probability score: like Brier but on cumulative
               probabilities, so for an ordered result (home, draw, away)
               calling a home win when it was a draw costs less than when it
               was an away win
    ECE        expected calibration error: bucket every stated probability into
               tenths and average the gap between the stated and the observed
               frequency, weighted by bucket size
    accuracy   share of matches where the most likely outcome happened
"""

from __future__ import annotations

import numpy as np

_EPS = 1e-12


def _per_match(probs: np.ndarray, outcomes: np.ndarray) -> dict[str, np.ndarray]:
    """Each metric's value for every match (ECE has none; it is a group measure)."""
    n, k = probs.shape
    onehot = np.eye(k)[outcomes]
    cum_gap = np.cumsum(probs, axis=1)[:, :-1] - np.cumsum(onehot, axis=1)[:, :-1]
    return {
        "log_loss": -np.log(np.clip(probs[np.arange(n), outcomes], _EPS, 1.0)),
        "brier": np.sum((probs - onehot) ** 2, axis=1),
        "rps": np.sum(cum_gap ** 2, axis=1) / (k - 1),
        "accuracy": (probs.argmax(axis=1) == outcomes).astype(float),
    }


def calibration_table(probs: np.ndarray, outcomes: np.ndarray, bins: int = 10) -> list[dict]:
    """Stated against observed frequency, pooling every class's probabilities.
    One entry per non-empty bucket: {"stated", "observed", "count"}."""
    stated = probs.ravel()
    happened = np.eye(probs.shape[1])[outcomes].ravel()
    bucket = np.minimum((stated * bins).astype(int), bins - 1)
    table = []
    for b in range(bins):
        mask = bucket == b
        if mask.any():
            table.append({"stated": float(stated[mask].mean()),
                          "observed": float(happened[mask].mean()), "count": int(mask.sum())})
    return table


def ece(probs: np.ndarray, outcomes: np.ndarray, bins: int = 10) -> float:
    table = calibration_table(probs, outcomes, bins)
    total = sum(row["count"] for row in table)
    return float(sum(row["count"] * abs(row["stated"] - row["observed"]) for row in table) / total)


def score(probs: np.ndarray, outcomes: np.ndarray) -> dict[str, float]:
    out = {name: float(v.mean()) for name, v in _per_match(probs, outcomes).items()}
    out["ece"] = ece(probs, outcomes)
    return out


def score_with_intervals(probs: np.ndarray, outcomes: np.ndarray, draws: int = 2000,
                         seed: int = 0) -> dict[str, dict[str, float]]:
    """{"log_loss": {"value", "low", "high"}, ...} with 95% intervals from
    resampling matches with replacement."""
    per_match = _per_match(probs, outcomes)
    n = len(outcomes)
    picks = np.random.default_rng(seed).integers(0, n, size=(draws, n))
    out = {}
    for name, values in per_match.items():
        low, high = np.percentile(values[picks].mean(axis=1), [2.5, 97.5])
        out[name] = {"value": float(values.mean()), "low": float(low), "high": float(high)}
    out["ece"] = {"value": ece(probs, outcomes)}
    return out


def log_loss_gap(probs_a: np.ndarray, probs_b: np.ndarray, outcomes: np.ndarray,
                 draws: int = 2000, seed: int = 0) -> dict[str, float]:
    """Log loss of a minus log loss of b on the same matches, with a 95%
    interval. Resampling the per-match differences keeps the pairing, which is
    much tighter than comparing two separate intervals. An interval that
    excludes zero means the gap is unlikely to be luck."""
    diff = _per_match(probs_a, outcomes)["log_loss"] - _per_match(probs_b, outcomes)["log_loss"]
    n = len(diff)
    picks = np.random.default_rng(seed).integers(0, n, size=(draws, n))
    low, high = np.percentile(diff[picks].mean(axis=1), [2.5, 97.5])
    return {"value": float(diff.mean()), "low": float(low), "high": float(high)}
