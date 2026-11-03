import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getGames } from "../api/client";
import type { GameSummary } from "../api/types";
import { TeamBadge, dayKey, sastTime, shortTeam } from "../lib/ui";
import { Spotlight, useCountUp, useReveal } from "../lib/fx";

export default function SlatePage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["games"],
    queryFn: () => getGames(),
    refetchInterval: 60_000, // auto-pick up fixture/prediction refreshes
    refetchOnWindowFocus: true,
  });

  if (isLoading) {
    return <SkeletonSlate />;
  }
  if (error) {
    return (
      <div className="rounded-2xl border border-bad/40 bg-bad/10 p-6 text-center">
        <p className="text-bad font-semibold text-lg">Failed to load games</p>
        <p className="text-muted text-sm mt-1">{String(error)}</p>
      </div>
    );
  }

  const games = data?.games ?? [];

  // Group by day so the slate reads like a fixture list.
  const groups: { label: string; games: GameSummary[] }[] = [];
  for (const g of games) {
    const label = dayKey(g.date);
    const last = groups[groups.length - 1];
    if (last && last.label === label) last.games.push(g);
    else groups.push({ label, games: [g] });
  }

  let idx = 0;

  return (
    <div>
      <div className="flex items-end justify-between mb-7">
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em] text-accent/80 font-semibold mb-1.5">
            The Slate
          </p>
          <h1 className="kinetic text-4xl sm:text-6xl font-black tracking-tight leading-[0.95]">
            {"Upcoming games".split(" ").map((w, i) => (
              <span className="w mr-[0.25em]" key={w}>
                <span style={{ animationDelay: `${120 + i * 90}ms` }}>{w}</span>
              </span>
            ))}
          </h1>
          <p className="text-dim text-sm mt-2">
            Tap a game to see every market and build a slip.
          </p>
        </div>
        {data && (
          <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] text-muted rounded-full border border-glass-border bg-glass px-2.5 py-1 backdrop-blur-md">
            {data.model_name} <span className="text-dim">{data.model_version}</span>
          </span>
        )}
      </div>

      {games.length === 0 ? (
        <div className="rounded-2xl border border-glass-border bg-glass p-10 text-center">
          <div className="text-3xl mb-2">🏟️</div>
          <p className="text-muted text-sm">
            No upcoming games yet. Knockout fixtures appear here once both teams are confirmed.
          </p>
        </div>
      ) : (
        <div className="space-y-8">
          {groups.map((grp) => (
            <section key={grp.label}>
              <h2 className="text-[11px] uppercase tracking-[0.18em] text-dim mb-3 pl-1 flex items-center gap-2">
                <span className="w-1 h-1 rounded-full bg-accent" />
                {grp.label}
              </h2>
              <div className="grid sm:grid-cols-2 gap-3">
                {grp.games.map((g) => (
                  <GameCard key={g.match_id} game={g} index={idx++} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function GameCard({ game, index }: { game: GameSummary; index: number }) {
  const { ref, shown } = useReveal<HTMLDivElement>();
  const hasPick = game.has_prediction && !!game.pick_label;
  const p = game.pick_p ?? 0;
  const count = useCountUp(p * 100, shown && hasPick);

  return (
    <div
      ref={ref}
      className={`reveal ${shown ? "shown" : ""}`}
      style={{ transitionDelay: `${Math.min(index, 9) * 45}ms` }}
    >
      <Spotlight
        as={Link}
        tilt
        to={`/match/${game.match_id}`}
        className="group block rounded-2xl border border-glass-border bg-glass hover:border-glass-border-strong transition-[border-color,background-color] duration-200 p-4 hover:bg-glass-hover"
      >
        {game.kickoff_ts && (
          <div className="flex justify-center -mt-1 mb-2">
            <span className="num text-[11px] text-muted">{sastTime(game.kickoff_ts)} SAST</span>
          </div>
        )}

        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <TeamBadge team={game.home_team} />
            <span className="font-semibold truncate">{shortTeam(game.home_team)}</span>
          </div>
          <span className="text-dim text-[10px] font-bold shrink-0 px-1.5 py-0.5 rounded-md bg-white/5">
            VS
          </span>
          <div className="flex items-center gap-2 min-w-0 flex-1 flex-row-reverse text-right">
            <TeamBadge team={game.away_team} />
            <span className="font-semibold truncate">{shortTeam(game.away_team)}</span>
          </div>
        </div>

        {hasPick ? (
          <div className="fx-tz mt-4 pt-3 border-t border-glass-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-[10px] uppercase tracking-wider text-dim shrink-0">Pick</span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-pick/15 ring-1 ring-pick/30 px-2.5 py-1 text-pick text-sm font-semibold truncate max-w-full group-hover:shadow-pick transition-shadow">
                  {shortTeam(game.pick_label!)}
                </span>
              </div>
              <div className="text-right shrink-0 ml-2">
                <div className="num text-sm font-bold tabular-nums">{count.toFixed(0)}%</div>
                <div className="num text-[11px] text-muted">
                  fair {game.pick_fair_odds?.toFixed(2)}
                </div>
              </div>
            </div>
            {/* confidence micro-bar */}
            <div className="mt-2.5 h-1 rounded-full bg-white/5 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-pick/70 to-pick transition-[width] duration-700 ease-out"
                style={{ width: shown ? `${Math.min(100, p * 100)}%` : "0%" }}
              />
            </div>
          </div>
        ) : (
          <div className="mt-4 pt-3 border-t border-glass-border text-xs text-muted">No pick yet</div>
        )}
      </Spotlight>
    </div>
  );
}

function SkeletonSlate() {
  return (
    <div className="space-y-3">
      <div className="h-9 w-56 rounded-lg bg-glass animate-pulse mb-7" />
      <div className="grid sm:grid-cols-2 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="relative h-32 rounded-2xl bg-glass border border-glass-border overflow-hidden"
          >
            <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/5 to-transparent" />
          </div>
        ))}
      </div>
    </div>
  );
}
