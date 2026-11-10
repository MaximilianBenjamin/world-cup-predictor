"""Command-line entry point.

    uv run zuba fetch                        # new results, fixtures and scores
    uv run zuba predict                      # price every unplayed fixture
    uv run zuba pick Arsenal Chelsea         # one-off prediction
    uv run zuba backtest                     # score the models on past seasons
    uv run zuba archive                      # price the finished 2026 World Cup (see markets.py)
    uv run zuba table                        # current table and predicted final table
    uv run zuba snapshot save                # write fixtures and predictions to data/live/site.json
    uv run zuba snapshot load                # read them back into the database

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
    backtest.add_argument("years", nargs="*", type=int,
                          help="World Cup only: tournaments to score (default: 2018 2022 2026)")

    sub.add_parser("archive", help="price the finished 2026 World Cup from pre-tournament data")
    sub.add_parser("table", help="write the current and predicted Premier League tables")

    snapshot = sub.add_parser("snapshot", help="save or load fixtures and predictions as JSON")
    snapshot.add_argument("action", choices=["save", "load"])

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    warnings.filterwarnings("ignore", category=UserWarning)

    if args.command == "pick" and args.competition == "epl":
        import pandas as pd

        from zuba.stacks.premier_league import price_fixtures

        fixture = pd.DataFrame([{"date": dt.date.today(), "home_team": args.home,
                                 "away_team": args.away}])
        _, preds, _ = price_fixtures(fixture)
        (p_home, p_draw, p_away), over = preds.result[0], preds.over25[0]
        print(f"{args.home} vs {args.away}\n"
              f"  {args.home} {p_home:.1%}  Draw {p_draw:.1%}  {args.away} {p_away:.1%}\n"
              f"  Over 2.5 {over:.1%}  Under 2.5 {1 - over:.1%}")
        for name, probs in preds.result_models.items():
            print(f"    {name:12s} {probs[0][0]:.1%} / {probs[0][1]:.1%} / {probs[0][2]:.1%}")
    elif args.command == "pick":
        from zuba.stacks.international import Ensemble

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

        print(f"{predict_upcoming(args.competition)} matches priced")
    elif args.command == "archive":
        from zuba.markets import price_world_cup_archive

        print(f"{price_world_cup_archive()} World Cup matches priced")
    elif args.command == "table":
        from zuba import table

        built = table.write()
        print(f"{built['season']}: {built['matches_played']} played, "
              f"{built['matches_remaining']} simulated {built['simulations']:,} times\n")
        print(f"{'':3}{'Predicted final table':22}{'Pts':>6}{'GD':>7}{'Title':>8}{'Top 4':>8}{'Down':>8}")
        for r in built["predicted"]:
            print(f"{r['position']:>2} {r['team']:22}{r['points']:>6.1f}{r['goal_difference']:>+7.1f}"
                  f"{r['p_title']:>8.1%}{r['p_top4']:>8.1%}{r['p_relegation']:>8.1%}")
    elif args.command == "snapshot":
        from zuba import snapshot as snap
        from zuba.db import get_connection

        n = getattr(snap, args.action)(get_connection())
        print(f"{n} matches {'saved to' if args.action == 'save' else 'loaded from'} {snap.SNAPSHOT}")
    elif args.command == "backtest" and args.competition == "epl":
        from zuba.evaluate.report import print_report, run_premier_league

        print_report(run_premier_league())
    elif args.command == "backtest":
        from zuba.evaluate.world_cup import run

        results, goals = run(args.years or None)
        print("\nMatch result, group stages\n")
        print(results.to_string(index=False, float_format="%.3f"))
        print("\nOver/under 2.5 goals, all group-stage games\n")
        print(goals.to_string(index=False, float_format="%.3f"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
