import axios from "axios";
import type {
  CombineLeg,
  CombineResponse,
  GamesResponse,
  LineupResponse,
  MatchBoardResponse,
} from "./types";

// In development Vite proxies /api to the backend on port 8001 (vite.config.ts).
// Set VITE_API_BASE_URL when the backend lives on another origin.
const baseURL = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api`
  : "/api";

const api = axios.create({ baseURL, timeout: 30_000 });

export async function getGames(includeCompleted = false): Promise<GamesResponse> {
  const r = await api.get<GamesResponse>("/games", {
    params: { include_completed: includeCompleted },
  });
  return r.data;
}

export async function getBoard(matchId: number): Promise<MatchBoardResponse> {
  const r = await api.get<MatchBoardResponse>(`/board/${matchId}`);
  return r.data;
}

export async function getLineups(matchId: number): Promise<LineupResponse> {
  const r = await api.get<LineupResponse>(`/lineups/${matchId}`);
  return r.data;
}

export async function postCombine(legs: CombineLeg[]): Promise<CombineResponse> {
  const r = await api.post<CombineResponse>("/combine", { legs });
  return r.data;
}
