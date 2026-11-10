import { useQuery } from "@tanstack/react-query";
import type { PredictedRow, TableResponse, TableRow } from "../api/types";
import { getTable } from "../api/client";
import TeamBadge from "../components/TeamBadge";
import { pct, shortDate, teamName } from "../lib/ui";

export default function TablePage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["table"],
    queryFn: getTable,
    staleTime: 5 * 60_000,
  });

  return (
    <div>
      <header className="mb-8">
        <p className="label text-red-hot mb-3">
          Premier League{data && ` ${data.season}`}
        </p>
        <h1 className="headline text-6xl sm:text-8xl">
          The <span className="text-red">table</span>
        </h1>
        <div className="tape mt-5 mb-4 max-w-xs" />
        <p className="text-dust max-w-xl">
          Where the clubs stand now, and where the model expects them to finish.
        </p>
      </header>

      {isLoading && <p className="label text-dust py-16 text-center">Loading the table</p>}
      {error && (
        <div className="panel p-6">
          <p className="font-semibold">The table is not available yet.</p>
          <p className="text-dust text-sm mt-1">It is built by the daily refresh.</p>
        </div>
      )}

      {data && (
        <div className="grid lg:grid-cols-2 gap-x-10 xl:gap-x-16 gap-y-12 items-start">
          <Current data={data} />
          <Predicted data={data} />
        </div>
      )}
    </div>
  );
}

function SectionHead({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-line pb-2">
      <h2 className="label text-chalk text-sm">{title}</h2>
      <p className="text-dust text-sm mt-1 lg:h-10">{children}</p>
    </div>
  );
}

const th = "py-2 px-2 font-semibold text-right";
const td = "num py-2 px-2 text-right";
const stuck = "sticky left-0 z-10 bg-ink group-hover:bg-coal shadow-[1px_0_0_#2c2c31]";

/** Champions League places end after 4th; the bottom three go down. A heavier
 *  rule under those rows marks the lines. */
function zoneRule(position: number, clubs: number): string {
  return position === 4 || position === clubs - 3 ? "border-b-2 border-b-dust" : "border-b border-line";
}

/** Position and club. This cell stays put while the rest of the row scrolls
 *  sideways. */
function ClubCell({ position, team }: { position: number; team: string }) {
  return (
    <td className={`${stuck} py-2 pr-3`}>
      <span className="flex items-center gap-2.5">
        <span className="num text-dust w-5 shrink-0">{position}</span>
        <TeamBadge team={team} size={24} />
        <span className="font-semibold whitespace-nowrap">{teamName(team)}</span>
      </span>
    </td>
  );
}

function ClubHead() {
  return <th className={`${stuck} py-2 pr-3 font-semibold`}>Club</th>;
}

function ScrollHint() {
  return <p className="label text-dust mt-2">Scroll the table sideways for more</p>;
}

// ---- predicted final table ----

function Movement({ row }: { row: PredictedRow }) {
  const places = row.current_position - row.position;
  if (places === 0) return <span className="text-dust">–</span>;
  return (
    <span className={places > 0 ? "text-gold" : "text-red-hot"}>
      {places > 0 ? "▲" : "▼"}{Math.abs(places)}
    </span>
  );
}

function Chance({ p, strong }: { p: number; strong: string }) {
  if (p < 0.0005) return <span className="text-line">–</span>;
  const text = p < 0.01 ? "<1%" : p > 0.99 ? ">99%" : pct(p);
  return <span className={p >= 0.5 ? `font-bold ${strong}` : ""}>{text}</span>;
}

function Predicted({ data }: { data: TableResponse }) {
  const n = data.predicted.length;
  return (
    <section>
      <SectionHead title="Predicted final table">
        The {data.matches_remaining} matches still to play, simulated{" "}
        {data.simulations.toLocaleString("en-GB")} times. Points and goals are averages.
      </SectionHead>
      <div className="overflow-x-auto">
        <table className="w-full text-left min-w-[700px]">
          <thead>
            <tr className="label text-dust border-b border-line">
              <ClubHead />
              <th className={th}>Pts</th>
              <th className={th} title="Places gained or lost from the current table">Move</th>
              <th className={th}>GD</th>
              <th className={th}>GF</th>
              <th className={th}>GA</th>
              <th className={th} title="Range of final positions in the middle 90% of simulations">Range</th>
              <th className={th}>Title</th>
              <th className={th}>Top 4</th>
              <th className={`${th} pr-0`}>Down</th>
            </tr>
          </thead>
          <tbody>
            {data.predicted.map((r) => (
              <tr key={r.team} className={`group ${zoneRule(r.position, n)} hover:bg-coal`}>
                <ClubCell position={r.position} team={r.team} />
                <td className={`${td} text-lg font-bold`}>{Math.round(r.points)}</td>
                <td className={`${td} text-sm`}><Movement row={r} /></td>
                <td className={td}>{signedRound(r.goal_difference)}</td>
                <td className={`${td} text-dust`}>{Math.round(r.goals_for)}</td>
                <td className={`${td} text-dust`}>{Math.round(r.goals_against)}</td>
                <td className={`${td} text-dust whitespace-nowrap`}>
                  {r.position_low === r.position_high
                    ? r.position_low
                    : `${r.position_low}–${r.position_high}`}
                </td>
                <td className={td}><Chance p={r.p_title} strong="text-gold" /></td>
                <td className={td}><Chance p={r.p_top4} strong="text-chalk" /></td>
                <td className={`${td} pr-0`}><Chance p={r.p_relegation} strong="text-red-hot" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ScrollHint />
      <p className="text-sm text-dust mt-3 max-w-2xl">
        Updated after each round of results. Move is places gained or lost from the current table.
        Range is where a club finishes in 9 simulated seasons out of 10. Every remaining match is
        priced from today's form, and a club's strength does not change during a simulated season,
        so the real spread is somewhat wider.
      </p>
    </section>
  );
}

function signedRound(x: number): string {
  const r = Math.round(x);
  return r > 0 ? `+${r}` : r < 0 ? `−${Math.abs(r)}` : "0";
}

// ---- current table ----

function Current({ data }: { data: TableResponse }) {
  const n = data.current.length;
  return (
    <section>
      <SectionHead title="Current table">
        {data.matches_played} matches played, results to {shortDate(data.results_to)}.
      </SectionHead>
      <div className="overflow-x-auto">
        <table className="w-full text-left min-w-[600px]">
          <thead>
            <tr className="label text-dust border-b border-line">
              <ClubHead />
              <th className={th} title="Points">Pts</th>
              <th className={th} title="Played">P</th>
              <th className={th} title="Won">W</th>
              <th className={th} title="Drawn">D</th>
              <th className={th} title="Lost">L</th>
              <th className={th} title="Goals for">GF</th>
              <th className={th} title="Goals against">GA</th>
              <th className={`${th} pr-0`} title="Goal difference">GD</th>
            </tr>
          </thead>
          <tbody>
            {data.current.map((r: TableRow) => (
              <tr key={r.team} className={`group ${zoneRule(r.position, n)} hover:bg-coal`}>
                <ClubCell position={r.position} team={r.team} />
                <td className={`${td} text-lg font-bold`}>{r.points}</td>
                <td className={`${td} text-dust`}>{r.played}</td>
                <td className={`${td} text-dust`}>{r.won}</td>
                <td className={`${td} text-dust`}>{r.drawn}</td>
                <td className={`${td} text-dust`}>{r.lost}</td>
                <td className={td}>{r.goals_for}</td>
                <td className={td}>{r.goals_against}</td>
                <td className={`${td} pr-0`}>{signedRound(r.goal_difference)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ScrollHint />
    </section>
  );
}
