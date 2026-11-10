import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { postCombine } from "../api/client";
import { useCart, type CartLeg } from "./useCart";
import { pct } from "../lib/ui";

/** Bar pinned to the bottom of every page once a price has been selected. It
 *  holds the selections made across matches and shows their combined fair
 *  odds. Fair odds only: no stakes, payouts or bookmaker prices. */
export function ParlayBar() {
  const { legs, remove, clear } = useCart();
  const [open, setOpen] = useState(false);

  if (legs.length === 0) return null;

  return (
    <>
      <div className="fixed bottom-0 inset-x-0 z-40 bg-coal border-t-[3px] border-gold">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <span className="num grid place-items-center w-9 h-9 bg-gold text-ink text-xl font-bold shrink-0">
              {legs.length}
            </span>
            <div className="min-w-0">
              <div className="label text-gold">Combined picks</div>
              <QuickOdds legs={legs} />
            </div>
          </div>
          <div className="flex gap-2 shrink-0">
            <button onClick={clear} className="label border border-line px-3 py-2 text-dust hover:text-chalk hover:border-dust">
              Clear
            </button>
            <button onClick={() => setOpen(true)} className="label bg-red hover:bg-red-hot px-4 py-2 text-white">
              Review
            </button>
          </div>
        </div>
      </div>

      {/* Keeps the footer clear of the bar. */}
      <div className="h-20" />

      {open && <PicksDialog onRemove={remove} onClose={() => setOpen(false)} />}
    </>
  );
}

/** Product of the single prices. Right for picks from different matches; the
 *  dialog asks the server for the exact figure when picks share a match. */
function QuickOdds({ legs }: { legs: CartLeg[] }) {
  const product = legs.reduce((p, l) => p * l.modelP, 1);
  return (
    <div className="num text-dust truncate">
      about <span className="text-chalk font-bold">{(1 / product).toFixed(2)}</span> combined
    </div>
  );
}

function PicksDialog({
  onRemove, onClose,
}: { onRemove: (key: string) => void; onClose: () => void }) {
  const { legs, clear } = useCart();

  const { data, isLoading } = useQuery({
    queryKey: ["combine", legs.map((l) => l.key).sort()],
    queryFn: () => postCombine(
      legs.map((l) => ({ match_id: l.matchId, market: l.market, selection: l.selection })),
    ),
    enabled: legs.length > 0,
    staleTime: 30_000,
  });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 bg-black/80 z-50 flex items-end sm:items-center justify-center sm:p-6"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Combined picks"
        className="panel p-5 w-full sm:max-w-md max-h-[92vh] overflow-y-auto animate-rise"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="headline text-3xl">Combined picks</h3>
          <button onClick={onClose} className="label text-dust hover:text-chalk px-2 py-1">Close</button>
        </div>

        {legs.length === 0 && <p className="text-dust py-4">Nothing selected.</p>}

        <ul className="mb-4 border-t border-line">
          {legs.map((l) => (
            <li key={l.key} className="flex items-start justify-between gap-3 border-b border-line py-2.5">
              <div className="flex-1 min-w-0">
                <Link
                  to={`/match/${l.matchId}`}
                  onClick={onClose}
                  className="font-semibold hover:text-gold block truncate"
                >
                  {l.selectionLabel}
                </Link>
                <div className="num text-dust truncate">
                  {l.matchLabel} · {pct(l.modelP, 1)} · {l.fairOdds.toFixed(2)}
                </div>
              </div>
              <button onClick={() => onRemove(l.key)} className="label text-dust hover:text-red-hot shrink-0 py-1">
                Remove
              </button>
            </li>
          ))}
        </ul>

        {isLoading && <p className="label text-dust py-2">Combining</p>}

        {data && (
          <div className="border border-gold p-4">
            <div className="flex items-end justify-between gap-3">
              <div>
                <div className="label text-gold">Combined fair odds</div>
                <div className="num text-dust mt-1">{pct(data.combined_p, 1)} chance</div>
              </div>
              <span className="headline text-6xl text-gold">{data.combined_fair_odds.toFixed(2)}</span>
            </div>
            <p className={`text-sm mt-3 pt-3 border-t border-line ${data.correlated_warning ? "text-chalk" : "text-dust"}`}>
              {data.note}
            </p>
          </div>
        )}

        {legs.length > 0 && (
          <button
            onClick={() => { clear(); onClose(); }}
            className="label w-full mt-4 border border-line py-2.5 text-dust hover:text-chalk hover:border-dust"
          >
            Clear all
          </button>
        )}
      </div>
    </div>
  );
}
