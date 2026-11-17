"use client";

import { useEffect, useRef } from "react";

/* Decorative morphing mosaic. A fixed tree of splits fills the panel; each split's ratio drifts on its own
   slow sine, so tiles continuously grow, shrink and reshape while always filling the space, never overlapping,
   with constant white gaps. All black, one orange tile. */

type Node = { leaf: number } | { dir: "row" | "col"; speed: number; phase: number; a: Node; b: Node };
type Rect = { x: number; y: number; w: number; h: number };

const L = (leaf: number): Node => ({ leaf });
const S = (dir: "row" | "col", speed: number, phase: number, a: Node, b: Node): Node => ({ dir, speed, phase, a, b });

const TREE = S(
  "col", 0.21, 0.0,
  S("row", 0.33, 1.3, L(0), S("col", 0.27, 2.1, L(1), S("row", 0.39, 0.4, L(2), L(3)))),
  S("row", 0.24, 3.0, S("col", 0.36, 4.2, L(4), L(5)), S("col", 0.3, 5.1, S("row", 0.42, 2.7, L(6), L(7)), L(8))),
);
const LEAVES = 9;
const ORANGE = 3;
const GAP = 6;

// wide: swap every split's direction so the same tree suits a landscape panel.
function layout(n: Node, r: Rect, t: number, out: Rect[], wide: boolean) {
  if ("leaf" in n) {
    out[n.leaf] = r;
    return;
  }
  const k = 0.5 + 0.22 * Math.sin(t * n.speed + n.phase);
  if ((n.dir === "row") !== wide) {
    layout(n.a, { ...r, w: r.w * k }, t, out, wide);
    layout(n.b, { ...r, x: r.x + r.w * k, w: r.w * (1 - k) }, t, out, wide);
  } else {
    layout(n.a, { ...r, h: r.h * k }, t, out, wide);
    layout(n.b, { ...r, y: r.y + r.h * k, h: r.h * (1 - k) }, t, out, wide);
  }
}

function frame(t: number, wide: boolean) {
  const out: Rect[] = [];
  layout(TREE, { x: 0, y: 0, w: 100, h: 100 }, t, out, wide);
  return out;
}

const place = (r: Rect) => ({
  left: `calc(${r.x}% + ${GAP / 2}px)`,
  top: `calc(${r.y}% + ${GAP / 2}px)`,
  width: `calc(${r.w}% - ${GAP}px)`,
  height: `calc(${r.h}% - ${GAP}px)`,
});

export function Compose({ wide = false, speed = 1 }: { wide?: boolean; speed?: number }) {
  const first = frame(0, wide);
  const tiles = useRef<(HTMLSpanElement | null)[]>([]);

  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0;
    const t0 = performance.now();
    const tick = (now: number) => {
      frame(((now - t0) / 1000) * speed, wide).forEach((r, i) => {
        const el = tiles.current[i];
        if (el) Object.assign(el.style, place(r));
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [wide, speed]);

  return (
    <div className="relative" style={{ margin: -GAP / 2, width: `calc(100% + ${GAP}px)`, height: `calc(100% + ${GAP}px)` }} aria-hidden>
      {Array.from({ length: LEAVES }, (_, i) => (
        <span
          key={i}
          ref={(el) => {
            tiles.current[i] = el;
          }}
          className={`absolute ${i === ORANGE ? "bg-action" : "bg-ink"}`}
          style={place(first[i])}
        />
      ))}
    </div>
  );
}
