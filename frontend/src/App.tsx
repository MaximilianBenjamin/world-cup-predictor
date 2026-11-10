import { useEffect } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { ParlayBar } from "./cart/ParlayBar";
import Ticker from "./components/Ticker";

const tabClass = ({ isActive }: { isActive: boolean }) =>
  [
    "label h-full inline-flex items-center border-b-[3px] px-1 sm:px-2 whitespace-nowrap transition-colors",
    isActive ? "border-red text-chalk" : "border-transparent text-dust hover:text-chalk",
  ].join(" ");

export default function App() {
  const location = useLocation();

  // Client-side navigation doesn't reset scroll on its own.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-30 bg-ink border-b border-line">
        <div className="h-1 bg-red" />
        <nav className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-stretch justify-between gap-4">
          <Link to="/" className="headline text-3xl self-center pt-1" aria-label="zuba home">
            zuba<span className="text-red">.</span>
          </Link>
          <div className="flex items-stretch gap-2 sm:gap-5">
            <NavLink to="/" end className={tabClass}>
              <span className="sm:hidden">Fixtures</span>
              <span className="hidden sm:inline">Premier League</span>
            </NavLink>
            <NavLink to="/table" className={tabClass}>Table</NavLink>
            <NavLink to="/world-cup" className={tabClass}>World Cup</NavLink>
            <NavLink to="/record" className={tabClass}>Record</NavLink>
          </div>
        </nav>
        <Ticker />
      </header>

      {/* The table page holds two tables side by side, so it gets the full width. */}
      <main
        className={`flex-1 w-full mx-auto px-4 sm:px-6 py-8 ${
          location.pathname === "/table" ? "max-w-[1600px]" : "max-w-5xl"
        }`}
      >
        <div key={location.pathname} className="animate-rise">
          <Outlet />
        </div>
      </main>

      <footer className="mt-12">
        <div className="tape" />
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 text-sm text-dust">
          <p>
            Fair odds are 1 divided by the model's probability. No bookmaker prices are shown, and
            the model is less accurate than the bookmakers: see the{" "}
            <Link to="/record" className="text-chalk underline underline-offset-4 hover:text-red-hot">
              record
            </Link>
            .
          </p>
        </div>
      </footer>

      <ParlayBar />
    </div>
  );
}
