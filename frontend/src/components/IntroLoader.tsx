/**
 * IntroLoader — a brief (~1.1s) branded wipe on first load of a session. Shown
 * once per tab (sessionStorage), skipped entirely under reduced-motion. The
 * fade-out is CSS (see `.intro` in index.css); this just unmounts afterward.
 */
import { useEffect, useState } from "react";

const KEY = "zuba-intro-seen";

const prefersReduced =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export default function IntroLoader() {
  const [show, setShow] = useState(() => {
    if (prefersReduced || typeof sessionStorage === "undefined") return false;
    return sessionStorage.getItem(KEY) !== "1";
  });

  useEffect(() => {
    if (!show) return;
    sessionStorage.setItem(KEY, "1");
    const t = window.setTimeout(() => setShow(false), 1200); // after CSS fade-out
    return () => window.clearTimeout(t);
  }, [show]);

  if (!show) return null;
  return (
    <div className="intro" aria-hidden>
      <span className="wm">zuba</span>
      <span className="wipe" />
    </div>
  );
}
