import { flag, monogram } from "./flags";

export function shortDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
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
  return d.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" });
}

export function pct(p: number, digits = 0): string {
  return `${(p * 100).toFixed(digits)}%`;
}

// A few national-team names are long enough to break a phone layout — show a
// tidy short form (the flag still identifies the country). Flag lookups use the
// full name, so only the displayed text changes.
const SHORT_NAMES: Record<string, string> = {
  "Bosnia and Herzegovina": "Bosnia",
  "United Arab Emirates": "UAE",
  "Trinidad and Tobago": "Trinidad",
  "Republic of Ireland": "Ireland",
  "Papua New Guinea": "Papua NG",
  "Democratic Republic of Congo": "DR Congo",
  "Central African Republic": "CAR",
  "Antigua and Barbuda": "Antigua",
  "São Tomé and Príncipe": "São Tomé",
  "United States": "USA",
};

export function shortTeam(name: string): string {
  return SHORT_NAMES[name] ?? name;
}

// ---- South African time (SAST = Africa/Johannesburg, UTC+2) ----
// kickoff_ts comes from the API as UTC ISO ("…+00:00"); older rows may be a
// naive "YYYY-MM-DD HH:MM" — assume UTC for those too.
const SAST = "Africa/Johannesburg";

function toUtcDate(iso?: string | null): Date | null {
  if (!iso) return null;
  let s = iso.trim().replace(" ", "T");
  if (!/[zZ]|[+-]\d\d:?\d\d$/.test(s)) s += "Z"; // no tz marker → assume UTC
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "19:00" — kickoff time of day in SAST. */
export function sastTime(iso?: string | null): string {
  const d = toUtcDate(iso);
  if (!d) return "";
  return d.toLocaleTimeString("en-ZA", {
    timeZone: SAST, hour: "2-digit", minute: "2-digit", hour12: false,
  });
}

/** "Tue 18:00" — a moment in SAST, optionally shifted by `offsetMin` minutes
 *  (e.g. -60 for "lineups drop ~1h before kickoff"). */
export function sastMoment(iso?: string | null, offsetMin = 0): string {
  const d = toUtcDate(iso);
  if (!d) return "";
  const shifted = new Date(d.getTime() + offsetMin * 60_000);
  return shifted.toLocaleString("en-ZA", {
    timeZone: SAST, weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false,
  });
}

/** Circular team crest: flag emoji where known, else a colour-tinted monogram. */
export function TeamBadge({ team, size = 34 }: { team: string; size?: number }) {
  const f = flag(team);
  if (f) {
    return (
      <span
        className="inline-grid place-items-center rounded-full bg-white/5 ring-1 ring-white/10 shrink-0"
        style={{ width: size, height: size, fontSize: size * 0.6 }}
        aria-hidden
      >
        {f}
      </span>
    );
  }
  // Deterministic hue from the name so the same team is always the same colour.
  let h = 0;
  for (let i = 0; i < team.length; i++) h = (h * 31 + team.charCodeAt(i)) % 360;
  return (
    <span
      className="inline-grid place-items-center rounded-full shrink-0 font-bold text-white ring-1 ring-white/15"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.32,
        background: `linear-gradient(135deg, hsl(${h} 55% 32%), hsl(${(h + 40) % 360} 55% 22%))`,
      }}
      aria-hidden
    >
      {monogram(team)}
    </span>
  );
}
