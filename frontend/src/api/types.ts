// Response and request shapes for the backend API (see src/zuba/api/schemas.py).

export interface SelectionPrice {
  market: string;          // "1x2" | "dc" | "ou_2_5"
  market_label: string;
  selection: string;       // "home"/"draw"/"away" | "1x"/"12"/"x2" | "over"/"under"
  selection_label: string;
  model_p: number;
  fair_odds: number;
}

export type Competition = "epl" | "wc";

export interface GameSummary {
  match_id: number;
  competition: Competition;
  date: string;
  kickoff_ts: string | null;
  home_team: string;
  away_team: string;
  completed: boolean;
  home_score: number | null;
  away_score: number | null;
  has_prediction: boolean;
  p_home: number | null;
  p_draw: number | null;
  p_away: number | null;
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
  competition: Competition;
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

// ---- model performance ----

export interface Interval { value: number; low: number; high: number }

export interface ModelScore {
  log_loss: Interval;
  brier: Interval;
  rps: Interval;
  accuracy: Interval;
  ece: { value: number };
}

export interface CalibrationBin { stated: number; observed: number; count: number }

/** docs/backtest_epl.json. Keys of the score maps are model ids
 *  ("dixon_coles", "blend", "market", "baseline", ...). */
export interface BacktestReport {
  seasons: [string, string];
  matches: number;
  result: Record<string, ModelScore>;
  goals: Record<string, ModelScore>;
  result_vs_market: Record<string, Interval>;
  goals_vs_market: Record<string, Interval>;
  calibration: { blend: CalibrationBin[]; market: CalibrationBin[] };
  by_season: { season: string; matches: number; blend: number; market: number }[];
  weights: { result: Record<string, number>; goals: Record<string, number> };
}

export interface SeasonGame {
  date: string;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  p_home: number;
  p_draw: number;
  p_away: number;
  p_result: number;
  correct: boolean;
}

export interface SeasonRecord {
  season: string;
  matches: number;
  correct: number;
  log_loss: number | null;
  games: SeasonGame[];
}

export interface PerformanceResponse {
  backtest: BacktestReport | null;
  season: SeasonRecord;
}

// ---- league table ----

export interface TableRow {
  position: number;
  team: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  points: number;
}

/** Averages over the simulated seasons, so points and goals are decimals. */
export interface PredictedRow {
  position: number;
  current_position: number;
  team: string;
  played: number;
  points: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  average_position: number;
  position_low: number;      // the middle 90% of simulations finish between
  position_high: number;     // these two positions
  p_title: number;
  p_top4: number;
  p_relegation: number;
}

export interface TableResponse {
  season: string;
  results_to: string;
  matches_played: number;
  matches_remaining: number;
  simulations: number;
  current: TableRow[];
  predicted: PredictedRow[];
}
