"""FastAPI backend for the React site.

    uv run uvicorn zuba.api.app:app --port 8001

Endpoints (all read-only apart from /api/combine, which only does arithmetic):
    GET  /api/games            upcoming fixtures with the model's pick for each
                               (?competition=epl or wc)
    GET  /api/performance      Premier League backtest scores and this season's record
    GET  /api/board/{id}       every market for one match, with fair odds
    GET  /api/lineups/{id}     starting XIs once ESPN publishes them
    POST /api/combine          price several picks together (bet-builder)

Optional background jobs, set by environment variable:
    ZUBA_REFRESH_AT=09:00      refresh fixtures and predictions on startup and
                               daily at that time (ZUBA_REFRESH_TZ, default
                               Africa/Johannesburg)
    ZUBA_LINEUPS=1             fetch lineups from 50 minutes before each kickoff

On startup, an empty database is filled from data/live/site.json if that file
exists. That is how the hosted app gets its fixtures and predictions: the
daily GitHub Actions run writes the file and the app only serves it.

If frontend/dist exists (run `npm run build` in frontend/), the site is served
from the same port.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from zuba import espn, snapshot
from zuba.api import board, performance
from zuba.api.schemas import (
    CombineRequest,
    CombineResponse,
    GamesResponse,
    LineupPlayer,
    LineupResponse,
    LineupSide,
    MatchBoardResponse,
    PerformanceResponse,
)
from zuba.data.fetch import update_club_results
from zuba.db import get_connection
from zuba.markets import MODEL_VERSION, predict_upcoming

log = logging.getLogger("uvicorn.error")


# ---- background jobs --------------------------------------------------------


def refresh() -> None:
    """Pull Premier League results, fixtures and scores, then re-price unplayed matches."""
    try:
        update_club_results()
        n_fixtures = espn.save_fixtures()
        n_priced = predict_upcoming()
        log.info("refresh: %d fixtures updated, %d matches priced", n_fixtures, n_priced)
    except Exception:
        log.exception("refresh failed")


def _daily_refresh(at: str, tz: dt.tzinfo) -> None:
    refresh()
    hour, minute = map(int, at.split(":"))
    while True:
        now = dt.datetime.now(tz)
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += dt.timedelta(days=1)
        time.sleep((target - now).total_seconds())
        refresh()


def _lineup_watch(lead_minutes: int = 50) -> None:
    """Every 5 minutes, fetch lineups for matches kicking off soon."""
    done: set[int] = set()
    while True:
        try:
            conn = get_connection()
            now = dt.datetime.now(dt.UTC)
            for row in conn.execute(
                "SELECT match_id, kickoff_ts FROM matches WHERE completed = 0 AND kickoff_ts IS NOT NULL"
            ):
                kickoff = dt.datetime.fromisoformat(row["kickoff_ts"])
                opens = kickoff - dt.timedelta(minutes=lead_minutes)
                closes = kickoff + dt.timedelta(minutes=15)
                if row["match_id"] in done or not opens <= now < closes:
                    continue
                if espn.save_lineups(row["match_id"], conn):
                    done.add(row["match_id"])
                    log.info("lineups saved for match %s", row["match_id"])
        except Exception:
            log.exception("lineup check failed")
        time.sleep(300)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if n := snapshot.load_if_empty(get_connection()):
        log.info("loaded %d matches from %s", n, snapshot.SNAPSHOT)
    if at := os.environ.get("ZUBA_REFRESH_AT", "").strip():
        tz = ZoneInfo(os.environ.get("ZUBA_REFRESH_TZ", "Africa/Johannesburg"))
        threading.Thread(target=_daily_refresh, args=(at, tz), daemon=True).start()
        log.info("daily refresh at %s %s", at, tz)
    if os.environ.get("ZUBA_LINEUPS", "").strip().lower() in ("1", "true", "yes"):
        threading.Thread(target=_lineup_watch, daemon=True).start()
        log.info("lineup watcher on")
    yield


# ---- app, CORS, security headers, rate limit --------------------------------

app = FastAPI(title="zuba", version=MODEL_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"]
    + [o.strip() for o in os.environ.get("ZUBA_ALLOWED_ORIGINS", "").split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}
_RATE_LIMIT = int(os.environ.get("ZUBA_RATE_LIMIT", "120"))  # requests per minute per IP
_hits: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def _guard(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    hits = _hits[ip]
    while hits and now - hits[0] > 60:
        hits.popleft()
    hits.append(now)
    if len(hits) > _RATE_LIMIT:
        return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
    response = await call_next(request)
    response.headers.update(_SECURITY_HEADERS)
    return response


# ---- data access ------------------------------------------------------------


def _matches(conn, ids: list[int]) -> dict[int, dict]:
    marks = ",".join("?" * len(ids))
    rows = conn.execute(f"SELECT * FROM matches WHERE match_id IN ({marks})", ids)
    return {r["match_id"]: dict(r) for r in rows}


def _predictions(conn, ids: list[int]) -> dict[int, dict]:
    marks = ",".join("?" * len(ids))
    rows = conn.execute(f"SELECT match_id, probs FROM predictions WHERE match_id IN ({marks})", ids)
    return {r["match_id"]: json.loads(r["probs"]) for r in rows}


# ---- routes -----------------------------------------------------------------


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "model_version": MODEL_VERSION}


@app.get("/api/games", response_model=GamesResponse)
def games(competition: Literal["epl", "wc"] = "epl",
          include_completed: bool = False) -> GamesResponse:
    conn = get_connection()
    upcoming = "" if include_completed else "AND completed = 0 AND date >= date('now')"
    rows = [dict(r) for r in conn.execute(
        f"SELECT * FROM matches WHERE competition = ? {upcoming} ORDER BY kickoff_ts, match_id",
        (competition,),
    )]
    preds = _predictions(conn, [r["match_id"] for r in rows])
    summaries = [board.build_game_summary(r, preds.get(r["match_id"])) for r in rows]
    dates = [s.date for s in summaries]
    return GamesResponse(
        from_date=min(dates, default=""), to_date=max(dates, default=""),
        games=summaries, model_name="zuba", model_version=MODEL_VERSION,
    )


@app.get("/api/performance", response_model=PerformanceResponse)
def model_performance() -> PerformanceResponse:
    return PerformanceResponse(
        backtest=performance.backtest_report(),
        season=performance.season_record(get_connection()),
    )


@app.get("/api/board/{match_id}", response_model=MatchBoardResponse)
def match_board(match_id: int) -> MatchBoardResponse:
    conn = get_connection()
    match = _matches(conn, [match_id]).get(match_id)
    if match is None:
        raise HTTPException(404, f"match {match_id} not found")
    return board.build_board(match, _predictions(conn, [match_id]).get(match_id))


@app.get("/api/lineups/{match_id}", response_model=LineupResponse)
def lineups(match_id: int) -> LineupResponse:
    conn = get_connection()
    match = _matches(conn, [match_id]).get(match_id)
    if match is None:
        raise HTTPException(404, f"match {match_id} not found")
    formations = dict(conn.execute(
        "SELECT side, formation FROM formations WHERE match_id = ?", (match_id,)
    ).fetchall())

    def side(name: str) -> LineupSide | None:
        rows = conn.execute(
            "SELECT * FROM lineups WHERE match_id = ? AND side = ? ORDER BY slot", (match_id, name)
        ).fetchall()
        if not rows:
            return None
        players = [(r["starter"], LineupPlayer(name=r["name"], shirt=r["shirt"],
                                               position=r["position"], slot=r["slot"])) for r in rows]
        return LineupSide(
            team=match[f"{name}_team"], formation=formations.get(name),
            starters=[p for starter, p in players if starter],
            bench=[p for starter, p in players if not starter],
        )

    home, away = side("home"), side("away")
    return LineupResponse(
        match_id=match_id, kickoff_ts=match["kickoff_ts"], home=home, away=away,
        available=bool(home and home.starters and away and away.starters),
    )


@app.post("/api/combine", response_model=CombineResponse)
def combine(req: CombineRequest) -> CombineResponse:
    if not req.legs:
        raise HTTPException(400, "no picks to combine")
    conn = get_connection()
    ids = sorted({leg.match_id for leg in req.legs})
    try:
        return board.combine([(leg.match_id, leg.market, leg.selection) for leg in req.legs],
                             _matches(conn, ids), _predictions(conn, ids))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


# ---- built frontend ---------------------------------------------------------

_DIST = (Path(__file__).resolve().parents[3] / "frontend" / "dist").resolve()

if (_DIST / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "not found")
        file = (_DIST / path).resolve()
        if path and file.is_file() and file.is_relative_to(_DIST):  # no path traversal
            return FileResponse(file)
        return FileResponse(_DIST / "index.html")
