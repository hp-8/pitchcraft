"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Check, ChevronLeft, ChevronRight, ExternalLink, FileText, Monitor, Smartphone, Undo2, X } from "lucide-react";
import {
  api,
  ApiError,
  apiFile,
  batchName,
  money,
  timeAgo,
  usePoll,
  type Decision,
  type LeadDetail,
  type LeadRow,
  type Problem,
} from "@/lib/api";
import { Button, DecisionBadge, ErrorState, PhaseTrack, Shell, Skeleton } from "@/components/ui";

const SEV: Record<Problem["severity"], string> = {
  high: "bg-fail-tint text-fail",
  medium: "bg-wait-tint text-wait",
  low: "bg-sunken text-ink-2",
};

function Preview({ lead }: { lead: LeadDetail }) {
  const [device, setDevice] = useState<"desktop" | "mobile">("desktop");
  const live = lead.build?.deploy_url ?? null;
  const src = live ?? (lead.files.site ? apiFile(lead.slug, "site") : null);

  return (
    <div className="overflow-hidden rounded-xl border border-line bg-surface shadow-[0_1px_2px_rgb(18_22_31/0.04),0_8px_24px_-12px_rgb(18_22_31/0.12)]">
      <div className="flex items-center gap-3 border-b border-line px-3 py-2">
        <div className="flex gap-1.5 pl-1" aria-hidden>
          <span className="size-2.5 rounded-full bg-line-strong" />
          <span className="size-2.5 rounded-full bg-line-strong" />
          <span className="size-2.5 rounded-full bg-line-strong" />
        </div>
        <div className="min-w-0 flex-1 truncate rounded-md bg-sunken px-3 py-1 text-center font-mono text-xs text-ink-2">
          {live ? live.replace(/^https?:\/\//, "") : src ? "local build (not deployed)" : "no prototype yet"}
        </div>
        <div className="flex rounded-md bg-sunken p-0.5" role="group" aria-label="Preview size">
          {(
            [
              ["desktop", Monitor],
              ["mobile", Smartphone],
            ] as const
          ).map(([d, Icon]) => (
            <button
              key={d}
              onClick={() => setDevice(d)}
              aria-pressed={device === d}
              aria-label={`${d} preview`}
              className={`rounded p-1 ${device === d ? "bg-surface text-ink shadow-sm" : "text-ink-3 hover:text-ink"}`}
            >
              <Icon className="size-4" strokeWidth={1.75} />
            </button>
          ))}
        </div>
        {live && (
          <a href={live} target="_blank" rel="noreferrer" className="rounded p-1 text-ink-3 hover:bg-sunken hover:text-ink" aria-label="Open live site">
            <ExternalLink className="size-4" strokeWidth={1.75} />
          </a>
        )}
      </div>
      <div className="flex h-[min(72vh,760px)] justify-center bg-sunken">
        {src ? (
          <iframe
            key={device}
            src={src}
            title="Prototype preview"
            sandbox="allow-scripts allow-same-origin"
            className={`h-full bg-white transition-[width] duration-500 ease-[var(--ease-out-expo)] ${
              device === "mobile" ? "my-4 h-[calc(100%-2rem)] w-[390px] rounded-[20px] border border-line-strong" : "w-full"
            }`}
          />
        ) : (
          <div className="grid place-items-center px-6 text-center">
            <div>
              <p className="font-medium">The prototype hasn&apos;t been built yet</p>
              <p className="mt-1 max-w-xs text-sm text-ink-2">It shows up here once Screens and Site are done.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function LeadView({ slug }: { slug: string }) {
  const router = useRouter();
  const batch = useSearchParams().get("batch");
  const { data: lead, error, loading, reload } = usePoll<LeadDetail>(`leads/${slug}`, 10000);
  const { data: batchData } = usePoll<{ leads: LeadRow[] }>(batch ? `batches/${batch}` : null, 30000);
  const [noteDraft, setNote] = useState<string | null>(null);
  const [saving, setSaving] = useState<Decision | "clear" | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const rows = batchData?.leads ?? [];
  const idx = rows.findIndex((r) => r.slug === slug);
  const row = idx >= 0 ? rows[idx] : null;
  const prev = idx > 0 ? rows[idx - 1] : null;
  const next = idx >= 0 && idx < rows.length - 1 ? rows[idx + 1] : null;
  const href = (s: string) => `/leads/${s}${batch ? `?batch=${batch}` : ""}`;

  const note = noteDraft ?? lead?.decision?.note ?? "";

  const decide = useCallback(
    async (decision: Decision) => {
      setSaving(decision ?? "clear");
      setSaveError(null);
      try {
        await api(`leads/${slug}/decision`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ decision, note }),
        });
        await reload();
        if (decision && next) router.push(href(next.slug));
      } catch (e) {
        setSaveError(e instanceof ApiError ? e.message : String(e));
      } finally {
        setSaving(null);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [slug, note, next, reload],
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLInputElement || e.metaKey || e.ctrlKey) return;
      if (e.key === "a") decide("approved");
      else if (e.key === "r") decide("rejected");
      else if (e.key === "j" && next) router.push(href(next.slug));
      else if (e.key === "k" && prev) router.push(href(prev.slug));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [decide, next, prev]);

  const title = row?.business ?? slug.replace(/-/g, ".");
  const problems = [...(lead?.audit.problems ?? [])].sort(
    (a, b) => ["high", "medium", "low"].indexOf(a.severity) - ["high", "medium", "low"].indexOf(b.severity),
  );
  const impact = lead?.audit.dollar_impact;

  return (
    <Shell
      crumbs={
        <>
          <Link href="/" className="rounded hover:text-ink">
            Batches
          </Link>
          {batch && (
            <>
              <ChevronRight className="size-3.5" />
              <Link href={`/batches/${batch}`} className="truncate rounded first-letter:uppercase hover:text-ink">
                {batchName(batch)}
              </Link>
            </>
          )}
          <ChevronRight className="size-3.5" />
          <span className="truncate text-ink">{title}</span>
        </>
      }
    >
      {error && !lead && <ErrorState error={error} onRetry={reload} />}
      {loading && !lead && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
          <Skeleton className="h-[72vh]" />
          <Skeleton className="h-96" />
        </div>
      )}
      {lead && (
        <>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <h1 className="truncate text-[28px] font-semibold tracking-[-0.02em]">{title}</h1>
              <p className="mt-1 text-[15px] text-ink-2">
                <span className="capitalize">{lead.audit.vertical ?? row?.vertical}</span>
                {row?.location && ` · ${row.location}`}
                {lead.audit.url && (
                  <>
                    {" · "}
                    <a href={lead.audit.url} target="_blank" rel="noreferrer" className="underline decoration-line-strong hover:decoration-ink">
                      current site
                    </a>
                  </>
                )}
              </p>
            </div>
            {batch && idx >= 0 && (
              <div className="num flex items-center gap-2 text-sm text-ink-3">
                <span>
                  {idx + 1} of {rows.length}
                </span>
                <Button variant="secondary" className="w-9 px-0" disabled={!prev} onClick={() => prev && router.push(href(prev.slug))} aria-label="Previous lead (K)">
                  <ChevronLeft className="size-4" />
                </Button>
                <Button variant="secondary" className="w-9 px-0" disabled={!next} onClick={() => next && router.push(href(next.slug))} aria-label="Next lead (J)">
                  <ChevronRight className="size-4" />
                </Button>
              </div>
            )}
          </div>

          <div className="mt-6 max-w-2xl">
            <PhaseTrack phases={lead.phases} size="lg" />
          </div>

          <div className="mt-8 grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
            <Preview lead={lead} />

            <aside className="space-y-4 lg:sticky lg:top-20">
              <section className="rounded-xl border border-line bg-surface p-5" aria-label="Review">
                <div className="flex items-center justify-between">
                  <h2 className="text-[15px] font-semibold">Your review</h2>
                  <DecisionBadge decision={lead.decision?.decision ?? null} />
                </div>
                <label htmlFor="note" className="mt-4 block text-sm text-ink-2">
                  Note (optional)
                </label>
                <textarea
                  id="note"
                  rows={2}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="e.g. hero photo feels generic"
                  className="mt-1.5 w-full resize-none rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm outline-none placeholder:text-ink-3 focus:border-action focus:ring-4 focus:ring-action/15"
                />
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <Button variant="danger" onClick={() => decide("rejected")} disabled={!!saving}>
                    <X className="size-4" strokeWidth={2} /> Reject
                  </Button>
                  <Button variant="primary" onClick={() => decide("approved")} disabled={!!saving}>
                    <Check className="size-4" strokeWidth={2} /> Approve
                  </Button>
                </div>
                {lead.decision?.decision && (
                  <button
                    onClick={() => decide(null)}
                    disabled={!!saving}
                    className="mt-3 inline-flex items-center gap-1.5 text-xs text-ink-3 hover:text-ink"
                  >
                    <Undo2 className="size-3.5" /> Clear decision ({timeAgo(lead.decision.decided_at)})
                  </button>
                )}
                {saveError && (
                  <p role="alert" className="mt-3 text-sm text-fail">
                    {saveError}
                  </p>
                )}
                <p className="mt-4 border-t border-line pt-3 text-xs text-ink-3">
                  Keys: <kbd className="font-mono text-ink-2">A</kbd> approve · <kbd className="font-mono text-ink-2">R</kbd> reject ·{" "}
                  <kbd className="font-mono text-ink-2">J</kbd>/<kbd className="font-mono text-ink-2">K</kbd> next/previous
                </p>
              </section>

              <section className="rounded-xl border border-line bg-surface p-5" aria-label="Audit findings">
                <div className="flex items-baseline justify-between gap-3">
                  <h2 className="text-[15px] font-semibold">Audit findings</h2>
                  {lead.audit.audited_at && <span className="text-xs text-ink-3">{timeAgo(lead.audit.audited_at)}</span>}
                </div>
                {impact?.monthly_loss_low != null && (
                  <p className="mt-3 text-sm text-ink-2">
                    Estimated revenue lost each month:{" "}
                    <span className="num font-semibold text-ink">
                      {money(impact.monthly_loss_low)}–{money(impact.monthly_loss_high)}
                    </span>
                  </p>
                )}
                {problems.length > 0 ? (
                  <ul className="mt-4 space-y-3">
                    {problems.map((p) => (
                      <li key={p.code} className="flex gap-3 text-sm">
                        <span className={`mt-px h-fit shrink-0 rounded px-1.5 py-0.5 text-[11px] font-medium capitalize ${SEV[p.severity]}`}>
                          {p.severity}
                        </span>
                        <span className="text-ink-2 text-pretty">{p.message}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-sm text-ink-3">{lead.phases.audit === "done" ? "No issues found." : "Audit hasn't run yet."}</p>
                )}
              </section>

              <section className="rounded-xl border border-line bg-surface p-5" aria-label="Documents">
                <h2 className="text-[15px] font-semibold">Documents</h2>
                <div className="mt-3 space-y-1">
                  {(
                    [
                      ["audit.pdf", "Revenue audit", lead.files.audit_pdf],
                      ["proposal.pdf", "Growth proposal", lead.files.proposal_pdf],
                    ] as const
                  ).map(([file, label, ok]) =>
                    ok ? (
                      <a
                        key={file}
                        href={apiFile(slug, file)}
                        target="_blank"
                        rel="noreferrer"
                        className="-mx-2 flex items-center gap-3 rounded-lg px-2 py-2 text-sm transition-colors hover:bg-sunken"
                      >
                        <FileText className="size-4 text-ink-2" strokeWidth={1.75} />
                        <span className="font-medium">{label}</span>
                        <span className="ml-auto text-xs text-ink-3">PDF</span>
                      </a>
                    ) : (
                      <div key={file} className="-mx-2 flex items-center gap-3 px-2 py-2 text-sm text-ink-3">
                        <FileText className="size-4" strokeWidth={1.75} />
                        {label}
                        <span className="ml-auto text-xs">Not generated</span>
                      </div>
                    ),
                  )}
                </div>
              </section>
            </aside>
          </div>
        </>
      )}
    </Shell>
  );
}

function KeyedLead() {
  const { slug } = useParams<{ slug: string }>();
  return <LeadView key={slug} slug={slug} />;
}

export default function LeadPage() {
  return (
    <Suspense>
      <KeyedLead />
    </Suspense>
  );
}
