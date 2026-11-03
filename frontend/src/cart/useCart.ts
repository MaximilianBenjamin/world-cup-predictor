import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "zuba.betslip.v2";

/** One pick in the bet-builder slip. `key` uniquely identifies a (match,
 *  market, selection) so the same pick can't be added twice. */
export interface CartLeg {
  key: string;
  matchId: number;
  matchLabel: string;
  market: string;
  selection: string;
  selectionLabel: string;
  modelP: number;
  fairOdds: number;
}

export function legKey(matchId: number, market: string, selection: string): string {
  return `${matchId}:${market}:${selection}`;
}

function read(): CartLeg[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as CartLeg[]).filter((l) => l && l.key) : [];
  } catch {
    return [];
  }
}

function write(legs: CartLeg[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(legs));
  window.dispatchEvent(new Event("zuba:cart"));
}

/** localStorage-backed bet-builder slip. Changes broadcast a `zuba:cart`
 *  event so every subscriber re-renders without prop drilling. */
export function useCart() {
  const [legs, setLegs] = useState<CartLeg[]>(read);

  useEffect(() => {
    const handler = () => setLegs(read());
    window.addEventListener("zuba:cart", handler);
    window.addEventListener("storage", handler);
    return () => {
      window.removeEventListener("zuba:cart", handler);
      window.removeEventListener("storage", handler);
    };
  }, []);

  const add = useCallback((leg: CartLeg) => {
    const cur = read();
    if (cur.some((l) => l.key === leg.key)) return;
    write([...cur, leg]);
  }, []);
  const remove = useCallback((key: string) => {
    write(read().filter((l) => l.key !== key));
  }, []);
  const toggle = useCallback((leg: CartLeg) => {
    const cur = read();
    write(cur.some((l) => l.key === leg.key)
      ? cur.filter((l) => l.key !== leg.key)
      : [...cur, leg]);
  }, []);
  const clear = useCallback(() => write([]), []);
  const has = useCallback((key: string) => read().some((l) => l.key === key), []);

  return { legs, add, remove, toggle, clear, has };
}
