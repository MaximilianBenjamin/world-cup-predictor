// Response and request shapes for the backend API (see src/zuba/api/schemas.py).

export interface SelectionPrice {
  market: string;          // "1x2" | "dc" | "ou_2_5"
  market_label: string;
  selection: string;       // "home"/"draw"/"away" | "1x"/"12"/"x2" | "over"/"under"
  selection_label: string;
  model_p: number;
  fair_odds: number;
}

export interface GameSummary {
  match_id: number;
  date: string;
  kickoff_ts: string | null;
  home_team: string;
  away_team: string;
  completed: boolean;
  home_score: number | null;
  away_score: number | null;
  has_prediction: boolean;
  pick_selection: string | null;
  pick_label: string | null;
  pick_p: number | null;
  pick_fair_odds: number | null;
}

export interface GamesResponse {
  from_date: string;
  to_date: string;
  games: GameSummary[];
  model_name: string;
  model_version: string;
}

export interface MatchBoardResponse {
  match_id: number;
  date: string;
  kickoff_ts: string | null;
  home_team: string;
  away_team: string;
  completed: boolean;
  home_score: number | null;
  away_score: number | null;
  exp_home_goals: number | null;
  exp_away_goals: number | null;
  prices: SelectionPrice[];
}

// ---- lineups / pitch view ----

export interface LineupPlayer {
  name: string;
  shirt: number | null;
  position: string | null; // ESPN abbreviation: "G", "CD-L", "DM", "F", …
  slot: number;
}

export interface LineupSide {
  team: string;
  formation: string | null; // "4-3-3"
  starters: LineupPlayer[];
  bench: LineupPlayer[];
}

export interface LineupResponse {
  match_id: number;
  available: boolean;
  kickoff_ts: string | null;
  home: LineupSide | null;
  away: LineupSide | null;
}

export interface CombineLeg {
  match_id: number;
  market: string;
  selection: string;
}

export interface CombinedLeg {
  match_id: number;
  match_label: string;
  market: string;
  market_label: string;
  selection: string;
  selection_label: string;
  model_p: number;
  fair_odds: number;
}

export interface CombineResponse {
  legs: CombinedLeg[];
  combined_p: number;
  combined_fair_odds: number;
  correlated_warning: boolean;
  note: string;
}
