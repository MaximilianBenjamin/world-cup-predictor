import json

import pytest
from fastapi.testclient import TestClient

from zuba.espn import _parse_event


def _event(home: str, away: str, state: str = "post") -> dict:
    return {
        "id": "101", "date": "2026-06-20T19:00Z",
        "status": {"type": {"state": state}},
        "competitions": [{"neutralSite": True, "competitors": [
            {"homeAway": "home", "team": {"displayName": home}, "score": "2"},
            {"homeAway": "away", "team": {"displayName": away}, "score": "1"},
        ]}],
    }


def test_espn_event_parsing():
    fx = _parse_event(_event("Türkiye", "Japan"))
    assert fx["home_team"] == "Turkey"  # mapped to the training data's spelling
    assert (fx["home_score"], fx["away_score"], fx["completed"]) == (2, 1, True)
    assert _parse_event(_event("Spain", "Japan", state="pre"))["home_score"] is None
    assert _parse_event(_event("Group A Winner", "Group B Runner-up")) is None


@pytest.fixture
def client(tmp_path, monkeypatch):
    import zuba.api.app as app_module
    from zuba.db import get_connection

    db = tmp_path / "test.db"
    monkeypatch.setattr(app_module, "get_connection", lambda: get_connection(db))
    conn = get_connection(db)
    conn.execute(
        "INSERT INTO matches (match_id, date, kickoff_ts, home_team, away_team) "
        "VALUES (1, '2999-01-01', '2999-01-01T18:00:00+00:00', 'Spain', 'Japan')"
    )
    probs = {"home_win_p": 0.6, "draw_p": 0.25, "away_win_p": 0.15, "over_2_5_p": 0.5}
    conn.execute(
        "INSERT INTO predictions VALUES (1, '2026-01-01', 'test', ?)", (json.dumps(probs),)
    )
    conn.commit()
    return TestClient(app_module.app)


def test_games_and_board(client):
    games = client.get("/api/games").json()["games"]
    assert [g["pick_label"] for g in games] == ["Spain"]
    board = client.get("/api/board/1").json()
    assert len(board["prices"]) == 5  # 3 results + over/under 2.5
    assert client.get("/api/board/99").status_code == 404


def test_lineups_before_they_are_published(client):
    assert client.get("/api/lineups/1").json()["available"] is False


def test_combine(client):
    res = client.post("/api/combine", json={"legs": [
        {"match_id": 1, "market": "1x2", "selection": "home"},
    ]})
    assert res.json()["combined_p"] == pytest.approx(0.6)
    assert client.post("/api/combine", json={"legs": []}).status_code == 400
