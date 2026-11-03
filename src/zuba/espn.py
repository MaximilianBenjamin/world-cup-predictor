"""World Cup fixtures, scores and lineups from ESPN's public JSON API.

ESPN needs no API key and returns clean national-team names, kickoff times and
final scores. Starting XIs appear on the match summary endpoint about an hour
before kickoff.

    fetch_fixtures(start, end)  -> list of fixture dicts
    save_fixtures(start, end)   -> upsert them into `matches`
    fetch_lineups(espn_id)      -> both teams' lineups, or None if not out yet
    save_lineups(match_id)      -> upsert them into `lineups` / `formations`
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import re
import sqlite3
import urllib.request

from zuba.db import get_connection

logger = logging.getLogger(__name__)

_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"

# ESPN's spelling -> the spelling in the training data.
TEAM_NAMES = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Congo DR": "DR Congo",
    "Czechia": "Czech Republic",
    "Türkiye": "Turkey",
}

# Knockout fixtures are listed before the teams are known, with names like
# "Group A Winner" or "Semifinal 1 Loser". Those rows are skipped.
_PLACEHOLDER = re.compile(
    r"winner|loser|runner|\bTBD\b|to be determined|round of|group [a-l]\b|"
    r"quarter|semi[- ]?final|\bfinal\b|place|\d(st|nd|rd|th)?\b",
    re.IGNORECASE,
)


def team_name(espn_name: str) -> str:
    return TEAM_NAMES.get(espn_name, espn_name)


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (zuba)"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed host
        return json.load(resp)


def _parse_event(event: dict) -> dict | None:
    comp = event["competitions"][0]
    sides = {c["homeAway"]: c for c in comp["competitors"]}
    home, away = sides["home"], sides["away"]
    home_name, away_name = home["team"]["displayName"], away["team"]["displayName"]
    if _PLACEHOLDER.search(home_name) or _PLACEHOLDER.search(away_name):
        return None

    kickoff = dt.datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
    completed = event["status"]["type"].get("state") == "post"

    def score(side: dict) -> int | None:
        raw = side.get("score")
        return int(raw) if completed and str(raw).isdigit() else None

    return {
        "match_id": int(event["id"]),
        "date": kickoff.date().isoformat(),
        "kickoff_ts": kickoff.isoformat(),
        "home_team": team_name(home_name),
        "away_team": team_name(away_name),
        "home_score": score(home),
        "away_score": score(away),
        # ESPN doesn't flag neutral venues reliably. Almost every World Cup game
        # is at a neutral ground, so that is the default.
        "neutral": comp.get("neutralSite") is not False,
        "completed": completed,
    }


def fetch_fixtures(start: dt.date, end: dt.date) -> list[dict]:
    """All confirmed World Cup fixtures between start and end (inclusive).

    One request per day: ESPN's date-range form of the query is unreliable.
    """
    fixtures: dict[int, dict] = {}
    day = start
    while day <= end:
        data = _get(f"{_BASE}/scoreboard?dates={day:%Y%m%d}")
        for event in data.get("events", []):
            try:
                fx = _parse_event(event)
            except (KeyError, ValueError) as exc:
                logger.warning("skipping malformed ESPN event %s: %r", event.get("id"), exc)
                continue
            if fx:
                fixtures[fx["match_id"]] = fx
        day += dt.timedelta(days=1)
    return sorted(fixtures.values(), key=lambda f: (f["kickoff_ts"], f["match_id"]))


def save_fixtures(
    start: dt.date | None = None,
    end: dt.date | None = None,
    conn: sqlite3.Connection | None = None,
) -> int:
    """Upsert fixtures into `matches`. Defaults to 3 days back to 25 days ahead,
    so recent games get their final scores and new knockout ties show up."""
    conn = conn or get_connection()
    today = dt.date.today()
    fixtures = fetch_fixtures(start or today - dt.timedelta(days=3),
                              end or today + dt.timedelta(days=25))
    conn.executemany(
        """
        INSERT INTO matches (match_id, date, kickoff_ts, home_team, away_team,
                             home_score, away_score, neutral, completed)
        VALUES (:match_id, :date, :kickoff_ts, :home_team, :away_team,
                :home_score, :away_score, :neutral, :completed)
        ON CONFLICT(match_id) DO UPDATE SET
            date = excluded.date, kickoff_ts = excluded.kickoff_ts,
            home_score = excluded.home_score, away_score = excluded.away_score,
            completed = excluded.completed
        """,
        fixtures,
    )
    conn.commit()
    return len(fixtures)


def fetch_lineups(espn_id: int) -> dict | None:
    """{"home": side, "away": side}, or None until both starting XIs are out.

    Each side is {"formation": str | None, "players": [{name, shirt, position,
    starter, slot}, ...]}.
    """
    data = _get(f"{_BASE}/summary?event={espn_id}")
    out: dict[str, dict] = {}
    for roster in data.get("rosters") or []:
        side = roster.get("homeAway")
        if side not in ("home", "away"):
            continue
        players = []
        for slot, entry in enumerate(roster.get("roster") or []):
            name = (entry.get("athlete") or {}).get("displayName")
            if not name:
                continue
            jersey = str(entry.get("jersey") or "")
            players.append({
                "slot": slot,
                "name": name,
                "shirt": int(jersey) if jersey.isdigit() else None,
                "position": (entry.get("position") or {}).get("abbreviation"),
                "starter": bool(entry.get("starter")),
            })
        out[side] = {"formation": roster.get("formation"), "players": players}

    if set(out) != {"home", "away"}:
        return None
    if not any(p["starter"] for p in out["home"]["players"]):
        return None
    return out


def save_lineups(match_id: int, conn: sqlite3.Connection | None = None) -> bool:
    """Fetch and store one match's lineups. Returns True if they were published.

    Existing rows are replaced, so a late change to the team sheet is picked up.
    """
    conn = conn or get_connection()
    try:
        lineups = fetch_lineups(match_id)
    except OSError as exc:
        logger.warning("lineup fetch failed for match %s: %r", match_id, exc)
        return False
    if not lineups:
        return False

    now = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
    conn.execute("DELETE FROM lineups WHERE match_id = ?", (match_id,))
    for side, data in lineups.items():
        conn.executemany(
            "INSERT INTO lineups (match_id, side, slot, name, shirt, position, starter) "
            "VALUES (:match_id, :side, :slot, :name, :shirt, :position, :starter)",
            [{**p, "match_id": match_id, "side": side} for p in data["players"]],
        )
        conn.execute(
            "INSERT OR REPLACE INTO formations (match_id, side, formation, fetched_at) "
            "VALUES (?, ?, ?, ?)",
            (match_id, side, data["formation"], now),
        )
    conn.commit()
    return True
