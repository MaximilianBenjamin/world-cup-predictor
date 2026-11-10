import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getGames } from "../api/client";
import type { Competition, GameSummary } from "../api/types";
import TeamBadge from "../components/TeamBadge";
import { dayKey, pct, sastTime, teamCode, teamName } from "../lib/ui";

const COPY: Record<Competition, { kicker: string; title: [string, string]; intro: string; empty: string }> = {
  epl: {
    kicker: "Fair odds from the model",
    title: ["Premier", "League"],
    intro: "Every upcoming fixture, priced by the model. Open a match for goals markets and combined picks.",
    empty: "No upcoming fixtures have been fetched yet.",
  },
  wc: {
    kicker: "Archive",
    title: ["World Cup", "2026"],
    intro: "The tournament is over. These are the prices the model gave before each game.",
    empty: "No World Cup matches are stored in this database.",
  },
};

export default function SlatePage({ competition }: { competition: Competition }) {
  const archive = competition === "wc";
  const { data, isLoading, error } = useQuery({
    queryKey: archive ? ["games", competition, "all"] : ["games", competition],
    queryFn: () => getGames(competition, archive),
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  });
  const copy = COPY[competition];

  const games = [...(data?.games ?? [])];
  if (archive) games.reverse();   // newest first

  // Grouped by day, so the page reads like a fixture list.
  const groups: { label: string; games: GameSummary[] }[] = [];
  for (const g of games) {
    const label = dayKey(g.kickoff_ts ?? g.date);
    const last = groups[groups.length - 1];
    if (last && last.label === label) last.games.push(g);
    else groups.push({ label, games: [g] });
  }

  return (
    <div>
      <header className="mb-8">
        <p className="label text-red-hot mb-3">{copy.kicker}</p>
        <h1 className="headline text-6xl sm:text-8xl">
          {copy.title[0]} <span className="text-red">{copy.title[1]}</span>
        </h1>
        <div className="tape mt-5 mb-4 max-w-xs" />
        <p className="text-dust max-w-xl">{copy.intro}</p>
      </header>

      {isLoading && <SkeletonRows />}

      {error && (
        <div className="panel p-6">
          <p className="font-semibold">Could not load the fixtures.</p>
          <p className="text-dust text-sm mt-1">{String(error)}</p>
        </div>
      )}

      {data && games.length === 0 && (
        <div className="panel p-8 text-dust">{copy.empty}</div>
      )}

      <div className="space-y-8">
        {groups.map((grp) => (
          <section key={grp.label}>
            <div className="flex items-end justify-between border-b border-line pb-2">
              <h2 className="label text-chalk text-sm">{grp.label}</h2>
              <div className="label text-dust hidden sm:grid grid-cols-3 w-[264px] text-center">
                <span>Home</span><span>Draw</span><span>Away</span>
              </div>
            </div>
            <ul>
              {grp.games.map((g) => (
                <FixtureRow key={g.match_id} game={g} />
              ))}
            </ul>
          </section>
        ))}
      </div>

      {data && games.length > 0 && (
        <p className="num text-sm text-dust mt-6">
          Kickoff times are South African time. Model version {data.model_version}.
        </p>
      )}
    </div>
  );
}

function FixtureRow({ game }: { game: GameSummary }) {
  const c = game.competition;
  const played = game.completed && game.home_score != null && game.away_score != null;
  const cells: [string, string, number | null][] = [
    ["home", teamCode(game.home_team, c), game.p_home],
    ["draw", "Draw", game.p_draw],
    ["away", teamCode(game.away_team, c), game.p_away],
  ];

  return (
    <li className="border-b border-line">
      <Link
        to={`/match/${game.match_id}`}
        className="group flex flex-col sm:flex-row sm:items-center gap-3 py-3 sm:px-2 hover:bg-coal transition-colors"
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <span className="num text-dust w-11 shrink-0">
            {played ? "FT" : sastTime(game.kickoff_ts)}
          </span>
          <div className="flex-1 min-w-0 space-y-1.5">
            <TeamLine team={game.home_team} competition={c} score={played ? game.home_score : null} />
            <TeamLine team={game.away_team} competition={c} score={played ? game.away_score : null} />
          </div>
        </div>

        {game.has_prediction ? (
          <div className="grid grid-cols-3 gap-1.5 sm:w-[264px] shrink-0 pl-14 sm:pl-0">
            {cells.map(([sel, label, p]) => {
              const pick = game.pick_selection === sel;
              return (
                <div
                  key={sel}
                  className={`px-2 py-1.5 text-center border ${
                    pick ? "border-gold bg-gold/10" : "border-line bg-slab"
                  }`}
                >
                  <div className="label text-dust sm:hidden">{label}</div>
                  <div className={`num text-xl font-bold leading-tight ${pick ? "text-gold" : ""}`}>
                    {p ? (1 / p).toFixed(2) : "–"}
                  </div>
                  <div className="num text-sm text-dust leading-tight">{p != null ? pct(p) : ""}</div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="label text-dust sm:w-[264px] shrink-0 pl-14 sm:pl-0 sm:text-center">
            Not priced yet
          </div>
        )}
      </Link>
    </li>
  );
}

function TeamLine({
  team, competition, score,
}: { team: string; competition: Competition; score: number | null }) {
  return (
    <div className="flex items-center gap-2.5 min-w-0">
      <TeamBadge team={team} competition={competition} size={26} />
      <span className="font-semibold text-lg leading-none truncate flex-1">
        {teamName(team, competition)}
      </span>
      {score != null && <span className="num text-xl font-bold pr-2">{score}</span>}
    </div>
  );
}

function SkeletonRows() {
  return (
    <div aria-busy="true" aria-label="Loading fixtures">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-[76px] border-b border-line bg-coal/60 animate-pulse" />
      ))}
    </div>
  );
}
