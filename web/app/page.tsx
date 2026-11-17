"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { PHASES, batchName, timeAgo, usePoll, type Batch } from "@/lib/api";
import { ErrorState, Shell, Skeleton } from "@/components/ui";
import { UploadBatch } from "@/components/upload";

function RunTag({ run }: { run: Batch["run"] }) {
  if (run.state === "running")
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-action">
        <span className="pc-live size-1.5 rounded-full bg-action" /> Running
      </span>
    );
  if (run.state === "failed") return <span className="text-xs font-medium text-fail">Last run failed</span>;
  return null;
}

function Progress({ b }: { b: Batch }) {
  const steps = PHASES.length * b.total;
  const done = PHASES.reduce((n, p) => n + (b.phase_done[p.key] ?? 0), 0);
  const pct = steps ? Math.round((done / steps) * 100) : 0;
  return (
    <div className="flex items-center gap-3 sm:w-44" title={PHASES.map((p) => `${p.label}: ${b.phase_done[p.key] ?? 0}/${b.total}`).join(" · ")}>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-sunken" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Pipeline progress">
        <div className="h-full rounded-full bg-ink transition-[width] duration-700 ease-[var(--ease-out-expo)]" style={{ width: `${pct}%` }} />
      </div>
      <span className="num w-9 text-right text-sm text-ink-2">{pct}%</span>
    </div>
  );
}

export default function Home() {
  const { data, error, loading, reload } = usePoll<Batch[]>("batches", 8000);

  const totals = (data ?? []).reduce(
    (a, b) => ({ leads: a.leads + b.total, live: a.live + b.deployed, approved: a.approved + b.approved, review: a.review + b.to_review }),
    { leads: 0, live: 0, approved: 0, review: 0 },
  );

  return (
    <Shell>
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="text-[28px] font-semibold tracking-[-0.02em]">Batches</h1>
          <p className="mt-1 text-[15px] text-ink-2">Each batch is one lead list moving through audit, design, build and review.</p>
        </div>
        {data && data.length > 0 && (
          <dl className="flex gap-8 text-sm">
            {[
              ["Leads", totals.leads],
              ["Sites live", totals.live],
              ["Approved", totals.approved],
              ["Ready to review", totals.review],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="text-ink-3">{k}</dt>
                <dd className={`num mt-0.5 text-xl font-semibold tracking-[-0.01em] ${k === "Ready to review" && Number(v) > 0 ? "text-action" : ""}`}>
                  {v}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      <div className="mt-8">
        <UploadBatch compact={!!data?.length} />
      </div>

      <section className="mt-10" aria-label="All batches">
        {loading && !data && (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-[76px]" />
            ))}
          </div>
        )}
        {error && !data && <ErrorState error={error} onRetry={reload} />}
        {data && data.length === 0 && (
          <div className="rounded-xl border border-line bg-surface px-6 py-14 text-center">
            <h2 className="text-base font-semibold">No batches yet</h2>
            <p className="mx-auto mt-1.5 max-w-sm text-sm text-ink-2">
              Upload your first lead list above. Pitchcraft audits each site, designs a new one, and holds it for your review.
            </p>
          </div>
        )}
        {data && data.length > 0 && (
          <ul className="overflow-hidden rounded-xl border border-line bg-surface shadow-[0_1px_2px_rgb(18_22_31/0.04)]">
            {data.map((b) => (
              <li key={b.id} className="border-b border-line last:border-0">
                <Link
                  href={`/batches/${b.id}`}
                  className="group grid items-center gap-x-6 gap-y-3 px-5 py-4 transition-colors hover:bg-ground sm:grid-cols-[minmax(0,1fr)_auto_auto_20px]"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-3">
                      <span className="truncate text-[15px] font-medium first-letter:uppercase">{batchName(b.id)}</span>
                      <RunTag run={b.run} />
                    </div>
                    <div className="num mt-1 text-sm text-ink-3">
                      {b.total} leads · created {timeAgo(b.created_at)}
                    </div>
                  </div>
                  <Progress b={b} />
                  <div className="num flex gap-5 text-sm sm:w-56 sm:justify-end">
                    <span>
                      <span className="font-semibold text-ink">{b.approved}</span> <span className="text-ink-3">approved</span>
                    </span>
                    {b.to_review > 0 ? (
                      <span className="text-action">
                        <span className="font-semibold">{b.to_review}</span> to review
                      </span>
                    ) : b.waiting > 0 ? (
                      <span className="text-wait">
                        <span className="font-semibold">{b.waiting}</span> on Stitch
                      </span>
                    ) : (
                      <span className="text-ink-3">
                        <span className="font-semibold text-ink">{b.deployed}</span> live
                      </span>
                    )}
                  </div>
                  <ChevronRight className="hidden size-4 text-ink-3 transition-transform group-hover:translate-x-0.5 sm:block" />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </Shell>
  );
}
