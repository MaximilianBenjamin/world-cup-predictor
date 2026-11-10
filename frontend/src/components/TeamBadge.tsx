import type { Competition } from "../api/types";
import { club, isLight } from "../lib/clubs";
import { flag } from "../lib/flags";

/** Team badge. Clubs get a square in their main colour with a stripe of
 *  their second colour along the bottom and their code on top; national teams get their flag. */
export default function TeamBadge({
  team, competition = "epl", size = 36,
}: { team: string; competition?: Competition; size?: number }) {
  if (competition === "wc") {
    return (
      <span
        className="inline-grid place-items-center bg-slab border border-line shrink-0"
        style={{ width: size, height: size, fontSize: size * 0.58 }}
        aria-hidden
      >
        {flag(team) ?? team.slice(0, 2).toUpperCase()}
      </span>
    );
  }
  const c = club(team);
  return (
    <span
      className="inline-grid place-items-center shrink-0 font-cond font-bold border border-black/40"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.36,
        letterSpacing: "0.02em",
        background: `linear-gradient(180deg, ${c.a} 0 80%, ${c.b} 80% 100%)`,
        paddingBottom: size * 0.16,
        color: isLight(c.a) ? "#0a0a0b" : "#ffffff",
      }}
      aria-hidden
    >
      {c.code}
    </span>
  );
}
