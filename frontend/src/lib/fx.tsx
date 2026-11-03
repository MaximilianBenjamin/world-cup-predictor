/**
 * fx — the interaction/motion engine. Pure browser APIs (rAF, IntersectionObserver,
 * pointer events), no dependencies, all gated on prefers-reduced-motion + touch so
 * the site stays fast and accessible. Powers spotlight cards, count-up numbers, and
 * scroll-reveal across every page.
 */
import {
  createElement,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ElementType,
  type ReactNode,
  type RefObject,
} from "react";

/** Respect the OS "reduce motion" setting — reactive. */
export function useReducedMotion(): boolean {
  const q = "(prefers-reduced-motion: reduce)";
  const [reduced, setReduced] = useState(
    () => typeof window !== "undefined" && window.matchMedia(q).matches,
  );
  useEffect(() => {
    const m = window.matchMedia(q);
    const h = () => setReduced(m.matches);
    m.addEventListener("change", h);
    return () => m.removeEventListener("change", h);
  }, []);
  return reduced;
}

const canHover =
  typeof window !== "undefined" &&
  window.matchMedia?.("(hover: hover) and (pointer: fine)").matches;

const prefersReduced =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/**
 * Magnetic hook — attach the returned ref to an element (button/link) and it
 * drifts toward the cursor while hovered, springing back on leave. Desktop-only
 * and off under reduced-motion. Pair with the `.magnetic` class (transition).
 */
export function useMagnetic<T extends HTMLElement = HTMLElement>(
  strength = 0.35,
): RefObject<T | null> {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || !canHover || prefersReduced) return;
    let raf = 0;
    const onMove = (e: PointerEvent) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const r = el.getBoundingClientRect();
        const x = e.clientX - (r.left + r.width / 2);
        const y = e.clientY - (r.top + r.height / 2);
        el.style.transform = `translate(${x * strength}px, ${y * strength}px)`;
      });
    };
    const leave = () => {
      cancelAnimationFrame(raf);
      el.style.transform = "";
    };
    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerleave", leave);
    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", leave);
      cancelAnimationFrame(raf);
    };
  }, [strength]);
  return ref;
}

/** Animate a number toward `target` with an ease-out cubic. Returns the live value.
 *  Starts once `active` is true (pair with useReveal so it counts as it appears), and
 *  re-animates smoothly from the current value whenever `target` changes. */
export function useCountUp(target: number, active = true, durationMs = 750): number {
  const reduced = useReducedMotion();
  const [val, setVal] = useState(reduced ? target : 0);
  const fromRef = useRef(0);
  const rafRef = useRef(0);

  useEffect(() => {
    if (!active) return;
    if (reduced) {
      setVal(target);
      fromRef.current = target;
      return;
    }
    const from = fromRef.current;
    const t0 = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / durationMs);
      const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      const cur = from + (target - from) * eased;
      setVal(cur);
      fromRef.current = cur;
      if (p < 1) rafRef.current = requestAnimationFrame(tick);
      else {
        setVal(target);
        fromRef.current = target;
      }
    };
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [active, target, durationMs, reduced]);

  return val;
}

/** Reveal-on-scroll. Returns a ref to attach and a boolean that flips true the
 *  first time the element enters the viewport (then stays true). */
export function useReveal<T extends HTMLElement = HTMLDivElement>(): {
  ref: RefObject<T | null>;
  shown: boolean;
} {
  const ref = useRef<T>(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || shown) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setShown(true);
          io.disconnect();
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.05 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [shown]);
  return { ref, shown };
}

/**
 * Spotlight surface — a card/button that tracks the cursor with a radial glow and
 * a reactive border. Writes CSS vars (--mx/--my/--active) consumed by `.fx-spot`
 * in index.css. No-ops on touch. Renders as `as` (default div).
 */
export function Spotlight({
  as = "div",
  className = "",
  children,
  style,
  tilt = false,
  tiltMax = 6,
  ...rest
}: {
  as?: ElementType;
  className?: string;
  children?: ReactNode;
  style?: CSSProperties;
  /** Add a subtle 3D parallax tilt toward the cursor (desktop only). */
  tilt?: boolean;
  /** Max rotation in degrees for each axis when `tilt`. */
  tiltMax?: number;
  [key: string]: unknown;
}) {
  const ref = useRef<HTMLElement>(null);
  const frame = useRef(0);
  const doTilt = tilt && !prefersReduced;

  useEffect(() => {
    const el = ref.current;
    if (!el || !canHover) return;
    const onMove = (e: PointerEvent) => {
      cancelAnimationFrame(frame.current);
      frame.current = requestAnimationFrame(() => {
        const r = el.getBoundingClientRect();
        const mx = (e.clientX - r.left) / r.width;
        const my = (e.clientY - r.top) / r.height;
        el.style.setProperty("--mx", `${mx * 100}%`);
        el.style.setProperty("--my", `${my * 100}%`);
        if (doTilt) {
          el.style.setProperty("--ry", `${(mx - 0.5) * tiltMax * 2}deg`);
          el.style.setProperty("--rx", `${-(my - 0.5) * tiltMax * 2}deg`);
        }
      });
    };
    const enter = () => el.style.setProperty("--active", "1");
    const leave = () => {
      cancelAnimationFrame(frame.current);
      el.style.setProperty("--active", "0");
      if (doTilt) {
        el.style.setProperty("--rx", "0deg");
        el.style.setProperty("--ry", "0deg");
      }
    };
    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerenter", enter);
    el.addEventListener("pointerleave", leave);
    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerenter", enter);
      el.removeEventListener("pointerleave", leave);
    };
  }, [doTilt, tiltMax]);

  return createElement(
    as,
    {
      ref,
      className: `fx-spot ${doTilt ? "fx-tilt" : ""} ${className}`,
      style,
      ...rest,
    },
    children,
  );
}
