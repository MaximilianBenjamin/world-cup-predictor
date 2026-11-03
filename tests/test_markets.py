import numpy as np
import pytest

from zuba.markets import grid_markets


def test_grid_markets_on_a_known_grid():
    # Only three scorelines are possible: 1-0 (50%), 1-1 (30%), 0-2 (20%).
    grid = np.zeros((4, 4))
    grid[1, 0], grid[1, 1], grid[0, 2] = 0.5, 0.3, 0.2
    m = grid_markets(grid)

    assert m["over_0_5_p"] == pytest.approx(1.0)
    assert m["over_1_5_p"] == pytest.approx(0.5)   # 1-1 and 0-2
    assert m["over_2_5_p"] == pytest.approx(0.0)
    assert m["h_u25_p"] == pytest.approx(0.5)      # home win and under 2.5
    assert m["a_o15_p"] == pytest.approx(0.2)      # away win and over 1.5
    assert m["dc1x_o15_p"] == pytest.approx(0.3)   # home or draw, and over 1.5


def test_joint_probabilities_add_up():
    rng = np.random.default_rng(0)
    grid = rng.random((8, 8))
    grid /= grid.sum()
    m = grid_markets(grid)
    for line in ("15", "25", "35"):
        # For a half-goal line, over + under covers every score in the outcome.
        assert m[f"dc1x_o{line}_p"] + m[f"dc1x_u{line}_p"] == pytest.approx(np.tril(grid).sum())
