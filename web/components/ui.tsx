"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AlertTriangle, BookOpen, LayoutGrid, LogOut, PlugZap, Plus } from "lucide-react";
import { PHASES, batchName, usePoll, type ApiError, type Batch, type Decision, type PhaseKey, type PhaseState } from "@/lib/api";
import type { ReactNode } from "react";

export function Mark({ className = "size-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <rect width="32" height="32" fill="var(--ink)" />
      <path d="M10 24V8h7.5a5.5 5.5 0 0 1 0 11H10" fill="none" stroke="#fff" strokeWidth="3.2" strokeLinejoin="miter" />
      <rect x="21" y="21" width="4" height="4" fill="var(--action)" />
    </svg>
  );
}

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="flex items-center gap-2.5 rounded-md text-ink" aria-label="Pitchcraft">
      <Mark />
      <span className="text-[17px] font-black tracking-[-0.03em]">Pitchcraft</span>
    </Link>
  );
}

function NavItem({ href, icon: Icon, children, active }: { href: string; icon: typeof LayoutGrid; children: ReactNode; active: boolean }) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`flex h-9 items-center gap-2.5 rounded-lg px-2.5 text-sm transition-colors ${
        active ? "bg-sunken font-semibold text-ink" : "text-ink-2 hover:bg-sunken hover:text-ink"
      }`}
    >
      <Icon className="size-4" strokeWidth={1.75} />
      {children}
    </Link>
  );
}

/** Full-viewport app frame: fixed sidebar, main column that owns its own scrolling. */
export function AppShell({ children, header }: { children: ReactNode; header?: ReactNode }) {
  const router = useRouter();
  const path = usePathname();
  const { data: batches } = usePoll<Batch[]>("batches", 15000);

  async function signOut() {
    await fetch("/api/auth", { method: "DELETE" });
    router.push("/login");
  }

  return (
    <div className="flex h-dvh overflow-hidden">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-ink bg-surface px-3 py-4 md:flex">
        <div className="px-2">
          <Logo href="/app" />
        </div>
        <Link
          href="/app?new=1"
          className="mt-6 flex h-9 items-center justify-center gap-2 rounded-lg bg-ink text-sm font-medium text-white transition-colors hover:bg-ink/90"
        >
          <Plus className="size-4" strokeWidth={2} /> New batch
        </Link>
        <nav className="mt-5 space-y-0.5" aria-label="Main">
          <NavItem href="/app" icon={LayoutGrid} active={path === "/app"}>
            Dashboard
          </NavItem>
          <NavItem href="/app/guide" icon={BookOpen} active={path === "/app/guide"}>
            How it works
          </NavItem>
        </nav>
        {batches && batches.length > 0 && (
          <div className="mt-7 min-h-0 flex-1 overflow-y-auto">
            <p className="px-2.5 text-xs font-medium text-ink-3">Recent batches</p>
            <ul className="mt-2 space-y-0.5">
              {batches.slice(0, 12).map((b) => {
                const active = path.startsWith(`/app/batches/${b.id}`);
                return (
                  <li key={b.id}>
                    <Link
                      href={`/app/batches/${b.id}`}
                      className={`flex h-8 items-center gap-2 rounded-lg px-2.5 text-sm transition-colors ${
                        active ? "bg-sunken font-medium text-ink" : "text-ink-2 hover:bg-sunken hover:text-ink"
                      }`}
                    >
                      <span
                        className={`size-1.5 shrink-0 rounded-full ${
                          b.run.state === "running" ? "pc-live bg-action" : b.to_review > 0 ? "bg-action" : "bg-line-strong"
                        }`}
                      />
                      <span className="block truncate first-letter:uppercase">{batchName(b.id)}</span>
                      {b.to_review > 0 && <span className="num ml-auto text-xs text-ink-3">{b.to_review}</span>}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
        <button
          onClick={signOut}
          className="mt-auto flex h-9 items-center gap-2.5 rounded-lg px-2.5 text-sm text-ink-3 transition-colors hover:bg-sunken hover:text-ink"
        >
          <LogOut className="size-4" strokeWidth={1.75} /> Sign out
        </button>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-ink px-4 sm:px-6">
          <span className="md:hidden">
            <Link href="/app" aria-label="Dashboard">
              <Mark className="size-6" />
            </Link>
          </span>
          <nav className="flex min-w-0 items-center gap-1.5 text-sm text-ink-3" aria-label="Breadcrumb">
            {header}
          </nav>
        </header>
        <main className="flex min-h-0 flex-1 flex-col px-4 py-6 sm:px-8">{children}</main>
      </div>
    </div>
  );
}

const PHASE_STYLE: Record<PhaseState, string> = {
  done: "bg-ink",
  waiting: "bg-action",
  pending: "border border-ink/35",
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
            <div className={`h-1 rounded-full ${PHASE_STYLE[phases[p.key]]}`} />
            <div
              className={`mt-1.5 truncate text-[11px] ${
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
    return <span className="inline-flex items-center bg-ink px-2 py-0.5 text-xs font-semibold uppercase tracking-[0.04em] text-white">Approved</span>;
  if (decision === "rejected")
    return <span className="text-xs uppercase tracking-[0.04em] text-ink-3 line-through">Rejected</span>;
  return <span className="text-xs text-ink-3">Not reviewed</span>;
}

export function Button({
  variant = "secondary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "danger" }) {
  const v = {
    primary: "bg-ink text-white hover:bg-ink/90",
    secondary: "border border-ink bg-surface text-ink hover:bg-sunken",
    ghost: "text-ink-2 hover:bg-sunken hover:text-ink",
    danger: "border border-ink bg-surface text-ink hover:bg-sunken",
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
    <div className="m-auto max-w-md border border-ink bg-surface px-6 py-10 text-center">
      <Icon className={`mx-auto size-6 ${offline ? "text-wait" : "text-fail"}`} strokeWidth={1.75} />
      <h2 className="mt-3 text-base font-semibold text-balance">
        {offline ? "The pipeline server isn't reachable" : "Something went wrong loading this"}
      </h2>
      <p className="mt-1.5 whitespace-pre-line text-sm text-ink-2 text-pretty">
        {offline ? "It may be waking up. This can take up to a minute on the first request." : error.message}
      </p>
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

export function Crumb({ href, children }: { href?: string; children: ReactNode }) {
  return href ? (
    <Link href={href} className="truncate rounded first-letter:uppercase hover:text-ink">
      {children}
    </Link>
  ) : (
    <span className="truncate text-ink first-letter:uppercase">{children}</span>
  );
}
