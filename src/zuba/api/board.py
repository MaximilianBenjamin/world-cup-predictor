"""Fair-odds board for one match, and the bet-builder that combines picks.

Fair odds are 1 / model probability. When two picks from the same match are a
result plus an over/under line (e.g. home win AND over 2.5), the combined
probability is read straight from the stored joint value. Any other combination
from one match falls back to multiplying probabilities, which assumes they are
independent; the response flags that.
"""

from __future__ import annotations

from collections.abc import Mapping

from zuba.api.schemas import (
    CombinedLeg,
    CombineResponse,
    GameSummary,
    MatchBoardResponse,
    SelectionPrice,
)

Probs = Mapping[str, float]
OU_LINES = ("0_5", "1_5", "2_5", "3_5", "4_5")
_JOINT_LINES = {"1_5": "15", "2_5": "25", "3_5": "35"}
_RESULT_PREFIX = {("1x2", "home"): "h", ("1x2", "away"): "a", ("dc", "1x"): "dc1x", ("dc", "x2"): "dcx2"}
_COLUMNS = {
    "1x2": {"home": "home_win_p", "draw": "draw_p", "away": "away_win_p"},
    "dc": {"1x": "dc_1x_p", "12": "dc_12_p", "x2": "dc_x2_p"},
}


def fair_odds(p: float) -> float:
    return 1.0 / max(p, 1e-6)


def market_label(market: str) -> str:
    if market == "1x2":
        return "Match result"
    if market == "dc":
        return "Double chance"
    if market.startswith("ou_"):
        return f"Over/Under {market[3:].replace('_', '.')}"
    return market


def selection_label(market: str, selection: str, home: str, away: str) -> str:
    if market == "1x2":
        return {"home": home, "draw": "Draw", "away": away}.get(selection, selection)
    if market == "dc":
        return {"1x": f"{home} or Draw", "12": f"{home} or {away}",
                "x2": f"Draw or {away}"}.get(selection, selection)
    if market.startswith("ou_"):
        return f"{selection.capitalize()} {market[3:].replace('_', '.')}"
    return selection


def probability(probs: Probs, market: str, selection: str) -> float | None:
    """The model's probability for one pick, or None if the pick is unknown."""
    if market in _COLUMNS:
        col = _COLUMNS[market].get(selection)
        return probs.get(col) if col else None
    if market.startswith("ou_") and selection in ("over", "under"):
        over = probs.get(f"over_{market[3:]}_p")
        if over is None:
            return None
        return over if selection == "over" else 1.0 - over
    return None


def _price(market: str, selection: str, probs: Probs, home: str, away: str) -> SelectionPrice | None:
    p = probability(probs, market, selection)
    if p is None:
        return None
    return SelectionPrice(
        market=market, market_label=market_label(market),
        selection=selection, selection_label=selection_label(market, selection, home, away),
        model_p=p, fair_odds=fair_odds(p),
    )


def _match_fields(m: Mapping) -> dict:
    return {
        "match_id": m["match_id"], "date": m["date"], "kickoff_ts": m["kickoff_ts"],
        "home_team": m["home_team"], "away_team": m["away_team"],
        "completed": bool(m["completed"]),
        "home_score": m["home_score"], "away_score": m["away_score"],
    }


def build_board(match: Mapping, probs: Probs | None) -> MatchBoardResponse:
    home, away = match["home_team"], match["away_team"]
    picks = [("1x2", s) for s in ("home", "draw", "away")]
    picks += [("dc", s) for s in ("1x", "12", "x2")]
    picks += [(f"ou_{line}", s) for line in OU_LINES for s in ("over", "under")]
    prices = [_price(m, s, probs, home, away) for m, s in picks] if probs else []
    return MatchBoardResponse(
        **_match_fields(match),
        exp_home_goals=probs.get("exp_home_goals") if probs else None,
        exp_away_goals=probs.get("exp_away_goals") if probs else None,
        prices=[p for p in prices if p is not None],
    )


def build_game_summary(match: Mapping, probs: Probs | None) -> GameSummary:
    summary = GameSummary(**_match_fields(match))
    if probs:
        options = {s: probability(probs, "1x2", s) for s in ("home", "draw", "away")}
        pick = max(options, key=options.get)
        summary.has_prediction = True
        summary.pick_selection = pick
        summary.pick_label = selection_label("1x2", pick, match["home_team"], match["away_team"])
        summary.pick_p = options[pick]
        summary.pick_fair_odds = fair_odds(options[pick])
    return summary


def _joint(probs: Probs, a: tuple[str, str], b: tuple[str, str]) -> float | None:
    """Exact P(a and b) for a result + over/under pair from the same match."""
    for (m1, s1), (m2, s2) in ((a, b), (b, a)):
        prefix = _RESULT_PREFIX.get((m1, s1))
        line = _JOINT_LINES.get(m2[3:]) if m2.startswith("ou_") else None
        if prefix and line:
            return probs.get(f"{prefix}_{'o' if s2 == 'over' else 'u'}{line}_p")
    return None


def combine(
    legs: list[tuple[int, str, str]],
    matches: Mapping[int, Mapping],
    probs: Mapping[int, Probs],
) -> CombineResponse:
    """Combine (match_id, market, selection) picks into one probability and price."""
    out: list[CombinedLeg] = []
    by_match: dict[int, list[tuple[str, str]]] = {}
    for match_id, market, selection in legs:
        if match_id not in matches or match_id not in probs:
            raise ValueError(f"no prediction for match {match_id}")
        p = probability(probs[match_id], market, selection)
        if p is None:
            raise ValueError(f"unknown pick: {market}/{selection}")
        home, away = matches[match_id]["home_team"], matches[match_id]["away_team"]
        out.append(CombinedLeg(
            match_id=match_id, match_label=f"{home} vs {away}",
            market=market, market_label=market_label(market),
            selection=selection, selection_label=selection_label(market, selection, home, away),
            model_p=p, fair_odds=fair_odds(p),
        ))
        by_match.setdefault(match_id, []).append((market, selection))

    combined, assumed_independent, used_joint = 1.0, False, False
    for match_id, picks in by_match.items():
        joint = _joint(probs[match_id], *picks) if len(picks) == 2 else None
        if joint is not None:
            combined *= joint
            used_joint = True
        else:
            for market, selection in picks:
                combined *= probability(probs[match_id], market, selection)
            assumed_independent |= len(picks) > 1

    if assumed_independent:
        note = ("Some picks are from the same match and have no exact joint probability, "
                "so they are treated as independent. The true price would differ.")
    elif used_joint:
        note = "Same-match picks priced with the model's exact joint probability."
    else:
        note = "Picks are from different matches, so they are combined as independent."

    return CombineResponse(
        legs=out, combined_p=combined, combined_fair_odds=fair_odds(combined),
        correlated_warning=assumed_independent, note=note,
    )
