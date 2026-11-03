import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getLineups } from "../api/client";
import type { LineupPlayer, LineupSide } from "../api/types";
import { flag } from "../lib/flags";
import { sastTime, sastMoment, shortTeam } from "../lib/ui";

/** True on tablet/desktop (≥768px). Drives whether we even mount the pitch —
 *  on phones we render nothing AND skip the lineups request, so the smaller
 *  screen does zero extra work. */
function useIsDesktop(): boolean {
  const q = "(min-width: 768px)";
  const [isDesktop, setIsDesktop] = useState(
    () => typeof window !== "undefined" && window.matchMedia(q).matches,
  );
  useEffect(() => {
    const m = window.matchMedia(q);
    const handler = () => setIsDesktop(m.matches);
    m.addEventListener("change", handler);
    return () => m.removeEventListener("change", handler);
  }, []);
  return isDesktop;
}

/** Football pitch with both confirmed XIs. Desktop/tablet only. Lineups publish
 *  ~1h before kickoff; until then we show a placeholder with the SAST time. */
export default function Pitch({ matchId }: { matchId: number }) {
  const isDesktop = useIsDesktop();

  const { data } = useQuery({
    queryKey: ["lineups", matchId],
    queryFn: () => getLineups(matchId),
    enabled: isDesktop, // never fetch on phones
    staleTime: 60_000,
    refetchInterval: isDesktop ? 180_000 : false,
  });

  if (!isDesktop || !data) return null;

  return (
    <section className="mt-5">
      <div className="flex items-center justify-between mb-2.5">
        <h2 className="text-[11px] uppercase tracking-[0.16em] text-dim">Starting lineups</h2>
        {data.available && (
          <span className="text-[11px] text-pick flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-pick" /> confirmed XI
          </span>
        )}
      </div>

      {data.available && data.home && data.away ? (
        <PitchBoard home={data.home} away={data.away} />
      ) : (
        <LineupPlaceholder kickoff={data.kickoff_ts} />
      )}
    </section>
  );
}

function LineupPlaceholder({ kickoff }: { kickoff: string | null }) {
  const drop = sastMoment(kickoff, -60); // ESPN publishes XIs ~1h before KO
  const ko = sastTime(kickoff);
  return (
    <div className="rounded-2xl border border-glass-border bg-glass p-8 text-center">
      <div className="text-3xl mb-2">📋</div>
      <p className="text-sm text-muted">
        Confirmed lineups drop about an hour before kickoff
        {drop && (
          <> — check back around <span className="text-cream font-medium">{drop} SAST</span></>
        )}
        .
      </p>
      {ko && <p className="text-[11px] text-dim mt-1">Kickoff {ko} SAST</p>}
    </div>
  );
}

// ---- role-based placement -------------------------------------------------
// ESPN's roster order is NOT row-order, so place each starter by its position
// abbreviation ("CD-L", "LB", "DM", "CM-R", "LF" …): a depth tier (how far up
// the pitch) and a lateral offset (left↔right).

function roleOf(pos: string | null): { depth: number; lateral: number } {
  if (!pos) return { depth: 3, lateral: 0 };
  const up = pos.toUpperCase();
  const [base, suffix] = up.split("-");

  let depth = 3; // default: central midfield band
  if (base === "G" || base === "GK") depth = 0;
  else if (/^(F|ST|CF|SS|RW|LW|RF|LF|W)$/.test(base)) depth = 5;
  else if (base.includes("AM")) depth = 4;
  else if (base.includes("DM")) depth = 2;
  else if (base.includes("M")) depth = 3;
  else if (base.includes("B") || base.includes("CD") || base.includes("CB") || base === "D" || base === "SW")
    depth = 1;

  let lateral = 0;
  if (suffix === "L") lateral = -1;
  else if (suffix === "R") lateral = 1;
  if (/^L/.test(base)) lateral = -2; // LB, LM, LW, LF, LWB
  else if (/^R/.test(base)) lateral = 2; // RB, RM, RW, RF, RWB
  return { depth, lateral };
}

/** Map each starter to an (x,y) %. `side` mirrors the layout: home attacks
 *  right (GK far left), away attacks left (GK far right). */
function placements(lineup: LineupSide, side: "home" | "away") {
  const starters = lineup.starters.slice(0, 11);
  const byDepth = new Map<number, { p: LineupPlayer; lat: number }[]>();
  for (const p of starters) {
    const { depth, lateral } = roleOf(p.position);
    if (!byDepth.has(depth)) byDepth.set(depth, []);
    byDepth.get(depth)!.push({ p, lat: lateral });
  }

  const spots: { x: number; y: number; p: LineupPlayer }[] = [];
  for (const [depth, group] of byDepth) {
    group.sort((a, b) => a.lat - b.lat || a.p.slot - b.p.slot);
    const n = group.length;
    const t = depth / 5; // 0 (goal line) → 1 (midfield)
    const x = side === "home" ? 3 + t * 44 : 97 - t * 44;
    group.forEach(({ p }, i) => {
      spots.push({ x, y: ((i + 1) / (n + 1)) * 100, p });
    });
  }
  return spots;
}

function PitchBoard({ home, away }: { home: LineupSide; away: LineupSide }) {
  const spots = [
    ...placements(home, "home").map((s) => ({ ...s, side: "home" as const })),
    ...placements(away, "away").map((s) => ({ ...s, side: "away" as const })),
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-2 text-sm">
        <span className="flex items-center gap-2 font-semibold min-w-0">
          <span className="w-2.5 h-2.5 rounded-full bg-home shrink-0" />
          <span className="truncate">{flag(home.team)} {shortTeam(home.team)}</span>
          {home.formation && <span className="text-dim text-xs num shrink-0">· {home.formation}</span>}
        </span>
        <span className="flex items-center gap-2 font-semibold min-w-0 justify-end">
          {away.formation && <span className="text-dim text-xs num shrink-0">{away.formation} ·</span>}
          <span className="truncate">{shortTeam(away.team)} {flag(away.team)}</span>
          <span className="w-2.5 h-2.5 rounded-full bg-away shrink-0" />
        </span>
      </div>

      <div
        className="relative w-full rounded-2xl overflow-hidden ring-1 ring-white/10"
        style={{
          aspectRatio: "16 / 9",
          background: "repeating-linear-gradient(90deg, #15803d 0 8%, #166b36 8% 16%)",
        }}
      >
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 bottom-0 left-1/2 w-px bg-white/25" />
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[16%] aspect-square rounded-full border border-white/25" />
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-white/30" />
          <div className="absolute top-1/2 -translate-y-1/2 left-0 h-[44%] w-[14%] border-y border-r border-white/25" />
          <div className="absolute top-1/2 -translate-y-1/2 right-0 h-[44%] w-[14%] border-y border-l border-white/25" />
          <div className="absolute inset-0 border border-white/15 rounded-2xl" />
        </div>

        {spots.map(({ x, y, p, side }) => (
          <PlayerChip key={`${side}-${p.slot}-${p.name}`} x={x} y={y} player={p} side={side} />
        ))}
      </div>
    </div>
  );
}

function lastName(name: string): string {
  const parts = name.split(/\s+/);
  return parts.length > 1 ? parts[parts.length - 1] : name;
}

function PlayerChip({
  x, y, player, side,
}: { x: number; y: number; player: LineupPlayer; side: "home" | "away" }) {
  return (
    <div
      className="absolute flex flex-col items-center gap-0.5 -translate-x-1/2 -translate-y-1/2"
      style={{ left: `${x}%`, top: `${y}%`, width: 64 }}
    >
      <div
        className={`grid place-items-center w-7 h-7 rounded-full text-[11px] font-extrabold text-white shadow-lg ring-2 ring-white/70 ${
          side === "home" ? "bg-home/90" : "bg-away/90"
        }`}
      >
        {player.shirt ?? ""}
      </div>
      <span className="num text-[10px] leading-tight text-center text-white drop-shadow-[0_1px_2px_rgba(0,0,0,0.9)] truncate w-full">
        {lastName(player.name)}
      </span>
    </div>
  );
}
