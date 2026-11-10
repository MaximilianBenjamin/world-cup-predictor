import { Fragment } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { getBoard } from "../api/client";
import { useCart, legKey, type CartLeg } from "../cart/useCart";
import type { Competition, MatchBoardResponse, SelectionPrice } from "../api/types";
import { COMPETITION_NAME, shortDate, pct, sastTime, teamName } from "../lib/ui";
import TeamBadge from "../components/TeamBadge";
import Pitch from "./Pitch";

export default function MatchPage() {
  const { matchId } = useParams();
  const id = Number(matchId);

  const { data, isLoading, error } = useQuery({
    queryKey: ["board", id],
    queryFn: () => getBoard(id),
    enabled: Number.isFinite(id),
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  });

  if (isLoading) return <p className="label text-dust py-16 text-center">Loading match</p>;
  if (error || !data) {
    return (
      <div className="panel p-6">
        <p className="font-semibold">Could not load this match.</p>
        {error && <p className="text-dust text-sm mt-1">{String(error)}</p>}
        <Link to="/" className="label text-red-hot mt-4 inline-block">← Fixtures</Link>
      </div>
    );
  }

  const c = data.competition;
  const prob = (sel: string) =>
    data.prices.find((p) => p.market === "1x2" && p.selection === sel)?.model_p ?? null;
  const ph = prob("home");
  const pd = prob("draw");
  const pa = prob("away");
  const played = data.completed && data.home_score != null && data.away_score != null;

  const resultPrices = data.prices.filter((p) => p.market === "1x2");
  const dcPrices = data.prices.filter((p) => p.market === "dc");
  const ouPrices = data.prices.filter((p) => p.market.startsWith("ou_"));

  return (
    <div>
      <Link
        to={c === "wc" ? "/world-cup" : "/"}
        className="label text-dust hover:text-chalk inline-block mb-4"
      >
        ← {COMPETITION_NAME[c]} fixtures
      </Link>

      <section className="panel p-5 sm:p-8">
        <p className="label text-dust text-center mb-6">
          {COMPETITION_NAME[c]} · {shortDate(data.kickoff_ts ?? data.date)}
          {data.kickoff_ts && <> · {sastTime(data.kickoff_ts)} SAST</>}
        </p>

        <div className="grid grid-cols-[1fr_auto_1fr] items-start gap-3 sm:gap-6">
          <TeamSide team={data.home_team} competition={c} side="Home" />
          <div className="text-center pt-3 sm:pt-5">
            {played ? (
              <div className="headline text-5xl sm:text-7xl whitespace-nowrap">
                {data.home_score}<span className="text-red">–</span>{data.away_score}
              </div>
            ) : (
              <div className="headline text-3xl sm:text-5xl text-red">v</div>
            )}
          </div>
          <TeamSide team={data.away_team} competition={c} side="Away" />
        </div>

        {ph != null && pd != null && pa != null && (
          <ResultBar
            home={ph} draw={pd} away={pa}
            homeTeam={teamName(data.home_team, c)} awayTeam={teamName(data.away_team, c)}
          />
        )}

        {data.exp_home_goals != null && data.exp_away_goals != null && (
          <p className="num text-center text-dust mt-5">
            Expected goals{" "}
            <span className="text-chalk font-bold">
              {data.exp_home_goals.toFixed(2)} – {data.exp_away_goals.toFixed(2)}
            </span>
          </p>
        )}
      </section>

      <Pitch matchId={data.match_id} competition={c} />

      {data.prices.length === 0 ? (
        <p className="panel p-8 text-dust mt-6">The model has not priced this match yet.</p>
      ) : (
        <div className="mt-6 space-y-6">
          {resultPrices.length > 0 && (
            <MarketSection title="Match result" prices={resultPrices} board={data} />
          )}
          {dcPrices.length > 0 && (
            <MarketSection title="Double chance" prices={dcPrices} board={data} />
          )}
          {ouPrices.length > 0 && <OverUnderSection prices={ouPrices} board={data} />}
        </div>
      )}

      <p className="text-sm text-dust mt-6 max-w-2xl">
        The large number is the fair price: 1 divided by the model's probability, shown beside it.
        Select two or more prices to see what they come to combined.
      </p>
    </div>
  );
}

function TeamSide({
  team, competition, side,
}: { team: string; competition: Competition; side: string }) {
  return (
    <div className="flex flex-col items-center gap-3 min-w-0 text-center">
      <TeamBadge team={team} competition={competition} size={64} />
      <div className="min-w-0 max-w-full">
        <div className="headline text-2xl sm:text-4xl break-words">{teamName(team, competition)}</div>
        <div className="label text-dust mt-1.5">{side}</div>
      </div>
    </div>
  );
}

/** One bar split three ways: home, draw, away. */
function ResultBar({
  home, draw, away, homeTeam, awayTeam,
}: { home: number; draw: number; away: number; homeTeam: string; awayTeam: string }) {
  const total = home + draw + away || 1;
  const parts = [
    { label: homeTeam, p: home, bar: "bg-red", align: "text-left" },
    { label: "Draw", p: draw, bar: "bg-dust/60", align: "text-center" },
    { label: awayTeam, p: away, bar: "bg-chalk", align: "text-right" },
  ];
  return (
    <div className="mt-8">
      <div className="flex h-3 gap-0.5" role="img"
           aria-label={`${homeTeam} ${pct(home)}, draw ${pct(draw)}, ${awayTeam} ${pct(away)}`}>
        {parts.map((s) => (
          <div key={s.label} className={s.bar} style={{ width: `${(s.p / total) * 100}%` }} />
        ))}
      </div>
      <div className="grid grid-cols-3 gap-2 mt-2">
        {parts.map((s) => (
          <div key={s.label} className={`min-w-0 ${s.align}`}>
            <div className="num text-2xl font-bold leading-tight">{pct(s.p)}</div>
            <div className="label text-dust truncate">{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MarketSection({
  title, prices, board,
}: { title: string; prices: SelectionPrice[]; board: MatchBoardResponse }) {
  return (
    <section>
      <h2 className="label text-chalk text-sm border-b border-line pb-2 mb-3">{title}</h2>
      <div className="grid grid-cols-3 gap-2">
        {prices.map((p) => (
          <PriceButton key={`${p.market}:${p.selection}`} price={p} board={board} />
        ))}
      </div>
    </section>
  );
}

/** Total goals in two columns, over on the left and under on the right, one
 *  row per line. */
function OverUnderSection({ prices, board }: { prices: SelectionPrice[]; board: MatchBoardResponse }) {
  const lines = [...new Set(prices.map((p) => p.market))].sort();
  return (
    <section>
      <h2 className="label text-chalk text-sm border-b border-line pb-2 mb-3">Total goals</h2>
      <div className="grid grid-cols-[1fr_3rem_1fr] gap-2 items-center">
        {lines.map((mkt) => {
          const over = prices.find((p) => p.market === mkt && p.selection === "over");
          const under = prices.find((p) => p.market === mkt && p.selection === "under");
          return (
            <Fragment key={mkt}>
              {over ? <PriceButton price={over} board={board} label="Over" /> : <div />}
              <div className="num text-center text-xl font-bold text-dust">
                {mkt.slice(3).replace("_", ".")}
              </div>
              {under ? <PriceButton price={under} board={board} label="Under" /> : <div />}
            </Fragment>
          );
        })}
      </div>
    </section>
  );
}

function PriceButton({
  price, board, label,
}: { price: SelectionPrice; board: MatchBoardResponse; label?: string }) {
  const { has, toggle } = useCart();
  const key = legKey(board.match_id, price.market, price.selection);
  const selected = has(key);
  const c = board.competition;

  const leg: CartLeg = {
    key,
    matchId: board.match_id,
    matchLabel: `${teamName(board.home_team, c)} v ${teamName(board.away_team, c)}`,
    market: price.market,
    selection: price.selection,
    selectionLabel: price.selection_label,
    modelP: price.model_p,
    fairOdds: price.fair_odds,
  };

  return (
    <button
      onClick={() => toggle(leg)}
      aria-pressed={selected}
      className={`text-left px-3 py-2.5 border transition-colors min-w-0 ${
        selected
          ? "border-gold bg-gold text-ink"
          : "border-line bg-slab hover:border-dust"
      }`}
    >
      <div className={`label truncate ${selected ? "text-ink" : "text-dust"}`}>
        {label ?? price.selection_label}
      </div>
      <div className="flex items-baseline justify-between gap-2 mt-1">
        <span className="num text-2xl font-bold leading-none">{price.fair_odds.toFixed(2)}</span>
        <span className={`num text-sm ${selected ? "text-ink" : "text-dust"}`}>
          {pct(price.model_p, 1)}
        </span>
      </div>
    </button>
  );
}
