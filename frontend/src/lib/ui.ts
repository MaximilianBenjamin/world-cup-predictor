import type { Competition } from "../api/types";
import { club } from "./clubs";

export type { Competition };

export const COMPETITION_NAME: Record<Competition, string> = {
  epl: "Premier League",
  wc: "World Cup",
};

export function shortDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
}

export function dayKey(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const today = new Date();
  const tomorrow = new Date();
  tomorrow.setDate(today.getDate() + 1);
  const same = (a: Date, b: Date) => a.toDateString() === b.toDateString();
  if (same(d, today)) return "Today";
  if (same(d, tomorrow)) return "Tomorrow";
  return d.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
}

export function pct(p: number, digits = 0): string {
  return `${(p * 100).toFixed(digits)}%`;
}

const SHORT_COUNTRIES: Record<string, string> = {
  "Bosnia and Herzegovina": "Bosnia",
  "United Arab Emirates": "UAE",
  "Trinidad and Tobago": "Trinidad",
  "Republic of Ireland": "Ireland",
  "United States": "USA",
};

/** The name to print for a team: full club name, or a country trimmed to fit. */
export function teamName(team: string, competition: Competition = "epl"): string {
  return competition === "epl" ? club(team).name : (SHORT_COUNTRIES[team] ?? team);
}

/** Three-letter code, for tight spaces. */
export function teamCode(team: string, competition: Competition = "epl"): string {
  return competition === "epl" ? club(team).code : team.slice(0, 3).toUpperCase();
}

// ---- South African time (SAST = Africa/Johannesburg, UTC+2) ----
// kickoff_ts arrives as UTC ISO; a value with no zone marker is assumed UTC.
const SAST = "Africa/Johannesburg";

function toUtcDate(iso?: string | null): Date | null {
  if (!iso) return null;
  let s = iso.trim().replace(" ", "T");
  if (!/[zZ]|[+-]\d\d:?\d\d$/.test(s)) s += "Z";
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "19:00": kickoff time of day in SAST. */
export function sastTime(iso?: string | null): string {
  const d = toUtcDate(iso);
  if (!d) return "";
  return d.toLocaleTimeString("en-ZA", {
    timeZone: SAST, hour: "2-digit", minute: "2-digit", hour12: false,
  });
}

/** "Tue 18:00": a moment in SAST, shifted by `offsetMin` minutes. */
export function sastMoment(iso?: string | null, offsetMin = 0): string {
  const d = toUtcDate(iso);
  if (!d) return "";
  const shifted = new Date(d.getTime() + offsetMin * 60_000);
  return shifted.toLocaleString("en-ZA", {
    timeZone: SAST, weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false,
  });
}
