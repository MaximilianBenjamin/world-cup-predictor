/**
 * CustomCursor — a precise dot plus a trailing ring that lerps behind it and
 * swells over interactive elements (links/buttons). Desktop only; never mounts
 * under reduced-motion or on touch/no-hover devices (the OS cursor is used).
 */
import { useEffect, useRef } from "react";

const canHover =
  typeof window !== "undefined" &&
  window.matchMedia?.("(hover: hover) and (pointer: fine)").matches;

const prefersReduced =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export default function CustomCursor() {
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const dot = dotRef.current;
    const ring = ringRef.current;
    if (!dot || !ring) return;

    let mx = window.innerWidth / 2;
    let my = window.innerHeight / 2;
    let rx = mx;
    let ry = my;
    let raf = 0;

    const onMove = (e: PointerEvent) => {
      mx = e.clientX;
      my = e.clientY;
      dot.style.transform = `translate3d(${mx}px, ${my}px, 0) translate(-50%, -50%)`;
      const hot = !!(e.target as Element)?.closest?.(
        "a, button, [role='button'], input, label, .fx-spot",
      );
      ring.classList.toggle("zc-hot", hot);
    };

    const loop = () => {
      rx += (mx - rx) * 0.18; // trailing ring
      ry += (my - ry) * 0.18;
      ring.style.transform = `translate3d(${rx}px, ${ry}px, 0) translate(-50%, -50%)`;
      raf = requestAnimationFrame(loop);
    };

    const onLeave = () => {
      dot.style.opacity = "0";
      ring.style.opacity = "0";
    };
    const onEnter = () => {
      dot.style.opacity = "1";
      ring.style.opacity = "1";
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerleave", onLeave);
    document.addEventListener("pointerenter", onEnter);
    loop();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerleave", onLeave);
      document.removeEventListener("pointerenter", onEnter);
    };
  }, []);

  if (prefersReduced || !canHover) return null;
  return (
    <>
      <div ref={ringRef} className="zc-ring" aria-hidden />
      <div ref={dotRef} className="zc-dot" aria-hidden />
    </>
  );
}
