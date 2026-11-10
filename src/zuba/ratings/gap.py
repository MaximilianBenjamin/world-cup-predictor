"""GAP ratings for over/under goals (Wheatcroft 2020).

Wheatcroft, E. (2020). A profitable model for predicting the over/under market
in football. International Journal of Forecasting, 36(3), 916-932.

Each team gets four ratings: attack and defence, at home and away. For a match
between home team i and away team j:

    expected home output = exp(attack_home[i] + defence_away[j] + home_adv + c)
    expected away output = exp(attack_away[j] + defence_home[i] + c)

The ratings are fitted by Poisson maximum likelihood. A logistic regression per
goal line then maps the two expected outputs to P(total goals > line).

"Output" is whatever measure of attacking play is chosen. The paper found
goals to be the worst choice and shots and corners the best, because they
happen often enough to pin a team down quickly. Club data has all four
(`measure="shots"`, "sot" for shots on target, "corners", or "goals").
National teams have no shots or corners data, so they use goals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

LINES = (0.5, 1.5, 2.5, 3.5, 4.5)
MEASURES = ("goals", "shots", "sot", "corners")


class GAPRatings:
    def __init__(self, measure: str = "goals", lines: tuple[float, ...] = LINES):
        if measure not in MEASURES:
            raise ValueError(f"measure must be one of {MEASURES}")
        self.measure = measure
        self.lines = lines
        self._team_index: dict[str, int] = {}
        self._params: np.ndarray | None = None
        self._scaler = StandardScaler()
        self._ou_models: dict[float, LogisticRegression] = {}

    def _expected(self, home_idx: np.ndarray, away_idx: np.ndarray) -> np.ndarray:
        """(N, 2) expected home and away goals. Index -1 means an unseen team,
        which gets neutral (zero) ratings."""
        n = len(self._team_index)
        p = self._params
        ah, dh, aa, da = (np.append(p[k * n:(k + 1) * n], 0.0) for k in range(4))
        home_adv, intercept = p[4 * n], p[4 * n + 1]
        mu_h = np.exp(ah[home_idx] + da[away_idx] + home_adv + intercept)
        mu_a = np.exp(aa[away_idx] + dh[home_idx] + intercept)
        return np.column_stack([mu_h, mu_a])

    def fit(self, df: pd.DataFrame) -> GAPRatings:
        """df needs home_team, away_team, home_goals, away_goals, and for any
        measure other than goals, home_<measure> and away_<measure>."""
        cols = ["home_goals", "away_goals", f"home_{self.measure}", f"away_{self.measure}"]
        df = df.dropna(subset=cols)
        teams = sorted(set(df["home_team"]) | set(df["away_team"]))
        self._team_index = {t: i for i, t in enumerate(teams)}
        n = len(teams)

        hi = df["home_team"].map(self._team_index).to_numpy()
        ai = df["away_team"].map(self._team_index).to_numpy()
        out_h = df[f"home_{self.measure}"].to_numpy(float)
        out_a = df[f"away_{self.measure}"].to_numpy(float)

        # Parameters: attack_home, defence_home, attack_away, defence_away (n each),
        # then home advantage and an intercept. Returns the negative log
        # likelihood and its gradient; a small ridge keeps the ratings identified.
        ridge = 1e-3

        def objective(p: np.ndarray) -> tuple[float, np.ndarray]:
            ah, dh, aa, da = (p[k * n:(k + 1) * n] for k in range(4))
            mu_h = np.exp(ah[hi] + da[ai] + p[4 * n] + p[4 * n + 1])
            mu_a = np.exp(aa[ai] + dh[hi] + p[4 * n + 1])
            loss = np.sum(mu_h - out_h * np.log(mu_h) + mu_a - out_a * np.log(mu_a))
            err_h, err_a = mu_h - out_h, mu_a - out_a
            grad = np.concatenate([
                np.bincount(hi, err_h, n), np.bincount(hi, err_a, n),
                np.bincount(ai, err_a, n), np.bincount(ai, err_h, n),
                [err_h.sum(), err_h.sum() + err_a.sum()],
            ])
            return loss + ridge * np.sum(p[:4 * n] ** 2), grad + 2 * ridge * np.r_[p[:4 * n], 0, 0]

        x0 = np.zeros(4 * n + 2)
        x0[4 * n] = 0.1  # small home advantage to start from
        x0[4 * n + 1] = np.log(max(out_a.mean(), 1e-3))
        self._params = minimize(
            objective, x0, jac=True, method="L-BFGS-B", options={"maxiter": 500}
        ).x

        X = self._scaler.fit_transform(np.log(self._expected(hi, ai)))
        total = df["home_goals"].to_numpy(float) + df["away_goals"].to_numpy(float)
        for line in self.lines:
            y = (total > line).astype(int)
            if min(y.sum(), len(y) - y.sum()) >= 10:  # need both classes
                self._ou_models[line] = LogisticRegression(max_iter=200).fit(X, y)
        return self

    @property
    def teams(self) -> set[str]:
        """Teams seen in training."""
        return set(self._team_index)

    def predict(self, home_team: str, away_team: str) -> dict[str, float]:
        """{"over_2_5": p, "under_2_5": 1 - p, ...} for each fitted line."""
        if self._params is None:
            raise RuntimeError("Call fit() before predict().")
        hi = np.array([self._team_index.get(home_team, -1)])
        ai = np.array([self._team_index.get(away_team, -1)])
        X = self._scaler.transform(np.log(self._expected(hi, ai)))
        out = {}
        for line, model in self._ou_models.items():
            label = str(line).replace(".", "_")
            out[f"over_{label}"] = float(model.predict_proba(X)[0, 1])
            out[f"under_{label}"] = 1.0 - out[f"over_{label}"]
        return out
