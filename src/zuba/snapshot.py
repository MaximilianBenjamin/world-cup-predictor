"""Save the fixtures and predictions to a JSON file, and load them back.

The SQLite database is not committed. The daily refresh on GitHub Actions
starts from an empty one, so this file is what carries state from one day to
the next: load it, fetch new results and fixtures, price them, save it again,
commit. The hosted app loads the same file when it starts and fits no models.

Keeping finished matches in the file matters. A prediction is only rewritten
while its match is unplayed, so the row left behind after full time is what
the model said before kickoff, and the season record is built from those.

Lineups are not saved; the app fetches them itself shortly before kickoff.
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "live" / "site.json"

_MATCH_COLUMNS = ("match_id", "competition", "date", "kickoff_ts", "home_team", "away_team",
                  "home_score", "away_score", "neutral", "completed")
_PREDICTION_COLUMNS = ("match_id", "generated_at", "model_version", "probs")


def save(conn: sqlite3.Connection, path: Path = SNAPSHOT) -> int:
    """Write every match and prediction to `path`. Returns the number of matches."""
    matches = [dict(r) for r in conn.execute(
        f"SELECT {', '.join(_MATCH_COLUMNS)} FROM matches ORDER BY date, match_id")]
    predictions = [
        {**dict(r), "probs": json.loads(r["probs"])}
        for r in conn.execute(
            f"SELECT {', '.join(_PREDICTION_COLUMNS)} FROM predictions ORDER BY match_id")
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "saved_at": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "matches": matches,
        "predictions": predictions,
    }, indent=1) + "\n")
    return len(matches)


def load(conn: sqlite3.Connection, path: Path = SNAPSHOT) -> int:
    """Insert the matches and predictions in `path`, replacing rows with the
    same match id. Returns the number of matches, or 0 if there is no file."""
    if not path.exists():
        return 0
    data = json.loads(path.read_text())
    conn.executemany(
        f"INSERT OR REPLACE INTO matches ({', '.join(_MATCH_COLUMNS)}) "
        f"VALUES ({', '.join(':' + c for c in _MATCH_COLUMNS)})",
        data["matches"],
    )
    conn.executemany(
        f"INSERT OR REPLACE INTO predictions ({', '.join(_PREDICTION_COLUMNS)}) "
        f"VALUES ({', '.join(':' + c for c in _PREDICTION_COLUMNS)})",
        [{**p, "probs": json.dumps(p["probs"])} for p in data["predictions"]],
    )
    conn.commit()
    return len(data["matches"])


def load_if_empty(conn: sqlite3.Connection, path: Path = SNAPSHOT) -> int:
    """Load the snapshot into a database that has no matches yet."""
    if conn.execute("SELECT 1 FROM matches LIMIT 1").fetchone():
        return 0
    return load(conn, path)
