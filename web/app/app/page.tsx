"use client";

import Link from "next/link";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowRight, Download } from "lucide-react";
import { PHASES, batchName, timeAgo, usePoll, type Batch } from "@/lib/api";
import { AppShell, Crumb, ErrorState, Skeleton } from "@/components/ui";
import { UploadBatch } from "@/components/upload";

const STEPS = [
  {
    title: "Bring your leads",
    body: "A CSV with each business's name, website and vertical. Restaurants, dental, realtors and food & beverage are supported.",
  },
  {
    title: "Run the pipeline",
    body: "Pitchcraft audits every site, writes a brand brief, designs a new site and builds the audit and proposal PDFs.",
  },
  {
    title: "Review and approve",
    body: "Look at each redesign next to its audit. Approve the ones you'd put your name on. Only approved pitches go out.",
  },
];

function Onboarding({ first }: { first: boolean }) {
  return (
    <div className="m-auto w-full max-w-4xl" style={{ animation: "pc-in 500ms var(--ease-out-expo) both" }}>
      <h1 className="text-[36px] font-black leading-[0.95] tracking-[-0.03em] [word-spacing:0.06em] text-balance">
        {first ? "Your first batch takes about two minutes to set up." : "Start a new batch"}
      </h1>
      <p className="mt-2 max-w-xl text-[15px] text-ink-2 text-pretty">
        Upload a lead list and Pitchcraft turns every row into an audited, redesigned, ready-to-review pitch.
      </p>

      <ol className="mt-10 grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-3">
        {STEPS.map((s, i) => (
          <li key={s.title} className="bg-surface p-5">
            <span className="num grid size-6 place-items-center rounded-full border border-line-strong text-xs font-medium text-ink-2">{i + 1}</span>
            <h2 className="mt-4 text-[15px] font-semibold">{s.title}</h2>
            <p className="mt-1.5 text-sm leading-relaxed text-ink-2 text-pretty">{s.body}</p>
          </li>
        ))}
      </ol>

      <div className="mt-6">
        <UploadBatch />
      </div>
      <a
        href="/sample-leads.csv"
        download
        className="mt-4 inline-flex items-center gap-1.5 text-sm text-ink-2 underline decoration-line-strong underline-offset-4 hover:text-ink hover:decoration-ink"
      >
        <Download className="size-3.5" strokeWidth={2} /> Download a sample CSV to see the format
      </a>
    </div>
  );
}

function BatchTable({ data }: { data: Batch[] }) {
  return (
    <div className="min-h-0 flex-1 overflow-auto border border-ink bg-surface">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="sticky top-0 z-10 bg-surface">
          <tr className="border-b border-line text-xs text-ink-3">
            <th className="px-5 py-3 font-medium">Batch</th>
            <th className="px-3 py-3 font-medium">Progress</th>
            <th className="px-3 py-3 text-right font-medium">Leads</th>
            <th className="px-3 py-3 text-right font-medium">To review</th>
            <th className="px-3 py-3 text-right font-medium">Approved</th>
            <th className="px-5 py-3 text-right font-medium">Created</th>
          </tr>
        </thead>
        <tbody>
          {data.map((b) => {
            const steps = PHASES.length * b.total;
            const done = PHASES.reduce((n, p) => n + (b.phase_done[p.key] ?? 0), 0);
            const pct = steps ? Math.round((done / steps) * 100) : 0;
            return (
              <tr key={b.id} className="group border-b border-line last:border-0 hover:bg-ground">
                <td className="px-5 py-3.5">
                  <Link href={`/app/batches/${b.id}`} className="flex items-center gap-2 font-medium">
                    <span className="inline-block first-letter:uppercase">{batchName(b.id)}</span>
                    {b.run.state === "running" && <span className="pc-live size-1.5 rounded-full bg-action" aria-label="Running" />}
                    {b.run.state === "failed" && <span className="text-xs font-normal text-fail">Last run failed</span>}
                  </Link>
                </td>
                <td className="px-3 py-3.5">
                  <div className="flex items-center gap-3">
                    <div className="h-1.5 w-36 overflow-hidden rounded-full bg-sunken" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
                      <div className="h-full bg-ink" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="num w-9 text-ink-2">{pct}%</span>
                  </div>
                </td>
                <td className="num px-3 py-3.5 text-right">{b.total}</td>
                <td className={`num px-3 py-3.5 text-right ${b.to_review ? "font-medium text-action" : "text-ink-3"}`}>{b.to_review}</td>
                <td className="num px-3 py-3.5 text-right">{b.approved}</td>
                <td className="px-5 py-3.5 text-right text-ink-3">{timeAgo(b.created_at)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Dashboard() {
  const wantsNew = useSearchParams().get("new") === "1";
  const { data, error, loading, reload } = usePoll<Batch[]>("batches", 8000);

  if (loading && !data) return <Skeleton className="m-auto h-80 w-full max-w-4xl" />;
  if (error && !data) return <ErrorState error={error} onRetry={reload} />;
  if (!data || data.length === 0 || wantsNew) return <Onboarding first={!data?.length} />;

  const t = data.reduce(
    (a, b) => ({ leads: a.leads + b.total, review: a.review + b.to_review, approved: a.approved + b.approved, live: a.live + b.deployed }),
    { leads: 0, review: 0, approved: 0, live: 0 },
  );
  const next = data.find((b) => b.to_review > 0);

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="text-[36px] font-black leading-[0.95] tracking-[-0.03em] [word-spacing:0.06em]">Dashboard</h1>
          <p className="mt-1 text-[15px] text-ink-2">
            {t.review > 0 ? `${t.review} ${t.review === 1 ? "pitch is" : "pitches are"} ready for your review.` : "Nothing waiting on you right now."}
          </p>
        </div>
        {next && (
          <Link
            href={`/app/batches/${next.id}?filter=review`}
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-ink px-3.5 text-sm font-medium text-white transition-colors hover:bg-ink/90"
          >
            Start reviewing <ArrowRight className="size-4" strokeWidth={2} />
          </Link>
        )}
      </div>

      <dl className="mt-6 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-4">
        {(
          [
            ["Leads", t.leads],
            ["Ready to review", t.review],
            ["Approved", t.approved],
            ["Sites live", t.live],
          ] as const
        ).map(([k, v]) => (
          <div key={k} className="bg-surface px-5 py-4">
            <dt className="text-xs text-ink-3">{k}</dt>
            <dd className="num mt-1 text-[28px] font-black tracking-[-0.03em] [word-spacing:0.06em]">{v}</dd>
          </div>
        ))}
      </dl>

      <h2 className="mb-3 mt-8 text-sm font-medium text-ink-2">Batches</h2>
      <BatchTable data={data} />
    </>
  );
}

export default function DashboardPage() {
  return (
    <AppShell header={<Crumb>Dashboard</Crumb>}>
      <Suspense>
        <Dashboard />
      </Suspense>
    </AppShell>
  );
}
