/**
 * Ticker — a slim infinite marquee of the model's live picks, shown under the
 * header. Reuses the cached ["games"] query (same key as the slate), so it adds
 * no network request. Pauses on hover; static under reduced-motion (CSS).
 */
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getGames } from "../api/client";
import { shortTeam } from "../lib/ui";

export default function Ticker() {
  const { data } = useQuery({
    queryKey: ["games"],
    queryFn: () => getGames(),
    refetchInterval: 60_000,
  });

  const picks = (data?.games ?? []).filter((g) => g.has_prediction && g.pick_label);
  if (picks.length === 0) return null;

  // Duplicate the run so the -50% keyframe wraps seamlessly.
  const items = [...picks, ...picks];

  return (
    <div className="ticker relative z-20">
      <div className="max-w-6xl mx-auto">
        <div className="ticker-track px-4 text-[12px]">
          {items.map((g, i) => (
            <Link
              key={`${g.match_id}-${i}`}
              to={`/match/${g.match_id}`}
              className="inline-flex items-center gap-2 text-muted hover:text-cream transition-colors"
              aria-hidden={i >= picks.length}
              tabIndex={i >= picks.length ? -1 : 0}
            >
              <span className="font-semibold text-cream">{shortTeam(g.pick_label!)}</span>
              <span className="text-pick font-bold num">
                {Math.round((g.pick_p ?? 0) * 100)}%
              </span>
              <span className="text-dim num">fair {g.pick_fair_odds?.toFixed(2)}</span>
              <span className="text-accent/60">▸</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
