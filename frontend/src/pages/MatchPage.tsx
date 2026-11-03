import { Fragment, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getBoard } from "../api/client";
import { useCart, legKey, type CartLeg } from "../cart/useCart";
import type { MatchBoardResponse, SelectionPrice } from "../api/types";
import { TeamBadge, shortDate, pct, sastTime, shortTeam } from "../lib/ui";
import { Spotlight, useCountUp, useMagnetic } from "../lib/fx";
import Pitch from "./Pitch";

export default function MatchPage() {
  const { matchId } = useParams();
  const navigate = useNavigate();
  const id = Number(matchId);
  const backRef = useMagnetic<HTMLButtonElement>(0.3);

  const { data, isLoading, error } = useQuery({
    queryKey: ["board", id],
    queryFn: () => getBoard(id),
    enabled: Number.isFinite(id),
    refetchInterval: 60_000, // auto-pick up re-pricing
    refetchOnWindowFocus: true,
  });

  if (isLoading) return <p className="text-muted text-sm py-16 text-center animate-pulse">Loading match…</p>;
  if (error || !data) {
    return (
      <div className="rounded-2xl border border-bad/40 bg-bad/10 p-6 text-center">
        <p className="text-bad font-semibold">Failed to load match</p>
        <p className="text-muted text-sm mt-1">{String(error)}</p>
        <Link to="/" className="text-accent text-sm mt-3 inline-block">← back to games</Link>
      </div>
    );
  }

  const prob = (sel: string) =>
    data.prices.find((p) => p.market === "1x2" && p.selection === sel)?.model_p ?? null;
  const ph = prob("home");
  const pd = prob("draw");
  const pa = prob("away");

  const resultPrices = data.prices.filter((p) => p.market === "1x2");
  const dcPrices = data.prices.filter((p) => p.market === "dc");
  const ouPrices = data.prices.filter((p) => p.market.startsWith("ou_"));

  return (
    <div className="animate-fade-up">
      <button
        ref={backRef}
        onClick={() => navigate(-1)}
        className="magnetic group inline-flex items-center gap-2 rounded-full border border-glass-border bg-glass hover:bg-glass-hover hover:border-glass-border-strong pl-2.5 pr-4 py-1.5 text-sm text-muted hover:text-white transition mb-3"
      >
        <span className="grid place-items-center w-5 h-5 rounded-full bg-white/10 group-hover:bg-accent/20 group-hover:text-accent group-hover:-translate-x-0.5 transition text-xs">←</span>
        All games
      </button>

      {/* Hero */}
      <Spotlight tilt tiltMax={3} className="rounded-3xl border border-glass-border bg-glass-strong p-5 sm:p-6 overflow-hidden shadow-glow">
        <div className="relative">
          <div className="text-[11px] uppercase tracking-[0.18em] text-dim text-center mb-4">
            {shortDate(data.date)}
            {data.kickoff_ts && <> · {sastTime(data.kickoff_ts)} SAST</>} · World Cup
          </div>
          <div className="flex items-center justify-between gap-3">
            <TeamSide team={data.home_team} accent="home" />
            <div className="shrink-0 text-center px-2">
              <div className="text-dim text-xs font-semibold mb-1">VS</div>
              {data.exp_home_goals != null && data.exp_away_goals != null && (
                <div className="num text-[11px] text-muted whitespace-nowrap">
                  xG {data.exp_home_goals.toFixed(2)}–{data.exp_away_goals.toFixed(2)}
                </div>
              )}
            </div>
            <TeamSide team={data.away_team} accent="away" reverse />
          </div>

          {ph != null && pd != null && pa != null && (
            <WinProbBar home={ph} draw={pd} away={pa} homeTeam={data.home_team} awayTeam={data.away_team} />
          )}
        </div>
      </Spotlight>

      {/* Lineups pitch — md+ only (hidden on phones) */}
      <Pitch matchId={data.match_id} />

      {data.prices.length === 0 ? (
        <p className="text-muted text-sm py-12 text-center">No model prediction for this game yet.</p>
      ) : (
        <div className="mt-5 space-y-5">
          {resultPrices.length > 0 && (
            <MarketSection title="Match result" prices={resultPrices} board={data} cols={3} />
          )}
          {dcPrices.length > 0 && (
            <MarketSection title="Double chance" prices={dcPrices} board={data} cols={3} />
          )}
          {ouPrices.length > 0 && <OverUnderSection prices={ouPrices} board={data} />}
        </div>
      )}

      <p className="text-[11px] text-muted mt-6 leading-relaxed">
        <b className="text-dim">Fair odds</b> = 1 ÷ the model's probability. These are our models' own
        numbers — no bookmaker odds. Tick any picks to combine them in the slip below.
      </p>
    </div>
  );
}

function TeamSide({ team, accent, reverse }: { team: string; accent: "home" | "away"; reverse?: boolean }) {
  return (
    <div className={`flex-1 min-w-0 flex flex-col items-center gap-2 ${reverse ? "" : ""}`}>
      <div
        className={`rounded-2xl p-0.5 transition-transform duration-300 hover:scale-105 ${
          accent === "home" ? "bg-home/20 shadow-[0_0_28px_-8px_#50a5b1]" : "bg-away/20 shadow-[0_0_28px_-8px_#f1600d]"
        }`}
      >
        <TeamBadge team={team} size={52} />
      </div>
      <div className="font-bold text-center leading-tight text-sm sm:text-base break-words max-w-full">
        {shortTeam(team)}
      </div>
    </div>
  );
}

function WinProbBar({
  home, draw, away, homeTeam, awayTeam,
}: { home: number; draw: number; away: number; homeTeam: string; awayTeam: string }) {
  const total = home + draw + away || 1;
  const h = (home / total) * 100;
  const d = (draw / total) * 100;
  const a = (away / total) * 100;

  // spring-fill from the centre outward on mount
  const [filled, setFilled] = useState(false);
  useEffect(() => {
    const t = requestAnimationFrame(() => setFilled(true));
    return () => cancelAnimationFrame(t);
  }, []);

  const ch = useCountUp(home, filled);
  const cd = useCountUp(draw, filled);
  const ca = useCountUp(away, filled);
  const ease = "cubic-bezier(0.16,1,0.3,1)";

  return (
    <div className="mt-5">
      <div className="flex h-3 rounded-full overflow-hidden ring-1 ring-white/10 bg-white/5">
        <div
          className="bg-home transition-[width] duration-700"
          style={{ width: filled ? `${h}%` : "0%", transitionTimingFunction: ease }}
        />
        <div
          className="bg-white/25 transition-[width] duration-700"
          style={{ width: filled ? `${d}%` : "0%", transitionTimingFunction: ease, transitionDelay: "60ms" }}
        />
        <div
          className="bg-away transition-[width] duration-700"
          style={{ width: filled ? `${a}%` : "0%", transitionTimingFunction: ease, transitionDelay: "120ms" }}
        />
      </div>
      <div className="flex justify-between items-baseline gap-2 mt-2 text-[11px]">
        <span className="flex items-baseline gap-1 min-w-0 flex-1">
          <span className="text-home font-semibold truncate">{shortTeam(homeTeam)}</span>
          <span className="num text-home shrink-0">{pct(ch)}</span>
        </span>
        <span className="text-muted num shrink-0">Draw {pct(cd)}</span>
        <span className="flex items-baseline justify-end gap-1 min-w-0 flex-1">
          <span className="text-away font-semibold truncate">{shortTeam(awayTeam)}</span>
          <span className="num text-away shrink-0">{pct(ca)}</span>
        </span>
      </div>
    </div>
  );
}

function MarketSection({
  title, prices, board, cols,
}: { title: string; prices: SelectionPrice[]; board: MatchBoardResponse; cols: number }) {
  return (
    <section className="rounded-2xl border border-glass-border bg-glass p-4">
      <h2 className="text-[11px] uppercase tracking-[0.16em] text-dim mb-3">{title}</h2>
      <div
        className="grid gap-2"
        style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
      >
        {prices.map((p) => (
          <PriceButton key={`${p.market}:${p.selection}`} price={p} board={board} />
        ))}
      </div>
    </section>
  );
}

/** Total goals laid out as two columns — every Over on the left, every Under on
 *  the right, lines aligned row-by-row (not jumbled). */
function OverUnderSection({ prices, board }: { prices: SelectionPrice[]; board: MatchBoardResponse }) {
  const lines = [...new Set(prices.map((p) => p.market))].sort();
  return (
    <section className="rounded-2xl border border-glass-border bg-glass p-4">
      <h2 className="text-[11px] uppercase tracking-[0.16em] text-dim mb-3">Total goals — over / under</h2>
      <div className="grid grid-cols-[1fr_2.5rem_1fr] gap-x-2 gap-y-2 items-center">
        <div className="text-center text-[10px] uppercase tracking-wider text-pick font-semibold">Over</div>
        <div />
        <div className="text-center text-[10px] uppercase tracking-wider text-amber font-semibold">Under</div>
        {lines.map((mkt) => {
          const over = prices.find((p) => p.market === mkt && p.selection === "over");
          const under = prices.find((p) => p.market === mkt && p.selection === "under");
          const line = mkt.slice(3).replace("_", ".");
          return (
            <Fragment key={mkt}>
              {over ? <PriceButton price={over} board={board} compact /> : <div />}
              <div className="num text-center text-sm font-bold text-dim">{line}</div>
              {under ? <PriceButton price={under} board={board} compact /> : <div />}
            </Fragment>
          );
        })}
      </div>
    </section>
  );
}

function PriceButton({
  price, board, compact,
}: { price: SelectionPrice; board: MatchBoardResponse; compact?: boolean }) {
  const { has, toggle } = useCart();
  const key = legKey(board.match_id, price.market, price.selection);
  const selected = has(key);
  const odds = useCountUp(price.fair_odds, true, 650);

  const leg: CartLeg = {
    key,
    matchId: board.match_id,
    matchLabel: `${board.home_team} vs ${board.away_team}`,
    market: price.market,
    selection: price.selection,
    selectionLabel: price.selection_label,
    modelP: price.model_p,
    fairOdds: price.fair_odds,
  };

  return (
    <Spotlight
      as="button"
      onClick={() => toggle(leg)}
      className={`group flex flex-col items-start rounded-xl border px-3 py-2.5 text-left transition-[transform,background-color,border-color] duration-150 active:scale-[0.97] ${
        selected
          ? "border-pick/50 bg-pick/15 shadow-pick"
          : "border-glass-border bg-glass-strong hover:bg-glass-hover hover:border-glass-border-strong"
      }`}
    >
      <div className="flex items-center justify-between w-full">
        <span className="text-xs font-medium truncate pr-1">
          {compact ? (price.selection === "over" ? "Over" : "Under") : price.selection_label}
        </span>
        <span
          className={`shrink-0 grid place-items-center w-4 h-4 rounded-full text-[10px] transition ${
            selected ? "bg-pick text-black scale-100" : "bg-white/5 text-transparent group-hover:text-dim"
          }`}
        >
          ✓
        </span>
      </div>
      <div className="flex items-baseline justify-between w-full mt-1.5">
        <span className={`num text-lg font-extrabold tabular-nums ${selected ? "text-pick" : ""}`}>
          {odds.toFixed(2)}
        </span>
        <span className="num text-[11px] text-muted">{pct(price.model_p, 1)}</span>
      </div>
    </Spotlight>
  );
}
