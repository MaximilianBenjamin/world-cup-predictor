"""Response and request bodies for the JSON API."""

from __future__ import annotations

from pydantic import BaseModel


class SelectionPrice(BaseModel):
    """One outcome with the model's probability and the matching fair odds
    (1 / probability, i.e. the decimal odds at which a bet breaks even)."""

    market: str           # "1x2" | "dc" | "ou_2_5" ...
    market_label: str     # "Match result" | "Double chance" | "Over/Under 2.5"
    selection: str        # "home"/"draw"/"away" | "1x"/"12"/"x2" | "over"/"under"
    selection_label: str
    model_p: float
    fair_odds: float


class GameSummary(BaseModel):
    match_id: int
    competition: str = "epl"        # "epl" | "wc"
    date: str
    kickoff_ts: str | None = None   # ISO with UTC offset; the UI converts it
    home_team: str
    away_team: str
    completed: bool
    home_score: int | None = None
    away_score: int | None = None
    has_prediction: bool = False
    p_home: float | None = None
    p_draw: float | None = None
    p_away: float | None = None
    # The model's most likely result, if the match has been priced.
    pick_selection: str | None = None   # "home" | "draw" | "away"
    pick_label: str | None = None       # team name or "Draw"
    pick_p: float | None = None
    pick_fair_odds: float | None = None


class GamesResponse(BaseModel):
    from_date: str
    to_date: str
    games: list[GameSummary]
    model_name: str
    model_version: str


class MatchBoardResponse(BaseModel):
    match_id: int
    competition: str = "epl"
    date: str
    kickoff_ts: str | None = None
    home_team: str
    away_team: str
    completed: bool
    home_score: int | None = None
    away_score: int | None = None
    exp_home_goals: float | None = None
    exp_away_goals: float | None = None
    prices: list[SelectionPrice] = []


class CombineLeg(BaseModel):
    match_id: int
    market: str
    selection: str


class CombineRequest(BaseModel):
    legs: list[CombineLeg]


class CombinedLeg(BaseModel):
    match_id: int
    match_label: str
    market: str
    market_label: str
    selection: str
    selection_label: str
    model_p: float
    fair_odds: float


class CombineResponse(BaseModel):
    legs: list[CombinedLeg]
    combined_p: float
    combined_fair_odds: float
    correlated_warning: bool
    note: str


class LineupPlayer(BaseModel):
    name: str
    shirt: int | None = None
    position: str | None = None   # ESPN abbreviation, e.g. "G", "CD-L", "DM"
    slot: int                     # roster order, used to place players on the pitch


class LineupSide(BaseModel):
    team: str
    formation: str | None = None  # e.g. "4-3-3"
    starters: list[LineupPlayer]
    bench: list[LineupPlayer]


class LineupResponse(BaseModel):
    match_id: int
    available: bool               # true once ESPN publishes the XIs (~1h before kickoff)
    kickoff_ts: str | None = None
    home: LineupSide | None = None
    away: LineupSide | None = None


class SeasonGame(BaseModel):
    """A finished match with what the model said before kickoff."""

    date: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    p_home: float
    p_draw: float
    p_away: float
    p_result: float               # probability given to the result that happened
    correct: bool                 # the most likely result happened


class SeasonRecord(BaseModel):
    season: str
    matches: int
    correct: int
    log_loss: float | None = None       # None until a match has been played
    games: list[SeasonGame]             # newest first


class PerformanceResponse(BaseModel):
    backtest: dict | None = None        # docs/backtest_epl.json, absent until it has been run
    season: SeasonRecord
