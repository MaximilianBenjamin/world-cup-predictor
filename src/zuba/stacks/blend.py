"""Combine several models' probabilities into one.

`fit_weights` finds the non-negative weights, summing to one, that minimise log
loss on predictions the models made for matches they had not seen. `blend`
applies them. A model with nothing to say about a match (NaN) is left out of
that match and the remaining weights are rescaled.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

_EPS = 1e-12


def _stack(probs: dict[str, np.ndarray]) -> np.ndarray:
    """(models, N, K) array. A 1-D input is P(yes) and becomes [P(no), P(yes)]."""
    arrays = []
    for p in probs.values():
        p = np.asarray(p, dtype=float)
        arrays.append(np.column_stack([1 - p, p]) if p.ndim == 1 else p)
    return np.stack(arrays)


def blend(probs: dict[str, np.ndarray], weights: dict[str, float] | None = None) -> np.ndarray:
    """Weighted average across models, row by row. weights=None means equal.

    Returns (N, K), or (N,) of P(yes) if the inputs were 1-D. A row no model
    covers is NaN.
    """
    one_dim = np.asarray(next(iter(probs.values()))).ndim == 1
    P = _stack(probs)
    w = np.array([1.0 if weights is None else weights.get(name, 0.0) for name in probs])
    present = ~np.isnan(P).any(axis=2)                      # (models, N)
    w_row = w[:, None] * present
    total = w_row.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        mixed = (np.nan_to_num(P) * w_row[:, :, None]).sum(axis=0) / total[:, None]
        mixed = mixed / mixed.sum(axis=1, keepdims=True)
    mixed[total == 0] = np.nan
    return mixed[:, 1] if one_dim else mixed


def fit_weights(probs: dict[str, np.ndarray], outcomes: np.ndarray) -> dict[str, float]:
    """Weights that minimise log loss. outcomes: the index of what happened
    (0/1/2 for a result, 0/1 for under/over). Rows any model is missing are ignored."""
    P = _stack(probs)
    ok = ~np.isnan(P).any(axis=(0, 2))
    P, y = P[:, ok], np.asarray(outcomes)[ok]
    hit = P[:, np.arange(len(y)), y]                        # (models, N): P(actual outcome)

    def loss(w: np.ndarray) -> float:
        return float(-np.mean(np.log(np.clip(w @ hit, _EPS, None))))

    m = len(probs)
    best = minimize(loss, np.full(m, 1 / m), method="SLSQP", bounds=[(0.0, 1.0)] * m,
                    constraints={"type": "eq", "fun": lambda w: w.sum() - 1.0})
    w = np.clip(best.x, 0.0, None)
    w = np.where(w < 1e-4, 0.0, w)
    return dict(zip(probs, (w / w.sum()).round(4).tolist(), strict=True))
