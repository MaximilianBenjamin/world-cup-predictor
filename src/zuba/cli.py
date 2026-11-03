"""Command-line entry point.

    uv run zuba pick Brazil Morocco          # one-off prediction
    uv run zuba fetch                        # pull fixtures and scores from ESPN
    uv run zuba predict                      # price every unplayed fixture
    uv run zuba backtest                     # score the models on past World Cups
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
import warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zuba", description="World Cup match predictions")
    sub = parser.add_subparsers(dest="command", required=True)

    pick = sub.add_parser("pick", help="predict one match")
    pick.add_argument("home")
    pick.add_argument("away")
    pick.add_argument("--home-advantage", action="store_true",
                      help="the first team is playing at home (default: neutral venue)")

    fetch = sub.add_parser("fetch", help="update fixtures and scores from ESPN")
    fetch.add_argument("--from", dest="start", type=dt.date.fromisoformat)
    fetch.add_argument("--to", dest="end", type=dt.date.fromisoformat)

    sub.add_parser("predict", help="price every unplayed fixture in the database")

    backtest = sub.add_parser("backtest", help="score the models on past World Cups")
    backtest.add_argument("years", nargs="*", type=int, help="default: 2018 2022 2026")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    warnings.filterwarnings("ignore", category=UserWarning)

    if args.command == "pick":
        from zuba.ensemble import Ensemble

        print(Ensemble().fit().predict(args.home, args.away, neutral=not args.home_advantage))
    elif args.command == "fetch":
        from zuba.espn import save_fixtures

        print(f"{save_fixtures(args.start, args.end)} fixtures saved")
    elif args.command == "predict":
        from zuba.markets import predict_upcoming

        print(f"{predict_upcoming()} matches priced")
    elif args.command == "backtest":
        from zuba.backtest import run

        results, goals = run(args.years or None)
        print("\nMatch result, group stages\n")
        print(results.to_string(index=False, float_format="%.3f"))
        print("\nOver/under 2.5 goals, all group-stage games\n")
        print(goals.to_string(index=False, float_format="%.3f"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
