"""Bookmaker odds as a yardstick.

Closing odds are the best public forecast of a football match there is, so the
honest test of a model is how close it gets to them. Decimal odds turn into
probabilities as 1/odds, but those add up to more than one: the excess is the
bookmaker's margin, and it has to be taken out first.

For the three-way result this uses Shin's method, which assumes the margin
protects the bookmaker against bettors with inside knowledge and so removes
more of it from long shots than from favourites. That matches how real odds
behave better than scaling every outcome down equally. For two-way over/under
the two methods give nearly the same answer and plain scaling is used.
"""

from __future__ import annotations

import numpy as np
from penaltyblog.implied import calculate_implied


def result_probs(odds: np.ndarray) -> np.ndarray:
    """(N, 3) decimal odds [home, draw, away] -> (N, 3) probabilities. Rows with
    a missing price are NaN."""
    odds = np.asarray(odds, dtype=float)
    out = np.full(odds.shape, np.nan)
    for i, row in enumerate(odds):
        if np.all(np.isfinite(row)) and np.all(row > 1.0):
            out[i] = calculate_implied(row.tolist(), method="shin").probabilities
    return out


def over_probs(odds_over: np.ndarray, odds_under: np.ndarray) -> np.ndarray:
    """(N,) P(over), from decimal odds for over and under."""
    over, under = 1 / np.asarray(odds_over, float), 1 / np.asarray(odds_under, float)
    return over / (over + under)
