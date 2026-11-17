"use client";

import Link from "next/link";
import { Suspense, useMemo, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { ChevronRight, Loader2, Play, RotateCw, ScrollText, Search, X } from "lucide-react";
import { api, ApiError, batchName, money, usePoll, type LeadRow, type RunState } from "@/lib/api";
import { AppShell, Button, Crumb, DecisionBadge, ErrorState, PhaseTrack, Skeleton } from "@/components/ui";

type BatchDetail = { id: string; leads: LeadRow[]; run: RunState };

const FILTERS = [
  { key: "all", label: "All" },
  { key: "review", label: "Ready to review" },
  { key: "waiting", label: "Waiting on Stitch" },
  { key: "approved", label: "Approved" },
  { key: "rejected", label: "Rejected" },
] as const;
type FilterKey = (typeof FILTERS)[number]["key"];

const PAGE = 50;

function matches(l: LeadRow, f: FilterKey) {
  switch (f) {
    case "review":
      return l.decision === null && l.phases.site === "done";
    case "waiting":
      return Object.values(l.phases).includes("waiting");
    case "approved":
      return l.decision === "approved";
    case "rejected":
      return l.decision === "rejected";
    default:
      return true;
  }
}

function LogDrawer({ id, onClose }: { id: string; onClose: () => void }) {
  const { data } = usePoll<{ lines: string[] }>(`batches/${id}/log`, 3000);
  return (
    <aside
      className="fixed inset-y-0 right-0 z-30 flex w-full max-w-xl flex-col border-l border-white/10 bg-ink"
      style={{ animation: "pc-in 250ms var(--ease-out-expo) both" }}
      aria-label="Run log"
    >
      <div className="flex h-14 items-center justify-between border-b border-white/10 px-5">
        <span className="text-sm font-medium text-white/90">Run log</span>
        <button onClick={onClose} className="rounded p-1.5 text-white/60 hover:bg-white/10 hover:text-white" aria-label="Close log">
          <X className="size-4" />
        </button>
      </div>
      <pre className="min-h-0 flex-1 overflow-auto px-5 py-4 font-mono text-xs leading-relaxed text-white/75">
        {data?.lines.length ? data.lines.join("\n") : "No output yet. Start a run to see pipeline output here."}
      </pre>
    </aside>
  );
}

function BatchView() {
  const { id } = useParams<{ id: string }>();
  const initial = useSearchParams().get("filter") as FilterKey | null;
  const router = useRouter();
  const { data, error, loading, reload } = usePoll<BatchDetail>(`batches/${id}`, 5000);
  const [filter, setFilter] = useState<FilterKey>(FILTERS.some((f) => f.key === initial) ? initial! : "all");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(0);
  const [showLog, setShowLog] = useState(false);
  const [busy, setBusy] = useState<"run" | "resume" | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const leads = useMemo(() => data?.leads ?? [], [data]);
  const counts = useMemo(
    () => Object.fromEntries(FILTERS.map((f) => [f.key, leads.filter((l) => matches(l, f.key)).length])) as Record<FilterKey, number>,
    [leads],
  );
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return leads.filter(
      (l) => matches(l, filter) && (!needle || [l.business, l.site_url, l.location, l.lead_id].some((s) => s?.toLowerCase().includes(needle))),
    );
  }, [leads, filter, q]);
  const pages = Math.max(1, Math.ceil(shown.length / PAGE));
  const slice = shown.slice(page * PAGE, page * PAGE + PAGE);

  async function start(mode: "run" | "resume") {
    setBusy(mode);
    setRunError(null);
    try {
      await api(`batches/${id}/run`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ mode }) });
      setShowLog(true);
      reload();
    } catch (e) {
      setRunError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  const running = data?.run.state === "running";
  const anyStarted = leads.some((l) => l.phases.audit === "done");
  const leadHref = (slug: string) => `/app/leads/${slug}?batch=${id}`;

  return (
    <AppShell
      header={
        <>
          <Crumb href="/app">Dashboard</Crumb>
          <ChevronRight className="size-3.5 shrink-0" />
          <Crumb>{batchName(id)}</Crumb>
        </>
      }
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-[36px] font-black leading-[0.95] tracking-[-0.03em] [word-spacing:0.06em] first-letter:uppercase">{batchName(id)}</h1>
          <p className="num mt-1 text-[15px] text-ink-2">
            {data ? `${leads.length} leads` : "Loading…"}
            {running && (
              <span className="ml-3 inline-flex items-center gap-1.5 font-medium text-action">
                <span className="pc-live size-1.5 rounded-full bg-action" /> Pipeline running
              </span>
            )}
            {data?.run.state === "failed" && <span className="ml-3 font-medium text-fail">Last run failed. Open the log for details.</span>}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" onClick={() => setShowLog(true)}>
            <ScrollText className="size-4" strokeWidth={1.75} /> Log
          </Button>
          {anyStarted && (
            <Button onClick={() => start("resume")} disabled={running || !!busy}>
              {busy === "resume" ? <Loader2 className="size-4 animate-spin" /> : <RotateCw className="size-4" strokeWidth={1.75} />}
              Resume after Stitch
            </Button>
          )}
          <Button variant="primary" onClick={() => start("run")} disabled={running || !!busy}>
            {busy === "run" ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" strokeWidth={2} />}
            {anyStarted ? "Run again" : "Start pipeline"}
          </Button>
        </div>
      </div>

      {runError && (
        <p role="alert" className="mt-4 rounded-lg bg-fail-tint px-4 py-2.5 text-sm text-fail">
          {runError}
        </p>
      )}
      {counts.waiting > 0 && (
        <p className="mt-4 rounded-lg border border-wait/25 bg-wait-tint px-4 py-2.5 text-sm text-ink-2">
          <span className="font-medium text-wait">
            {counts.waiting} {counts.waiting === 1 ? "lead is" : "leads are"} waiting on Stitch screens.
          </span>{" "}
          Run <code className="rounded bg-surface/70 px-1.5 py-0.5 font-mono text-[13px] text-ink">/stitch-batch</code> in Claude Code, then Resume
          after Stitch.
        </p>
      )}

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <div role="tablist" aria-label="Filter leads" className="flex flex-wrap gap-1 rounded-lg bg-sunken p-1">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              role="tab"
              aria-selected={filter === f.key}
              onClick={() => {
                setFilter(f.key);
                setPage(0);
              }}
              className={`num inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-sm transition-colors ${
                filter === f.key ? "bg-surface font-medium text-ink" : "text-ink-2 hover:text-ink"
              }`}
            >
              {f.label}
              <span className="text-ink-3">{counts[f.key] ?? 0}</span>
            </button>
          ))}
        </div>
        <label className="relative ml-auto w-full sm:w-72">
          <span className="sr-only">Search leads</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-3" strokeWidth={1.75} />
          <input
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(0);
            }}
            placeholder="Search business, site or city"
            className="h-9 w-full rounded-lg border border-line-strong bg-surface pl-9 pr-3 text-sm outline-none placeholder:text-ink-3 focus:border-action focus:ring-4 focus:ring-action/15"
          />
        </label>
      </div>

      <section className="mt-4 flex min-h-0 flex-1 flex-col">
        {loading && !data && <Skeleton className="flex-1" />}
        {error && !data && <ErrorState error={error} onRetry={reload} />}
        {data && (
          <div className="min-h-0 flex-1 overflow-auto border border-ink bg-surface">
            <table className="w-full min-w-[860px] text-left text-sm">
              <thead className="sticky top-0 z-10 bg-surface">
                <tr className="border-b border-line text-xs text-ink-3">
                  <th className="px-5 py-3 font-medium">Business</th>
                  <th className="px-3 py-3 font-medium">Progress</th>
                  <th className="px-3 py-3 text-right font-medium">Issues</th>
                  <th className="px-3 py-3 text-right font-medium">Est. monthly loss</th>
                  <th className="px-3 py-3 font-medium">Review</th>
                  <th className="w-10" />
                </tr>
              </thead>
              <tbody>
                {slice.map((l) => (
                  <tr
                    key={l.lead_id}
                    onClick={() => router.push(leadHref(l.slug))}
                    className="group cursor-pointer border-b border-line transition-colors last:border-0 hover:bg-ground"
                  >
                    <td className="max-w-[320px] px-5 py-3">
                      <Link href={leadHref(l.slug)} className="block truncate font-medium text-ink" onClick={(e) => e.stopPropagation()}>
                        {l.business}
                      </Link>
                      <div className="mt-0.5 truncate text-xs text-ink-3">
                        <span className="capitalize">{l.vertical}</span>
                        {l.location && ` · ${l.location}`} · {l.site_url.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "")}
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <PhaseTrack phases={l.phases} />
                    </td>
                    <td className="num px-3 py-3 text-right">
                      {l.phases.audit === "done" ? (
                        <>
                          {l.problem_count}
                          {l.high_count > 0 && <span className="ml-1.5 text-xs text-fail">{l.high_count} high</span>}
                        </>
                      ) : (
                        <span className="text-ink-3">—</span>
                      )}
                    </td>
                    <td className="num px-3 py-3 text-right text-ink-2">
                      {l.loss_low != null ? `${money(l.loss_low)}–${money(l.loss_high)}` : <span className="text-ink-3">—</span>}
                    </td>
                    <td className="px-3 py-3">
                      <DecisionBadge decision={l.decision} />
                    </td>
                    <td className="pr-4">
                      <ChevronRight className="size-4 text-ink-3 transition-transform group-hover:translate-x-0.5" />
                    </td>
                  </tr>
                ))}
                {slice.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-5 py-14 text-center text-sm text-ink-2">
                      {q ? `No leads match “${q}”.` : filter === "review" ? "Nothing to review yet. Leads appear here once their site is built." : "No leads in this view."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        {data && pages > 1 && (
          <div className="num mt-3 flex items-center justify-between text-sm text-ink-2">
            <span>
              {page * PAGE + 1}–{Math.min(shown.length, (page + 1) * PAGE)} of {shown.length}
            </span>
            <div className="flex gap-2">
              <Button disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                Previous
              </Button>
              <Button disabled={page >= pages - 1} onClick={() => setPage((p) => p + 1)}>
                Next
              </Button>
            </div>
          </div>
        )}
      </section>

      {showLog && <LogDrawer id={id} onClose={() => setShowLog(false)} />}
    </AppShell>
  );
}

export default function BatchPage() {
  return (
    <Suspense>
      <BatchView />
    </Suspense>
  );
}
