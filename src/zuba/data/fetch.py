"""Download the current season's results from football-data.co.uk.

The site republishes each league's season file a day or two after every round
of matches, with results, shots, corners, expected goals and odds. Past seasons
never change, so only the current one is fetched.

    update_club_results()   -> {"epl": 100, "championship": 180}
"""

from __future__ import annotations

import datetime as dt
import io
import logging
import urllib.request

import pandas as pd

from zuba.data.clubs import LEAGUES, season_path

logger = logging.getLogger(__name__)

_URL = "https://www.football-data.co.uk/mmz4281/{code}/{division}.csv"
_REQUIRED = {"Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"}


def current_season(today: dt.date | None = None) -> str:
    """The season in progress, e.g. "2026-27". A season runs July to June."""
    today = today or dt.date.today()
    start = today.year if today.month >= 7 else today.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (zuba)"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed host
        return resp.read()


def _played(raw: bytes) -> int:
    """Number of played matches in a season file. Raises if it isn't one."""
    df = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig", encoding_errors="replace")
    missing = _REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"season file is missing columns {sorted(missing)}")
    return int(df.dropna(subset=["HomeTeam", "FTHG", "FTAG"]).shape[0])


def update_club_results(season: str | None = None) -> dict[str, int]:
    """Refresh this season's file for each league. Returns matches played per league.

    A download replaces the stored file only if it parses and has at least as
    many played matches. Anything else raises, so a broken or truncated
    download never overwrites good data.
    """
    season = season or current_season()
    code = season[2:4] + season[5:7]  # "2026-27" -> "2627"
    counts = {}
    for league, division in LEAGUES.items():
        raw = _download(_URL.format(code=code, division=division))
        n_new = _played(raw)
        path = season_path(league, season)
        n_old = _played(path.read_bytes()) if path.exists() else 0
        if n_new < n_old:
            raise ValueError(f"{league} {season}: download has {n_new} matches, stored file has {n_old}")
        path.write_bytes(raw)
        logger.info("%s %s: %d matches (%+d)", league, season, n_new, n_new - n_old)
        counts[league] = n_new
    return counts
