"use client";

import { useCallback, useRef, useState } from "react";

/* Two authored sample sites for one fictional business. Clearly illustrative. */

function OldSite() {
  return (
    <div className="pc-keep-shape absolute inset-0 overflow-hidden bg-[#e9edf2] font-[Times_New_Roman,serif] text-[#222]">
      <div className="bg-[#1d4f91] px-5 py-2 text-[13px] text-white">
        Call us: (512) 555-0142 &nbsp;|&nbsp; Mon–Fri 8am–5pm &nbsp;|&nbsp; <u>Patient Forms</u>
      </div>
      <div className="flex items-center justify-between border-b-4 border-[#f2b600] bg-white px-5 py-3">
        <span className="text-[26px] font-bold italic text-[#1d4f91]">Bluebell Dental</span>
        <span className="flex gap-4 text-[13px] text-[#1d4f91] underline">
          <span>Home</span>
          <span>About Us</span>
          <span>Services</span>
          <span>Insurance</span>
          <span>Contact</span>
        </span>
      </div>
      <div className="grid grid-cols-[1fr_200px] gap-4 p-5">
        <div>
          <h3 className="text-[22px] font-bold text-[#1d4f91]">Welcome to Our Practice!!</h3>
          <p className="mt-2 text-[13px] leading-snug">
            We are a family owned dental practice serving the Austin area since 1998. We offer a full range of dental services for the whole
            family including cleanings, fillings, crowns, bridges, dentures, root canals and much more. Please call our office to schedule.
          </p>
          <div className="mt-3 h-28 border border-[#999] bg-[repeating-linear-gradient(45deg,#cfd6df,#cfd6df_8px,#dde3ea_8px,#dde3ea_16px)]" />
          <p className="mt-3 text-[13px] text-[#1d4f91] underline">Click here to learn more about our services »</p>
        </div>
        <div className="space-y-2 text-[12px]">
          <div className="border border-[#999] bg-white p-2">
            <b>NEW PATIENTS</b>
            <br />
            Download forms (PDF)
          </div>
          <div className="border border-[#999] bg-[#fff8d6] p-2">
            <b>SPECIAL!</b> $99 cleaning + x-rays*
          </div>
          <div className="border border-[#999] bg-white p-2">We accept most insurance plans. Call for details.</div>
          <div className="border border-[#999] bg-white p-2">
            <b>HOURS</b>
            <br />
            Mon–Thu 8–5, Fri 8–12
            <br />
            Closed weekends
          </div>
        </div>
      </div>
      <div className="mx-5 grid grid-cols-3 gap-3 text-[12px]">
        {["Cleanings & Exams", "Crowns & Bridges", "Root Canals"].map((t) => (
          <div key={t} className="border border-[#999] bg-white p-2">
            <b className="text-[#1d4f91]">{t}</b>
            <p className="mt-1">Call our office for more information and pricing.</p>
          </div>
        ))}
      </div>
      <div className="absolute inset-x-0 bottom-0 bg-[#1d4f91] px-5 py-3 text-[11px] text-white/80">
        © 2011 Bluebell Dental. All rights reserved. | Site Map | Privacy Policy | Best viewed in Internet Explorer
      </div>
    </div>
  );
}

function NewSite() {
  return (
    <div className="pc-keep-shape absolute inset-0 overflow-hidden bg-[#f3efe7] text-[#1c2622]">
      <div className="flex items-center justify-between px-[6%] py-5 text-[13px]">
        <span className="font-semibold tracking-[-0.01em]">Bluebell Dental Studio</span>
        <span className="hidden gap-6 text-[#4d5852] sm:flex">
          <span>Care</span>
          <span>Team</span>
          <span>Visit</span>
        </span>
        <span className="rounded-full bg-[#1c2622] px-4 py-2 text-[12px] font-medium text-[#f3efe7]">Book a visit</span>
      </div>
      <div className="grid h-[calc(100%-68px)] grid-cols-[1.1fr_1fr] gap-[5%] px-[6%] pb-[6%]">
        <div className="flex flex-col justify-center">
          <p className="text-[11px] text-[#6b756f]">Family dentistry · South Austin</p>
          <h3 className="mt-3 font-serif text-[clamp(26px,3.6vw,48px)] leading-[1.02] tracking-[-0.02em]">Care that feels like a neighbor.</h3>
          <p className="mt-4 max-w-[34ch] text-[13px] leading-relaxed text-[#4d5852]">
            Same-week appointments, honest pricing, and a team that remembers your name.
          </p>
          <div className="mt-6 flex items-center gap-4 text-[12px]">
            <span className="rounded-full bg-[#1c2622] px-5 py-2.5 font-medium text-[#f3efe7]">Book online</span>
            <span className="text-[#4d5852]">Rated 4.9 by 312 patients</span>
          </div>
        </div>
        <div className="relative overflow-hidden rounded-[18px] bg-[linear-gradient(160deg,#c9d3c4,#7f957f_60%,#5c705d)]">
          <div className="absolute inset-x-[10%] bottom-[10%] rounded-xl bg-[#f3efe7]/90 p-4 text-[12px] backdrop-blur-sm">
            <p className="font-medium">Next opening</p>
            <p className="mt-0.5 text-[#4d5852]">Thursday, 9:30 am · Dr. Reyes</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export function Compare() {
  const box = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState(50);

  const move = useCallback((clientX: number) => {
    const r = box.current?.getBoundingClientRect();
    if (!r) return;
    setPos(Math.min(100, Math.max(0, ((clientX - r.left) / r.width) * 100)));
  }, []);

  return (
    <figure>
      <div
        ref={box}
        className="relative aspect-[16/10] w-full cursor-ew-resize touch-none select-none overflow-hidden border-[3px] border-ink bg-surface"
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture(e.pointerId);
          move(e.clientX);
        }}
        onPointerMove={(e) => e.buttons === 1 && move(e.clientX)}
      >
        <NewSite />
        <div className="absolute inset-0" style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}>
          <OldSite />
        </div>
        <div className="pointer-events-none absolute inset-y-0 w-[3px] -translate-x-1/2 bg-ink" style={{ left: `${pos}%` }}>
          <div className="absolute left-1/2 top-1/2 grid size-10 -translate-x-1/2 -translate-y-1/2 place-items-center bg-ink text-white">
            <svg viewBox="0 0 24 24" className="size-4 text-white" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="m9 7-5 5 5 5M15 7l5 5-5 5" />
            </svg>
          </div>
        </div>
        <span className="pointer-events-none absolute bottom-4 left-4 bg-ink/80 px-3 py-1 text-xs font-medium text-white backdrop-blur-sm">
          Their site today
        </span>
        <span className="pointer-events-none absolute bottom-4 right-4 bg-action px-3 py-1.5 text-xs font-semibold text-white">
          Pitchcraft prototype
        </span>
        <input
          type="range"
          min={0}
          max={100}
          value={pos}
          onChange={(e) => setPos(Number(e.target.value))}
          aria-label="Compare the current site with the Pitchcraft prototype"
          className="sr-only"
        />
      </div>
      <figcaption className="mt-4 text-center text-sm text-ink-3">Drag to compare. Illustrative example of a fictional business.</figcaption>
    </figure>
  );
}
