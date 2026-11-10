/**
 * A slim scrolling strip of the model's pick for each upcoming Premier League
 * match, shown under the header. It reuses the fixture list's cached query, so
 * it adds no request. Pauses on hover; static under reduced motion (CSS).
 */
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getGames } from "../api/client";
import { teamCode } from "../lib/ui";

export default function Ticker() {
  const { data } = useQuery({
    queryKey: ["games", "epl"],
    queryFn: () => getGames("epl"),
    refetchInterval: 60_000,
  });

  const picks = (data?.games ?? []).filter((g) => g.has_prediction && g.pick_label);
  if (picks.length === 0) return null;

  // The run is duplicated so the -50% keyframe wraps without a jump.
  const items = [...picks, ...picks];

  return (
    <div className="ticker bg-coal border-t border-line overflow-hidden">
      <div className="ticker-track px-4 py-1.5">
        {items.map((g, i) => (
          <Link
            key={`${g.match_id}-${i}`}
            to={`/match/${g.match_id}`}
            className="num inline-flex items-baseline gap-2 text-sm text-dust hover:text-chalk"
            aria-hidden={i >= picks.length}
            tabIndex={i >= picks.length ? -1 : 0}
          >
            <span className="font-semibold tracking-wide">
              {teamCode(g.home_team)} v {teamCode(g.away_team)}
            </span>
            <span className="font-bold text-gold">
              {g.pick_selection === "draw" ? "Draw" : teamCode(g.pick_label!)}{" "}
              {Math.round((g.pick_p ?? 0) * 100)}%
            </span>
            <span>{g.pick_fair_odds?.toFixed(2)}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
