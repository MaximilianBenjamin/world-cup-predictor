import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getPerformance } from "../api/client";
import type {
  BacktestReport, CalibrationBin, Interval, ModelScore, SeasonRecord,
} from "../api/types";
import { pct, shortDate, teamName } from "../lib/ui";

const MODEL_NAME: Record<string, string> = {
  market: "Bookmakers' closing odds",
  blend: "Weighted blend",
  mean: "Plain average",
  dixon_coles: "Dixon-Coles",
  form_xgb: "XGBoost on form and shots",
  catboost_pi: "CatBoost on pi-ratings",
  elo_lgbm: "LightGBM on Elo and form",
  goals_xgb: "Poisson XGBoost",
  gap_sot: "GAP ratings on shots on target",
  gap_shots: "GAP ratings on shots",
  gap_corners: "GAP ratings on corners",
  baseline: "Baseline: long-run frequencies",
};

// Chart colours: the model in red, the bookmakers as the neutral reference.
const MODEL_COLOUR = "#ff3b45";
const MARKET_COLOUR = "#f3efe6";
const GRID = "#2c2c31";
const AXIS_TEXT = "#9b978d";

const f3 = (x: number) => x.toFixed(3);
const signed = (x: number) => `${x >= 0 ? "+" : "−"}${Math.abs(x).toFixed(3)}`;

export default function PerformancePage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["performance"],
    queryFn: getPerformance,
    staleTime: 5 * 60_000,
  });

  return (
    <div>
      <header className="mb-8">
        <p className="label text-red-hot mb-3">The record</p>
        <h1 className="headline text-6xl sm:text-8xl">
          Model <span className="text-red">v</span> bookmakers
        </h1>
        <div className="tape mt-5 max-w-xs" />
      </header>

      {isLoading && <p className="label text-dust py-16 text-center">Loading the record</p>}
      {error && (
        <div className="panel p-6">
          <p className="font-semibold">Could not load the record.</p>
          <p className="text-dust text-sm mt-1">{String(error)}</p>
        </div>
      )}

      {data && (
        <div className="space-y-12">
          {data.backtest
            ? <Backtest report={data.backtest} />
            : <p className="panel p-6 text-dust">The backtest has not been run on this server.</p>}
          <ThisSeason record={data.season} />
        </div>
      )}
    </div>
  );
}

function Backtest({ report }: { report: BacktestReport }) {
  const blend = report.result.blend;
  const market = report.result.market;
  const gap = report.result_vs_market.blend;
  const seasonsAhead = report.by_season.filter((s) => s.blend < s.market).length;

  return (
    <>
      <section>
        <p className="text-lg max-w-2xl">
          The model is less accurate than the bookmakers. Over{" "}
          <span className="num font-bold">{report.matches.toLocaleString("en-GB")}</span> Premier
          League matches from {report.seasons[0]} to {report.seasons[1]}, each predicted using only
          earlier matches, it scored better than the closing odds in{" "}
          <span className="num font-bold">{seasonsAhead}</span> of{" "}
          <span className="num font-bold">{report.by_season.length}</span> seasons.
        </p>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-6">
          <Tile label="Model log loss" value={f3(blend.log_loss.value)} note="lower is better" />
          <Tile label="Bookmakers log loss" value={f3(market.log_loss.value)} note="closing odds, margin removed" />
          <Tile label="Gap" value={signed(gap.value)} accent
                note={`95% interval ${signed(gap.low)} to ${signed(gap.high)}`} />
          <Tile label="Right result" value={pct(blend.accuracy.value)}
                note={`bookmakers ${pct(market.accuracy.value)}`} />
        </div>
      </section>

      <SeasonGaps seasons={report.by_season} />

      <ScoreTable
        title="Match result, by model"
        scores={report.result}
        gaps={report.result_vs_market}
      />
      <ScoreTable
        title="Over or under 2.5 goals, by model"
        scores={report.goals}
        gaps={report.goals_vs_market}
      />

      <div className="grid md:grid-cols-2 gap-10">
        <Calibration blend={report.calibration.blend} market={report.calibration.market} />
        <Weights weights={report.weights} />
      </div>
    </>
  );
}

function Tile({
  label, value, note, accent,
}: { label: string; value: string; note: string; accent?: boolean }) {
  return (
    <div className="panel p-4">
      <div className="label text-dust">{label}</div>
      <div className={`headline text-5xl mt-3 ${accent ? "text-red-hot" : ""}`}>{value}</div>
      <div className="num text-dust mt-2">{note}</div>
    </div>
  );
}

function SectionHead({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="border-b border-line pb-2 mb-4">
      <h2 className="label text-chalk text-sm">{title}</h2>
      {children && <p className="text-dust text-sm mt-1 max-w-2xl">{children}</p>}
    </div>
  );
}

// ---- gap to the bookmakers, season by season ----

type SeasonRow = BacktestReport["by_season"][number];

function SeasonGaps({ seasons }: { seasons: SeasonRow[] }) {
  const [active, setActive] = useState<number | null>(null);

  const W = 640, H = 240, left = 48, right = 8, top = 12, bottom = 30;
  const gaps = seasons.map((s) => s.blend - s.market);
  const hi = Math.max(0.03, Math.ceil(Math.max(...gaps) * 100) / 100);
  const lo = Math.min(-0.01, Math.floor(Math.min(...gaps) * 100) / 100);
  const y = (v: number) => top + ((hi - v) / (hi - lo)) * (H - top - bottom);
  const band = (W - left - right) / seasons.length;
  const ticks: number[] = [];
  for (let t = lo; t <= hi + 1e-9; t += 0.01) ticks.push(Math.round(t * 100) / 100);

  const shown = active != null ? seasons[active] : null;

  return (
    <section>
      <SectionHead title="Gap to the bookmakers, season by season">
        Model log loss minus bookmakers' log loss on match results. A bar above zero is a season
        the bookmakers won.
      </SectionHead>

      <p className="num text-dust h-6" aria-live="polite">
        {shown ? (
          <>
            <span className="text-chalk font-bold">{shown.season}</span> · model {f3(shown.blend)} ·
            bookmakers {f3(shown.market)} · gap{" "}
            <span className="text-chalk font-bold">{signed(shown.blend - shown.market)}</span> ·{" "}
            {shown.matches} matches
          </>
        ) : "Hover or tab to a bar for the season's figures."}
      </p>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img"
           aria-label="Bar chart of the model's log loss gap to the bookmakers in each season">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={left} x2={W - right} y1={y(t)} y2={y(t)}
                  stroke={t === 0 ? AXIS_TEXT : GRID} strokeWidth={1} />
            <text x={left - 8} y={y(t) + 4} textAnchor="end" fontSize="12" fill={AXIS_TEXT}
                  className="num">
              {t === 0 ? "0" : signed(t).slice(0, -1)}
            </text>
          </g>
        ))}
        {seasons.map((s, i) => {
          const g = gaps[i];
          const x = left + i * band;
          const barTop = Math.min(y(g), y(0));
          const height = Math.max(2, Math.abs(y(g) - y(0)));
          return (
            <g key={s.season}>
              <rect
                x={x + band * 0.22} width={band * 0.56} y={barTop} height={height}
                fill={g > 0 ? MODEL_COLOUR : MARKET_COLOUR}
                opacity={active == null || active === i ? 1 : 0.45}
              />
              <text x={x + band / 2} y={H - 10} textAnchor="middle" fontSize="12"
                    fill={active === i ? MARKET_COLOUR : AXIS_TEXT} className="num">
                {s.season.slice(2)}
              </text>
              <rect
                x={x} width={band} y={top} height={H - top} fill="transparent" tabIndex={0}
                aria-label={`${s.season}: gap ${signed(g)}`}
                onMouseEnter={() => setActive(i)} onMouseLeave={() => setActive(null)}
                onFocus={() => setActive(i)} onBlur={() => setActive(null)}
              />
            </g>
          );
        })}
      </svg>

      <Legend items={[
        ["Bookmakers ahead", MODEL_COLOUR],
        ["Model ahead", MARKET_COLOUR],
      ]} />

      <details className="mt-3">
        <summary className="label text-dust cursor-pointer hover:text-chalk">Show as a table</summary>
        <div className="overflow-x-auto mt-2">
          <table className="num w-full text-left">
            <thead>
              <tr className="label text-dust border-b border-line">
                <th className="py-2 pr-3 font-semibold">Season</th>
                <th className="py-2 px-3 font-semibold text-right">Matches</th>
                <th className="py-2 px-3 font-semibold text-right">Model</th>
                <th className="py-2 px-3 font-semibold text-right">Bookmakers</th>
                <th className="py-2 pl-3 font-semibold text-right">Gap</th>
              </tr>
            </thead>
            <tbody>
              {seasons.map((s) => (
                <tr key={s.season} className="border-b border-line">
                  <td className="py-1.5 pr-3">{s.season}</td>
                  <td className="py-1.5 px-3 text-right">{s.matches}</td>
                  <td className="py-1.5 px-3 text-right">{f3(s.blend)}</td>
                  <td className="py-1.5 px-3 text-right">{f3(s.market)}</td>
                  <td className="py-1.5 pl-3 text-right">{signed(s.blend - s.market)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}

function Legend({ items }: { items: [string, string][] }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1 mt-2">
      {items.map(([label, colour]) => (
        <span key={label} className="label text-dust inline-flex items-center gap-2">
          <span className="w-3 h-3" style={{ background: colour }} />
          {label}
        </span>
      ))}
    </div>
  );
}

// ---- every model's score ----

function ScoreTable({
  title, scores, gaps,
}: { title: string; scores: Record<string, ModelScore>; gaps: Record<string, Interval> }) {
  const rows = Object.entries(scores).sort((a, b) => a[1].log_loss.value - b[1].log_loss.value);
  return (
    <section>
      <SectionHead title={title} />
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="label text-dust border-b border-line">
              <th className="py-2 pr-3 font-semibold">Model</th>
              <th className="py-2 px-3 font-semibold text-right">Log loss</th>
              <th className="py-2 px-3 font-semibold text-right hidden sm:table-cell">95% interval</th>
              <th className="py-2 px-3 font-semibold text-right">Gap</th>
              <th className="py-2 pl-3 font-semibold text-right">Right</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([id, s]) => {
              const ours = id === "blend";
              return (
                <tr key={id} className={`border-b border-line ${ours ? "bg-coal" : ""}`}>
                  <td className={`py-2 pr-3 ${ours ? "font-bold border-l-[3px] border-red pl-2" : ""}`}>
                    {MODEL_NAME[id] ?? id}
                  </td>
                  <td className="num py-2 px-3 text-right text-lg font-bold">{f3(s.log_loss.value)}</td>
                  <td className="num py-2 px-3 text-right text-dust hidden sm:table-cell whitespace-nowrap">
                    {f3(s.log_loss.low)} to {f3(s.log_loss.high)}
                  </td>
                  <td className="num py-2 px-3 text-right">{gaps[id] ? signed(gaps[id].value) : ""}</td>
                  <td className="num py-2 pl-3 text-right">{pct(s.accuracy.value)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ---- calibration ----

function Calibration({ blend, market }: { blend: CalibrationBin[]; market: CalibrationBin[] }) {
  const [active, setActive] = useState<{ who: string; bin: CalibrationBin } | null>(null);
  const S = 320, pad = 36;
  const at = (v: number) => pad + v * (S - pad - 8);
  const px = (v: number) => at(v);
  const py = (v: number) => S - at(v);
  const series: [string, CalibrationBin[], string][] = [
    ["Bookmakers", market, MARKET_COLOUR],
    ["Model", blend, MODEL_COLOUR],
  ];

  return (
    <section>
      <SectionHead title="Do the probabilities hold up?">
        Predictions grouped by stated probability, against how often they happened. Points on the
        line are well calibrated.
      </SectionHead>

      <p className="num text-dust h-6" aria-live="polite">
        {active ? (
          <>
            <span className="text-chalk font-bold">{active.who}</span> said{" "}
            {pct(active.bin.stated, 1)}, happened{" "}
            <span className="text-chalk font-bold">{pct(active.bin.observed, 1)}</span> ·{" "}
            {active.bin.count.toLocaleString("en-GB")} predictions
          </>
        ) : "Hover a point for its figures."}
      </p>

      <svg viewBox={`0 0 ${S} ${S}`} className="w-full max-w-sm h-auto" role="img"
           aria-label="Stated probability against observed frequency, for the model and the bookmakers">
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line x1={px(0)} x2={px(1)} y1={py(t)} y2={py(t)} stroke={GRID} />
            <line y1={py(0)} y2={py(1)} x1={px(t)} x2={px(t)} stroke={GRID} />
            <text x={px(0) - 6} y={py(t) + 4} textAnchor="end" fontSize="12" fill={AXIS_TEXT} className="num">
              {Math.round(t * 100)}
            </text>
            <text x={px(t)} y={S - pad + 16} textAnchor="middle" fontSize="12" fill={AXIS_TEXT} className="num">
              {Math.round(t * 100)}
            </text>
          </g>
        ))}
        <line x1={px(0)} y1={py(0)} x2={px(1)} y2={py(1)} stroke={AXIS_TEXT} strokeDasharray="4 4" />
        <text x={(px(0) + px(1)) / 2} y={S - 2} textAnchor="middle" fontSize="12" fill={AXIS_TEXT}
              className="label">
          Stated %
        </text>
        {series.map(([who, bins, colour]) =>
          bins.map((b) => {
            const on = active?.bin === b;
            return (
              <g key={`${who}-${b.stated}`}>
                <circle cx={px(b.stated)} cy={py(b.observed)} r={on ? 7 : 5}
                        fill={colour} stroke="#0a0a0b" strokeWidth={2} />
                <circle cx={px(b.stated)} cy={py(b.observed)} r={12} fill="transparent" tabIndex={0}
                        aria-label={`${who}: said ${pct(b.stated, 1)}, happened ${pct(b.observed, 1)}`}
                        onMouseEnter={() => setActive({ who, bin: b })}
                        onMouseLeave={() => setActive(null)}
                        onFocus={() => setActive({ who, bin: b })}
                        onBlur={() => setActive(null)} />
              </g>
            );
          }),
        )}
      </svg>
      <Legend items={[["Model", MODEL_COLOUR], ["Bookmakers", MARKET_COLOUR]]} />
    </section>
  );
}

// ---- blend weights ----

function Weights({ weights }: { weights: BacktestReport["weights"] }) {
  const groups: [string, Record<string, number>][] = [
    ["Match result", weights.result],
    ["Goals", weights.goals],
  ];
  return (
    <section>
      <SectionHead title="What goes into the blend">
        Weights fitted on predictions from earlier seasons. A model at 0% adds nothing the others
        don't already cover.
      </SectionHead>
      <div className="space-y-6">
        {groups.map(([name, w]) => (
          <div key={name}>
            <h3 className="label text-dust mb-2">{name}</h3>
            <ul className="space-y-2">
              {Object.entries(w).sort((a, b) => b[1] - a[1]).map(([id, share]) => (
                <li key={id}>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className={share === 0 ? "text-dust" : ""}>{MODEL_NAME[id] ?? id}</span>
                    <span className="num font-bold">{pct(share)}</span>
                  </div>
                  <div className="h-1.5 bg-slab mt-1">
                    <div className="h-full bg-red" style={{ width: `${share * 100}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

// ---- this season ----

function ThisSeason({ record }: { record: SeasonRecord }) {
  const [all, setAll] = useState(false);
  const games = all ? record.games : record.games.slice(0, 20);

  return (
    <section>
      <SectionHead title={`This season, ${record.season}`}>
        Every finished match with the probabilities the model gave before kickoff.
      </SectionHead>

      {record.matches === 0 ? (
        <p className="text-dust">No finished matches with a prediction yet.</p>
      ) : (
        <>
          <p className="text-lg mb-4">
            <span className="num font-bold">{record.correct}</span> of{" "}
            <span className="num font-bold">{record.matches}</span> results called right (
            <span className="num font-bold">{pct(record.correct / record.matches)}</span>)
            {record.log_loss != null && (
              <>, log loss <span className="num font-bold">{f3(record.log_loss)}</span></>
            )}
            .
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="label text-dust border-b border-line">
                  <th className="py-2 pr-3 font-semibold">Date</th>
                  <th className="py-2 px-3 font-semibold">Match</th>
                  <th className="py-2 px-3 font-semibold text-right whitespace-nowrap">Home / draw / away</th>
                  <th className="py-2 pl-3 font-semibold text-right">Called</th>
                </tr>
              </thead>
              <tbody>
                {games.map((g) => {
                  const happened = g.home_score > g.away_score ? 0 : g.home_score === g.away_score ? 1 : 2;
                  return (
                    <tr key={`${g.date}-${g.home_team}`} className="border-b border-line">
                      <td className="num py-2 pr-3 text-dust whitespace-nowrap">{shortDate(g.date)}</td>
                      <td className="py-2 px-3">
                        {teamName(g.home_team)}{" "}
                        <span className="num font-bold whitespace-nowrap">{g.home_score}–{g.away_score}</span>{" "}
                        {teamName(g.away_team)}
                      </td>
                      <td className="num py-2 px-3 text-right whitespace-nowrap">
                        {[g.p_home, g.p_draw, g.p_away].map((p, i) => (
                          <span key={i} className={i === happened ? "text-chalk font-bold" : "text-dust"}>
                            {i > 0 && <span className="text-dust font-normal"> / </span>}
                            {pct(p)}
                          </span>
                        ))}
                      </td>
                      <td className={`label py-2 pl-3 text-right ${g.correct ? "text-gold" : "text-dust"}`}>
                        {g.correct ? "Right" : "Wrong"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {record.games.length > 20 && (
            <button
              onClick={() => setAll(!all)}
              className="label border border-line px-4 py-2 mt-4 text-dust hover:text-chalk hover:border-dust"
            >
              {all ? "Show the latest 20" : `Show all ${record.games.length}`}
            </button>
          )}
        </>
      )}
    </section>
  );
}
