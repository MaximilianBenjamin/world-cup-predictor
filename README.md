# zuba: World Cup 2026 match predictor

Zuba predicts international football matches. It trains five models on every international result since 2006, averages their probabilities, and shows them on a small web app as fair odds for the match result, goals and same-match combinations. It ran live through the 2026 World Cup, updating fixtures from ESPN each morning.

![Upcoming games page](docs/slate.png)

## Premier League backtest

Version 2.0 adds a Premier League stack. It was tested on 3,520 matches from 2017-18 to 2026-27. Every match was predicted from earlier matches only, with the team models refitted each week, and scored against bookmakers' closing odds with the margin removed.

**Match result**

| Model | Log loss (95% interval) | Gap to bookmakers |
|---|---|---|
| Bookmakers' closing odds | **0.955** (0.938 to 0.971) | |
| Weighted blend | 0.972 (0.956 to 0.987) | +0.017 (+0.012 to +0.022) |
| Dixon-Coles | 0.973 | +0.019 |
| Plain average | 0.974 | +0.019 |
| XGBoost on form and shots | 0.977 | +0.022 |
| CatBoost on pi-ratings | 0.980 | +0.025 |
| LightGBM on Elo and form | 0.981 | +0.026 |
| Baseline: long-run frequencies | 1.067 | |

The blend beats each of its models and the plain average, and its probabilities are well calibrated (calibration error 0.005). It does not beat the bookmakers: the gap is 0.017 and its interval is entirely above zero. The blend scored better than the closing odds in one season of ten (2019-20).

For over/under 2.5 goals the blend scores 0.679, against 0.675 for the bookmakers and 0.690 for the baseline.

The blend weights are fitted on predictions from earlier seasons only. For live fixtures the result is 67% Dixon-Coles and 33% XGBoost; goals are 43% Dixon-Coles, 38% Poisson XGBoost and 19% GAP ratings on shots on target. CatBoost, LightGBM, and GAP on shots and on corners get no weight.

Run it with `uv run zuba backtest --competition epl` (about 90 minutes). Full results are in `docs/backtest_epl.json`.

## World Cup backtest

Each World Cup below was predicted using only matches played before that tournament's opening game. Only group-stage games are scored, because recorded knockout scores include extra time.

**Match result (168 group-stage games)**

| Model | Log loss | Brier | Right result |
|---|---|---|---|
| Ensemble (average) | 0.960 | 0.567 | 58% |
| Dixon-Coles | **0.929** | **0.547** | 60% |
| CatBoost on pi-ratings | 0.975 | 0.580 | 58% |
| LightGBM on Elo and form | 0.979 | 0.579 | 57% |
| Zeileis/Groll ensemble | 0.995 | 0.582 | 55% |
| Baseline: 1/3 on each result | 1.099 | 0.667 | 40% |

Lower is better for log loss and Brier score. The baseline's "right result" is the share of home wins, because it ties every game and falls back to the first option.

By tournament, the ensemble's log loss was 0.942 in 2018, 1.100 in 2022 and 0.877 in 2026. Qatar 2022 was no better than guessing: Saudi Arabia beat Argentina, Japan beat Germany and Spain, and Morocco topped its group. Every model missed those.

The ensemble doesn't beat its best member. Dixon-Coles alone scores better in all three tournaments. With only 168 games there is too little to fit blend weights on without overfitting them, so the World Cup ensemble stays a plain average.

Over/under 2.5 goals is barely better than a coin flip (log loss 0.690 against 0.693 for 50/50). The dataset has no shots or expected-goals data for national teams, and goals alone are too noisy to predict totals.

These numbers are from version 2.0. Version 1.0 scored 0.973 for the ensemble and 0.955 for Dixon-Coles on the same games. The gain came from four fixes: neutral venues are now flagged in every model (before, the first-listed team was priced as if at home), the boosted models stop adding trees when a held-out slice stops improving, the Zeileis/Groll calibration is learned on matches its classifiers hadn't seen, and the tournament-importance flag at prediction time matches the one used in training.

168 games is a small sample, so gaps of 0.01 in log loss between models are within noise.

Run it yourself with `uv run zuba backtest --competition wc` (about 2 minutes).

## How it works

```
data/international_results.csv   (49,000 matches since 1872)
        │
        ├─ Elo ratings, rolled forward match by match (eloratings.net formula)
        ├─ pi-ratings (Constantinou & Fenton 2013)
        │
        ├─ Dixon-Coles ............ scoreline grid → result, goals, combinations
        ├─ CatBoost ............... pi-ratings → result
        ├─ LightGBM ............... Elo + last 3/5 games' form → result
        ├─ Zeileis/Groll .......... Elo, venue, tournament, confederation → result
        │                           (L1 logistic + random forest + XGBoost, isotonic-calibrated)
        └─ GAP (Wheatcroft 2020) .. attack/defence ratings → over/under
                │
                ▼
        average → SQLite → FastAPI → React site
```

Every feature for a match comes from games played before it. Elo and pi-ratings are recorded before each result is applied, form skips the current game, and the backtest cuts the data off at each tournament's opening day.

Combined picks are read off the Dixon-Coles scoreline grid. "Spain to win and over 2.5 goals" is the sum of every scoreline where both happen. Multiplying the two separate probabilities would be wrong, because a team that wins tends to score more.

Fair odds are 1 / probability. The site shows no bookmaker prices.

## Bugs found along the way

penaltyblog's `totals(line)` returns `(under, push, over)`. An earlier version read it the other way round, so every over/under probability was inverted, and an early backtest that looked profitable was really measuring the opposite bet.

`update_ratings` in penaltyblog takes the goal difference as its third argument. The old code passed home goals there and put away goals in the date argument, so the pi-ratings learned from the wrong number. Fixing it changed CatBoost's predictions but not its overall score (log loss 0.989 before, 1.000 after, within noise).

## Running it

Needs Python 3.12+ with [uv](https://docs.astral.sh/uv/), and Node 20+ for the site.

```bash
uv sync
uv run zuba pick Brazil Morocco          # one-off prediction (fits every model, about a minute)
uv run zuba backtest                     # the scores above
uv run pytest                            # fast tests, no model training
```

To run the site:

```bash
uv run zuba fetch                        # fixtures from ESPN (last 3 days to next 25)
uv run zuba predict                      # price every unplayed fixture
cd frontend && npm ci && npm run build && cd ..
uv run uvicorn zuba.api.app:app --port 8001
```

Then open http://localhost:8001. The 2026 tournament is over, so `fetch` only finds games once new ones are scheduled. Set `ZUBA_REFRESH_AT=09:00` to refresh fixtures and predictions daily, and `ZUBA_LINEUPS=1` to pull starting XIs from ESPN about 50 minutes before kickoff.

## Layout

```
src/zuba/
  data.py            load the results file
  ratings/           Elo, pi-ratings, GAP, confederations
  models/            Dixon-Coles, CatBoost, LightGBM, Zeileis/Groll
  stacks/            one model stack per competition: fit everything, blend the predictions
  markets.py         turn predictions into every market and save them
  espn.py            fixtures, scores and lineups
  backtest.py        score the models on past World Cups
  cli.py             the `zuba` command
  api/               FastAPI app, fair-odds board, bet-builder
frontend/            React + Vite + Tailwind
tests/
```

## How I built it

I wrote this with Claude Code. I chose the models from the papers they come from, decided how to test them (one tournament at a time, nothing from after the opening game), checked the output against real results, and tracked down the bugs above. Claude wrote most of the code to my spec, and I reviewed it.

It started as a joint project with my brother, who built the original data scrapers and database. This repository is my rewrite of the modelling and the site, with his parts replaced by a public results dataset and ESPN's API.

## Data

- International results: [martj42/international_results](https://github.com/martj42/international_results) (CC0).
- Fixtures, scores and lineups: ESPN's public scoreboard API.
