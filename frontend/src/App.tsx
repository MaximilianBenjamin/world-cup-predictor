import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { ParlayBar } from "./cart/ParlayBar";
import { useMagnetic } from "./lib/fx";
import ShaderBackground from "./components/ShaderBackground";
import CustomCursor from "./components/CustomCursor";
import IntroLoader from "./components/IntroLoader";
import Ticker from "./components/Ticker";

const tabClass = ({ isActive }: { isActive: boolean }) =>
  [
    "relative px-3 py-1.5 rounded-full text-sm font-semibold transition-colors duration-200 z-10",
    isActive ? "text-cream" : "text-muted hover:text-cream",
  ].join(" ");

/** Ambient parallax: feed cursor position into --px/--py (read by .aurora). rAF-throttled. */
function usePointerAmbient() {
  useEffect(() => {
    if (!window.matchMedia?.("(hover: hover) and (pointer: fine)").matches) return;
    let raf = 0;
    const onMove = (e: PointerEvent) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const root = document.documentElement;
        root.style.setProperty("--px", `${(e.clientX / window.innerWidth) * 100}%`);
        root.style.setProperty("--py", `${(e.clientY / window.innerHeight) * 100}%`);
      });
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      cancelAnimationFrame(raf);
    };
  }, []);
}

export default function App() {
  usePointerAmbient();
  const location = useLocation();
  const [scrolled, setScrolled] = useState(false);
  const tabsRef = useRef<HTMLDivElement>(null);
  const brandRef = useMagnetic<HTMLAnchorElement>(0.4);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Start every route at the top (client-side nav doesn't reset scroll on its own).
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  // Sliding indicator that snaps under the active nav tab. Re-placed only when
  // the route changes or the bar resizes — and setPill bails when the position
  // is unchanged, so it never triggers a render loop (a no-deps effect that set
  // a fresh object every render previously starved the router and broke nav).
  const [pill, setPill] = useState<{ left: number; width: number } | null>(null);
  useEffect(() => {
    const el = tabsRef.current;
    if (!el) return;
    const place = () => {
      const active = el.querySelector<HTMLElement>("[aria-current='page']");
      if (!active) return;
      const next = { left: active.offsetLeft, width: active.offsetWidth };
      setPill((prev) =>
        prev && prev.left === next.left && prev.width === next.width ? prev : next,
      );
    };
    place();
    const id = window.setTimeout(place, 60); // catch post-paint layout
    const ro = new ResizeObserver(place);
    ro.observe(el);
    return () => {
      ro.disconnect();
      window.clearTimeout(id);
    };
  }, [location.pathname]);

  return (
    <div className="min-h-screen text-white">
      {/* WebGL flow field on desktop; the .aurora CSS below is the fallback. */}
      <ShaderBackground />
      <IntroLoader />
      <CustomCursor />

      {/* ambient background (fallback + touch) */}
      <div className="aurora">
        <span className="a1" />
        <span className="a2" />
        <span className="a3" />
      </div>

      <header
        className={`sticky top-0 z-30 transition-all duration-300 ${
          scrolled
            ? "border-b border-glass-border bg-[#0e1436]/70 backdrop-blur-xl shadow-[0_8px_30px_-12px_rgba(0,0,0,0.6)]"
            : "border-b border-transparent bg-transparent"
        }`}
      >
        <nav className="max-w-5xl mx-auto px-4 sm:px-5 h-14 flex items-center justify-between gap-2">
          <Link
            ref={brandRef}
            to="/"
            className="magnetic flex items-center gap-2 shrink-0 group"
          >
            <span className="grid place-items-center w-7 h-7 rounded-lg bg-accent/15 ring-1 ring-accent/25 text-accent text-sm group-hover:scale-105 transition-transform">
              ⚡
            </span>
            <span className="font-black tracking-tight text-lg text-grad-sheen">zuba</span>
          </Link>

          <div
            ref={tabsRef}
            className="relative flex items-center gap-1 rounded-full bg-glass ring-1 ring-glass-border p-1 backdrop-blur-md"
          >
            {pill && (
              <span
                aria-hidden
                className="absolute top-1 bottom-1 rounded-full bg-glass-strong ring-1 ring-glass-border-strong shadow-[0_2px_12px_-2px_rgba(0,0,0,0.5)] transition-all duration-300"
                style={{
                  left: pill.left,
                  width: pill.width,
                  transitionTimingFunction: "cubic-bezier(0.34,1.56,0.64,1)",
                }}
              />
            )}
            <NavLink to="/" end className={tabClass}>
              <span className="sm:hidden">⚽</span>
              <span className="hidden sm:inline">⚽ World Cup</span>
            </NavLink>
          </div>

          <span className="hidden md:flex text-[11px] text-dim items-center gap-1.5 shrink-0">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full rounded-full bg-accent opacity-75 animate-ping" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-accent" />
            </span>
            live model odds
          </span>
        </nav>
        <Ticker />
      </header>

      <main className="relative z-10 max-w-5xl mx-auto px-4 sm:px-5 py-6">
        <div key={location.pathname} className="page-enter">
          <Outlet />
        </div>
      </main>

      <footer className="relative z-10 max-w-5xl mx-auto px-5 py-10 text-xs text-muted border-t border-glass-border mt-12">
        <p>
          Our models' own fair odds — no bookmaker odds, no guarantee of value. Just for fun.
          Bet at your own risk.
        </p>
      </footer>

      <ParlayBar />
    </div>
  );
}
