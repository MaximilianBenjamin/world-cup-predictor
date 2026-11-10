import datetime as dt

import pytest

from zuba import espn
from zuba.data import load_club_matches
from zuba.data.clubs import COLUMNS
from zuba.data.fetch import _played, current_season
from zuba.db import get_connection


@pytest.fixture(scope="module")
def matches():
    return load_club_matches()


def test_every_season_loads_in_full(matches):
    assert list(matches.columns) == COLUMNS
    assert matches["date"].is_monotonic_increasing
    done = matches[matches["season"] <= "2025-26"].groupby(["league", "season"]).size()
    assert (done["epl"] == 380).all() and len(done["epl"]) == 18
    assert (done["championship"] == 552).all()
    core = ["home_goals", "away_goals", "home_shots", "home_corners", "odds_h", "odds_over"]
    assert matches[core].isna().mean().max() < 0.001


def test_result_matches_the_score(matches):
    diff = matches["home_goals"] - matches["away_goals"]
    assert (matches.loc[diff > 0, "result"] == "H").all()
    assert (matches.loc[diff == 0, "result"] == "D").all()
    assert (matches.loc[diff < 0, "result"] == "A").all()


def test_xg_comes_from_understat_and_from_the_season_files(matches):
    epl = matches[matches["league"] == "epl"]
    assert epl.loc[epl["season"] == "2016-17", "home_xg"].notna().all()   # Understat
    assert epl.loc[epl["season"] == "2026-27", "home_xg"].notna().all()   # in the file
    assert epl.loc[epl["season"] == "2010-11", "home_xg"].isna().all()    # before either


def test_max_date_is_exclusive(matches):
    cut = load_club_matches(max_date="2020-01-01")
    assert cut["date"].max() < dt.datetime(2020, 1, 1)
    assert len(load_club_matches(leagues=("epl",))) < len(matches)


def test_current_season():
    assert current_season(dt.date(2026, 11, 10)) == "2026-27"
    assert current_season(dt.date(2027, 5, 20)) == "2026-27"
    assert current_season(dt.date(2027, 7, 1)) == "2027-28"
    assert current_season(dt.date(1999, 12, 1)) == "1999-00"


def test_a_file_without_results_is_rejected():
    assert _played(b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n01/08/26,A,B,1,0\n02/08/26,C,D,,\n") == 1
    with pytest.raises(ValueError):
        _played(b"<html>not found</html>\n")


def test_espn_club_names_map_onto_the_training_data(matches):
    known = set(matches["home_team"])
    assert set(espn.CLUB_NAMES.values()) <= known | {"Charlton", "Oxford", "Plymouth"}
    assert espn.team_name("Brighton & Hove Albion", "epl") == "Brighton"
    assert espn.team_name("Arsenal", "epl") == "Arsenal"
    assert espn.team_name("Türkiye", "wc") == "Turkey"


def test_league_fixtures_are_never_neutral():
    event = {
        "id": "1", "date": "2026-11-21T15:00Z", "status": {"type": {"state": "pre"}},
        "competitions": [{"competitors": [
            {"homeAway": "home", "team": {"displayName": "Manchester City"}},
            {"homeAway": "away", "team": {"displayName": "Fulham"}},
        ]}],
    }
    fx = espn._parse_event(event, "epl")
    assert (fx["home_team"], fx["neutral"], fx["competition"]) == ("Man City", False, "epl")
    assert espn._parse_event(event, "wc")["neutral"] is True


def test_old_databases_gain_the_competition_column(tmp_path):
    import sqlite3

    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE matches (match_id INTEGER PRIMARY KEY, date TEXT NOT NULL, "
                "kickoff_ts TEXT, home_team TEXT NOT NULL, away_team TEXT NOT NULL, "
                "home_score INTEGER, away_score INTEGER, neutral INTEGER NOT NULL DEFAULT 1, "
                "completed INTEGER NOT NULL DEFAULT 0)")
    old.execute("INSERT INTO matches (match_id, date, home_team, away_team) "
                "VALUES (1, '2026-06-11', 'A', 'B')")
    old.commit()
    old.close()
    row = get_connection(path).execute("SELECT competition FROM matches").fetchone()
    assert row["competition"] == "wc"
