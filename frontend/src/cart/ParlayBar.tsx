import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { postCombine } from "../api/client";
import { useCart } from "./useCart";
import { pct } from "../lib/ui";
import { useCountUp } from "../lib/fx";

/** Floating bet-builder slip pinned to the bottom of every page. Holds the
 *  picks ticked across games and shows the model's combined "fair" odds
 *  (exact same-game joints where available). Fair odds only — no stakes,
 *  no payouts, no bookmaker prices. */
export function ParlayBar() {
  const { legs, remove, clear } = useCart();
  const [open, setOpen] = useState(false);

  if (legs.length === 0) return null;

  const legProduct = legs.reduce((p, l) => p * l.modelP, 1);
  const combined = useCountUp(1 / legProduct, true, 500);

  return (
    <>
      <div className="fixed bottom-0 left-0 right-0 z-40 animate-slide-up">
        <div className="border-t border-glass-border-strong bg-[#0e1436]/80 backdrop-blur-2xl shadow-[0_-12px_40px_-10px_rgba(0,0,0,0.6)]">
          <div className="max-w-5xl mx-auto px-4 sm:px-5 py-3 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <span className="grid place-items-center w-9 h-9 rounded-xl bg-pick/15 ring-1 ring-pick/30 text-pick font-extrabold text-sm shrink-0 animate-pop shadow-pick">
                {legs.length}
              </span>
              <div className="min-w-0">
                <div className="text-[11px] uppercase tracking-[0.18em] text-pick font-semibold">
                  Bet slip
                </div>
                <div className="num text-xs text-dim mt-0.5 truncate">
                  ~<span className="text-cream font-semibold">{combined.toFixed(2)}</span> combined fair odds · tap to review
                </div>
              </div>
            </div>
            <div className="flex gap-2 shrink-0">
              <button
                onClick={clear}
                className="rounded-full border border-glass-border bg-glass hover:bg-glass-hover px-3 py-2 text-xs text-muted transition active:scale-95"
              >
                Clear
              </button>
              <button
                onClick={() => setOpen(true)}
                className="rounded-full bg-accent hover:brightness-110 hover:shadow-[0_0_24px_-4px_#f1600d] px-4 py-2 text-xs text-white font-bold transition active:scale-95"
              >
                Review slip
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="h-20" />

      {open && <SlipModal onRemove={remove} onClose={() => setOpen(false)} />}
    </>
  );
}

function CombinedOdds({ value }: { value: number }) {
  const v = useCountUp(value, true, 700);
  return (
    <span className="num text-4xl font-black text-pick leading-none drop-shadow-[0_0_18px_rgba(80,165,177,0.45)]">
      {v.toFixed(2)}
    </span>
  );
}

function SlipModal({
  onRemove, onClose,
}: { onRemove: (key: string) => void; onClose: () => void }) {
  const { legs, clear } = useCart();

  const combineLegs = legs.map((l) => ({
    match_id: l.matchId,
    market: l.market,
    selection: l.selection,
  }));

  const { data, isLoading } = useQuery({
    queryKey: ["combine", legs.map((l) => l.key).sort()],
    queryFn: () => postCombine(combineLegs),
    enabled: legs.length > 0,
    staleTime: 30_000,
  });

  return (
    <div
      className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-0 sm:p-6"
      onClick={onClose}
    >
      <div
        className="bg-[#1a2550] border-t sm:border border-glass-border-strong rounded-t-3xl sm:rounded-3xl p-5 w-full sm:max-w-md max-h-[92vh] overflow-y-auto animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-extrabold">
            Your slip <span className="text-dim font-medium">· {legs.length}</span>
          </h3>
          <button onClick={onClose} className="grid place-items-center w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 text-muted hover:text-white text-xl leading-none transition">×</button>
        </div>

        {legs.length === 0 && <p className="text-sm text-muted py-4">No picks yet.</p>}

        <ul className="space-y-2 mb-4">
          {legs.map((l) => (
            <li key={l.key} className="flex items-start justify-between gap-2 rounded-xl border border-glass-border bg-glass px-3 py-2.5">
              <div className="flex-1 min-w-0">
                <Link
                  to={`/match/${l.matchId}`}
                  onClick={onClose}
                  className="text-sm font-semibold hover:text-pick transition-colors block truncate"
                >
                  {l.selectionLabel}
                </Link>
                <div className="num text-[11px] text-muted truncate mt-0.5">
                  {l.matchLabel} · {pct(l.modelP, 1)} · fair {l.fairOdds.toFixed(2)}
                </div>
              </div>
              <button
                onClick={() => onRemove(l.key)}
                className="shrink-0 grid place-items-center w-6 h-6 rounded-full bg-white/5 hover:bg-bad/20 text-muted hover:text-bad text-sm transition"
                aria-label="remove"
              >
                ×
              </button>
            </li>
          ))}
        </ul>

        {isLoading && <p className="text-sm text-muted py-2">Combining…</p>}

        {data && (
          <div className="rounded-2xl bg-pick/10 border border-pick/30 p-4">
            <div className="flex items-end justify-between">
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-pick/90">Combined fair odds</div>
                <div className="num text-[11px] text-muted mt-0.5">
                  model {pct(data.combined_p, 1)} chance
                </div>
              </div>
              <CombinedOdds value={data.combined_fair_odds} />
            </div>
            <div className={`text-xs mt-3 pt-3 border-t border-pick/20 ${data.correlated_warning ? "text-warn" : "text-dim"}`}>
              {data.correlated_warning ? "⚠ " : ""}{data.note}
            </div>
          </div>
        )}

        {legs.length > 0 && (
          <button
            onClick={() => { clear(); onClose(); }}
            className="w-full mt-4 rounded-full border border-glass-border bg-glass hover:bg-glass-hover py-2.5 text-xs text-muted transition"
          >
            Clear slip
          </button>
        )}

        <p className="text-[11px] text-muted mt-3 leading-relaxed">
          Our models' own fair prices — there are no bookmaker odds here. Just for fun.
        </p>
      </div>
    </div>
  );
}
