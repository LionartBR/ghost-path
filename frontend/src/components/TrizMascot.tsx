/**TrizMascot — animated ASCII character with distance-based mouse interaction.
 *
 * Invariants:
 *   - Idle animation cycles 4 walking frames at 350ms intervals
 *   - Mouse distance calculated from mascot center via getBoundingClientRect
 *   - Zone transitions: idle (>200px) → curious (100-200px) → startled (<100px)
 *   - CSS custom properties drive continuous position updates (no React re-renders)
 *
 * Design Decisions:
 *   - Two-tier animation: CSS vars for mouse-driven flee, @keyframes for automatic bob (ADR: no transform conflict)
 *   - Outer div = flee transform, inner div = bob/jump keyframe — stacked, not competing
 *   - requestAnimationFrame wraps distance calc for frame-budget safety
 *   - React state only for discrete zone changes, not continuous mouse position
 */

import { useEffect, useRef, useState, useCallback } from "react";

type Zone = "idle" | "curious" | "startled";

const IDLE_FEET = [
  " ▘▘  ▝▝ ",
  "  ▘▘▝▝  ",
  "  ▝▝  ▘▘",
  "  ▘▘▝▝  ",
];

const STARTLED_FEET = "▘▘    ▝▝ ";

const HEAD = " ▐▛███▜▌ ";
const BODY = "▝▜█████▛▘";

const CURIOUS_THRESHOLD = 200;
const STARTLED_THRESHOLD = 100;
const MAX_FLEE_PX = 30;

export function TrizMascot() {
  const outerRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);
  const [zone, setZone] = useState<Zone>("idle");
  const [frame, setFrame] = useState(0);

  // --- idle walk cycle (350ms) ---
  useEffect(() => {
    if (zone === "curious") return;
    const ms = zone === "idle" ? 350 : 150;
    const id = setInterval(() => setFrame((f) => (f + 1) % 4), ms);
    return () => clearInterval(id);
  }, [zone]);

  // --- mouse distance tracking ---
  const trackMouse = useCallback((e: MouseEvent) => {
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      const el = outerRef.current;
      if (!el) return;

      const rect = el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = e.clientX - cx;
      const dy = e.clientY - cy;
      const dist = Math.sqrt(dx * dx + dy * dy);

      // continuous flee via CSS custom properties (no re-render)
      if (dist > 0 && dist < CURIOUS_THRESHOLD) {
        const intensity = (CURIOUS_THRESHOLD - dist) / CURIOUS_THRESHOLD;
        const flee = dist < STARTLED_THRESHOLD ? 1 : 0.3;
        const px = (-dx / dist) * intensity * flee * MAX_FLEE_PX;
        const py = dist < STARTLED_THRESHOLD ? -8 : (-dy / dist) * intensity * flee * 6;
        el.style.setProperty("--flee-x", `${px}px`);
        el.style.setProperty("--flee-y", `${py}px`);
      } else {
        el.style.setProperty("--flee-x", "0px");
        el.style.setProperty("--flee-y", "0px");
      }

      // discrete zone change (infrequent state update)
      const next: Zone =
        dist < STARTLED_THRESHOLD ? "startled" :
        dist < CURIOUS_THRESHOLD ? "curious" : "idle";
      setZone((prev) => (prev !== next ? next : prev));
    });
  }, []);

  useEffect(() => {
    document.addEventListener("mousemove", trackMouse);
    return () => {
      document.removeEventListener("mousemove", trackMouse);
      cancelAnimationFrame(rafRef.current);
    };
  }, [trackMouse]);

  // --- resolve current feet line ---
  const feet = zone === "startled" ? STARTLED_FEET : IDLE_FEET[frame];

  // --- pick inner animation class ---
  const bobClass =
    zone === "startled" ? "animate-mascot-jump" :
    zone === "curious" ? "animate-mascot-bob-slow" : "animate-mascot-bob";

  return (
    <div
      ref={outerRef}
      aria-hidden="true"
      className="inline-block transition-transform duration-200 ease-out"
      style={{ transform: "translate(var(--flee-x,0px),var(--flee-y,0px))" }}
    >
      <div className={bobClass}>
        <pre className="font-mono text-sm leading-tight select-none m-0">
          <span className="text-indigo-600">{HEAD}</span>
          {"\n"}
          <span className="text-indigo-500">{BODY}</span>
          {"\n"}
          <span className="text-indigo-300">{feet}</span>
        </pre>
      </div>
    </div>
  );
}
