"""GAP ratings for over/under goals (Wheatcroft 2020).

Wheatcroft, E. (2020). A profitable model for predicting the over/under market
in football. International Journal of Forecasting, 36(3), 916-932.

Each team gets four ratings: attack and defence, at home and away. For a match
between home team i and away team j:

    expected home output = exp(attack_home[i] + defence_away[j] + home_adv + c)
    expected away output = exp(attack_away[j] + defence_home[i] + c)

The ratings are fitted by Poisson maximum likelihood. A logistic regression per
goal line then maps the two expected outputs to P(total goals > line).

The paper's best version measures attacking output with shots and corners.
National teams have no shots or corners data, so goals are used here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

LINES = (0.5, 1.5, 2.5, 3.5, 4.5)


class GAPRatings:
    def __init__(self, lines: tuple[float, ...] = LINES):
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
        """df needs home_team, away_team, home_goals, away_goals."""
        df = df.dropna(subset=["home_goals", "away_goals"])
        teams = sorted(set(df["home_team"]) | set(df["away_team"]))
        self._team_index = {t: i for i, t in enumerate(teams)}
        n = len(teams)

        hi = df["home_team"].map(self._team_index).to_numpy()
        ai = df["away_team"].map(self._team_index).to_numpy()
        hg = df["home_goals"].to_numpy(float)
        ag = df["away_goals"].to_numpy(float)

        # Parameters: attack_home, defence_home, attack_away, defence_away (n each),
        # then home advantage and an intercept.
        def neg_log_likelihood(p: np.ndarray) -> float:
            ah, dh, aa, da = (p[k * n:(k + 1) * n] for k in range(4))
            mu_h = np.exp(ah[hi] + da[ai] + p[4 * n] + p[4 * n + 1])
            mu_a = np.exp(aa[ai] + dh[hi] + p[4 * n + 1])
            return -np.sum(hg * np.log(mu_h + 1e-10) - mu_h + ag * np.log(mu_a + 1e-10) - mu_a)

        x0 = np.zeros(4 * n + 2)
        x0[4 * n] = 0.1  # small home advantage to start from
        self._params = minimize(
            neg_log_likelihood, x0, method="L-BFGS-B", options={"maxiter": 500, "ftol": 1e-9}
        ).x

        X = self._scaler.fit_transform(self._expected(hi, ai))
        total = hg + ag
        for line in self.lines:
            y = (total > line).astype(int)
            if min(y.sum(), len(y) - y.sum()) >= 10:  # need both classes
                self._ou_models[line] = LogisticRegression(max_iter=200).fit(X, y)
        return self

    def predict(self, home_team: str, away_team: str) -> dict[str, float]:
        """{"over_2_5": p, "under_2_5": 1 - p, ...} for each fitted line."""
        if self._params is None:
            raise RuntimeError("Call fit() before predict().")
        hi = np.array([self._team_index.get(home_team, -1)])
        ai = np.array([self._team_index.get(away_team, -1)])
        X = self._scaler.transform(self._expected(hi, ai))
        out = {}
        for line, model in self._ou_models.items():
            label = str(line).replace(".", "_")
            out[f"over_{label}"] = float(model.predict_proba(X)[0, 1])
            out[f"under_{label}"] = 1.0 - out[f"over_{label}"]
        return out
