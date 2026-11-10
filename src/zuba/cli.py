"""Command-line entry point.

    uv run zuba fetch                        # new results, fixtures and scores
    uv run zuba predict                      # price every unplayed fixture
    uv run zuba pick Arsenal Chelsea         # one-off prediction
    uv run zuba backtest                     # score the models on past seasons

Every command takes --competition epl (Premier League, the default) or wc
(World Cup): `uv run zuba pick Brazil Morocco --competition wc`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
import warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zuba", description="Football match predictions")
    sub = parser.add_subparsers(dest="command", required=True)
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--competition", choices=["epl", "wc"], default="epl",
                        help="Premier League (default) or World Cup")

    pick = sub.add_parser("pick", parents=[shared], help="predict one match")
    pick.add_argument("home")
    pick.add_argument("away")
    pick.add_argument("--home-advantage", action="store_true",
                      help="World Cup only: the first team is the host nation "
                           "(default: neutral venue). League games always have a home side")

    fetch = sub.add_parser("fetch", parents=[shared], help="update results, fixtures and scores")
    fetch.add_argument("--from", dest="start", type=dt.date.fromisoformat)
    fetch.add_argument("--to", dest="end", type=dt.date.fromisoformat)

    sub.add_parser("predict", parents=[shared], help="price every unplayed fixture in the database")

    backtest = sub.add_parser("backtest", parents=[shared], help="score the models on past seasons")
    backtest.add_argument("years", nargs="*", type=int, help="default: 2018 2022 2026")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    warnings.filterwarnings("ignore", category=UserWarning)

    if args.command == "pick":
        from zuba.ensemble import Ensemble

        print(Ensemble().fit().predict(args.home, args.away, neutral=not args.home_advantage))
    elif args.command == "fetch":
        from zuba.espn import save_fixtures

        if args.competition == "epl":
            from zuba.data.fetch import update_club_results

            for league, n in update_club_results().items():
                print(f"{league}: {n} matches played this season")
        print(f"{save_fixtures(args.start, args.end, args.competition)} fixtures saved")
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
