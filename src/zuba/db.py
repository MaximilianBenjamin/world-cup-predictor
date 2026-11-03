"""SQLite storage for fixtures, predictions and lineups.

The database is a local file (`zuba.db` at the repo root, or `ZUBA_DB` if set).
It only holds things that change during a tournament; the training data lives
in `data/international_results.csv`. `get_connection()` creates the tables on
first use, so there is no separate setup step.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("ZUBA_DB", Path(__file__).resolve().parents[2] / "zuba.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    match_id    INTEGER PRIMARY KEY,   -- ESPN event id
    date        TEXT NOT NULL,         -- UTC calendar date, YYYY-MM-DD
    kickoff_ts  TEXT,                  -- ISO timestamp with UTC offset
    home_team   TEXT NOT NULL,         -- names as used in the training data
    away_team   TEXT NOT NULL,
    home_score  INTEGER,
    away_score  INTEGER,
    neutral     INTEGER NOT NULL DEFAULT 1,
    completed   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS predictions (
    match_id       INTEGER PRIMARY KEY REFERENCES matches(match_id),
    generated_at   TEXT NOT NULL,
    model_version  TEXT NOT NULL,
    probs          TEXT NOT NULL        -- JSON object: column name -> probability
);

CREATE TABLE IF NOT EXISTS lineups (
    match_id   INTEGER NOT NULL REFERENCES matches(match_id),
    side       TEXT NOT NULL CHECK (side IN ('home', 'away')),
    slot       INTEGER NOT NULL,        -- order ESPN lists the players in
    name       TEXT NOT NULL,
    shirt      INTEGER,
    position   TEXT,
    starter    INTEGER NOT NULL,
    PRIMARY KEY (match_id, side, slot)
);

CREATE TABLE IF NOT EXISTS formations (
    match_id    INTEGER NOT NULL REFERENCES matches(match_id),
    side        TEXT NOT NULL CHECK (side IN ('home', 'away')),
    formation   TEXT,
    fetched_at  TEXT NOT NULL,
    PRIMARY KEY (match_id, side)
);
"""


def get_connection(path: Path | str | None = None) -> sqlite3.Connection:
    """Open the database, creating the tables if they don't exist yet."""
    conn = sqlite3.connect(str(path or DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn
