"use client";

import { useEffect, useRef, useState } from "react";

/* Counts once to the real figure when scrolled into view. Reduced motion: final value immediately. */
export function Count({ to, prefix = "", duration = 1100 }: { to: number; prefix?: string; duration?: number }) {
  const el = useRef<HTMLSpanElement>(null);
  const [v, setV] = useState(to);

  useEffect(() => {
    const node = el.current;
    if (!node || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0;
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return;
        io.disconnect();
        const t0 = performance.now();
        const tick = (t: number) => {
          const p = Math.min(1, (t - t0) / duration);
          setV(Math.round(to * (1 - Math.pow(1 - p, 4))));
          if (p < 1) raf = requestAnimationFrame(tick);
        };
        setV(0);
        raf = requestAnimationFrame(tick);
      },
      { threshold: 0.6 },
    );
    io.observe(node);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [to, duration]);

  return (
    <span ref={el} className="num">
      {prefix}
      {v.toLocaleString("en-US")}
    </span>
  );
}
