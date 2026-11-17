"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, LogOut, PlugZap } from "lucide-react";
import { PHASES, type ApiError, type PhaseKey, type PhaseState, type Decision } from "@/lib/api";
import type { ReactNode } from "react";

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2.5 rounded-md text-ink" aria-label="Pitchcraft home">
      <svg viewBox="0 0 32 32" className="size-7" aria-hidden>
        <rect width="32" height="32" rx="8" fill="var(--ink)" />
        <path d="M10 23V9h7a5 5 0 0 1 0 10h-7" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="22.5" cy="23" r="2.2" fill="#6d7cf0" />
      </svg>
      <span className="text-[15px] font-semibold tracking-[-0.01em]">Pitchcraft</span>
    </Link>
  );
}

export function Shell({ children, crumbs }: { children: ReactNode; crumbs?: ReactNode }) {
  const router = useRouter();
  async function signOut() {
    await fetch("/api/auth", { method: "DELETE" });
    router.push("/login");
  }
  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-20 border-b border-line bg-ground/90 backdrop-blur-sm">
        <div className="mx-auto flex h-14 max-w-[1320px] items-center gap-4 px-4 sm:px-6">
          <Logo />
          {crumbs && <span className="h-5 w-px bg-line-strong" aria-hidden />}
          <nav className="flex min-w-0 items-center gap-1.5 text-sm text-ink-3" aria-label="Breadcrumb">
            {crumbs}
          </nav>
          <button
            onClick={signOut}
            className="ml-auto inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm text-ink-3 transition-colors hover:bg-sunken hover:text-ink"
          >
            <LogOut className="size-4" strokeWidth={1.75} />
            <span className="hidden sm:inline">Sign out</span>
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-[1320px] px-4 pb-24 pt-8 sm:px-6 sm:pt-10">{children}</main>
    </div>
  );
}

const PHASE_STYLE: Record<PhaseState, string> = {
  done: "bg-done",
  waiting: "bg-wait",
  pending: "bg-line-strong/70",
};

/** Seven segments, one per pipeline phase. */
export function PhaseTrack({ phases, size = "sm" }: { phases: Record<PhaseKey, PhaseState>; size?: "sm" | "lg" }) {
  const done = PHASES.filter((p) => phases[p.key] === "done").length;
  const waiting = PHASES.find((p) => phases[p.key] === "waiting");
  const label = `${done} of ${PHASES.length} steps done${waiting ? `, waiting on ${waiting.label}` : ""}`;
  if (size === "lg") {
    return (
      <ol className="grid grid-cols-7 gap-1.5" aria-label={label}>
        {PHASES.map((p) => (
          <li key={p.key} className="min-w-0">
            <div className={`h-1.5 rounded-full ${PHASE_STYLE[phases[p.key]]}`} />
            <div
              className={`mt-2 truncate text-xs ${
                phases[p.key] === "pending" ? "text-ink-3" : phases[p.key] === "waiting" ? "font-medium text-wait" : "text-ink-2"
              }`}
            >
              {p.label}
            </div>
          </li>
        ))}
      </ol>
    );
  }
  return (
    <div className="flex items-center gap-[3px]" role="img" aria-label={label} title={label}>
      {PHASES.map((p) => (
        <span key={p.key} className={`h-2 w-3.5 rounded-[2px] ${PHASE_STYLE[phases[p.key]]}`} />
      ))}
    </div>
  );
}

export function DecisionBadge({ decision }: { decision: Decision }) {
  if (decision === "approved")
    return <span className="inline-flex items-center rounded-full bg-done-tint px-2 py-0.5 text-xs font-medium text-done">Approved</span>;
  if (decision === "rejected")
    return <span className="inline-flex items-center rounded-full bg-fail-tint px-2 py-0.5 text-xs font-medium text-fail">Rejected</span>;
  return <span className="text-xs text-ink-3">Not reviewed</span>;
}

export function Button({
  variant = "secondary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "danger" }) {
  const v = {
    primary: "bg-action text-white shadow-[0_1px_2px_rgb(18_22_31/0.16)] hover:bg-action-hover",
    secondary: "border border-line-strong bg-surface text-ink shadow-[0_1px_2px_rgb(18_22_31/0.05)] hover:bg-sunken",
    ghost: "text-ink-2 hover:bg-sunken hover:text-ink",
    danger: "border border-line-strong bg-surface text-fail hover:bg-fail-tint",
  }[variant];
  return (
    <button
      {...props}
      className={`inline-flex h-9 items-center justify-center gap-2 rounded-lg px-3.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${v} ${className}`}
    />
  );
}

export function ErrorState({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  const offline = error.status === 503 || error.status === 502;
  const Icon = offline ? PlugZap : AlertTriangle;
  return (
    <div className="rounded-xl border border-line bg-surface px-6 py-10 text-center">
      <Icon className={`mx-auto size-6 ${offline ? "text-wait" : "text-fail"}`} strokeWidth={1.75} />
      <h2 className="mt-3 text-base font-semibold text-balance">
        {offline ? "The pipeline server isn't connected" : "Something went wrong loading this"}
      </h2>
      <p className="mx-auto mt-1.5 max-w-md whitespace-pre-line text-sm text-ink-2 text-pretty">{error.message}</p>
      {offline && (
        <p className="mx-auto mt-3 max-w-md text-sm text-ink-3">
          Start it with <code className="rounded bg-sunken px-1.5 py-0.5 font-mono text-[13px] text-ink">uv run uvicorn api.server:app</code> and
          point <code className="font-mono text-[13px] text-ink">PITCHCRAFT_API_URL</code> at it.
        </p>
      )}
      {onRetry && (
        <Button className="mt-5" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`pc-live rounded-md bg-sunken ${className}`} />;
}
