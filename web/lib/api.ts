"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export const PHASES = [
  { key: "audit", label: "Audit" },
  { key: "references", label: "References" },
  { key: "brief", label: "Brief" },
  { key: "screens", label: "Screens" },
  { key: "site", label: "Site" },
  { key: "deploy", label: "Deployed" },
  { key: "pdfs", label: "PDFs" },
] as const;

export type PhaseKey = (typeof PHASES)[number]["key"];
export type PhaseState = "done" | "waiting" | "pending";
export type Decision = "approved" | "rejected" | null;
export type RunState = { state: "idle" | "running" | "finished" | "failed"; log_updated_at: string | null };

export type Batch = {
  id: string;
  created_at: string | null;
  total: number;
  deployed: number;
  waiting: number;
  to_review: number;
  approved: number;
  rejected: number;
  phase_done: Record<PhaseKey, number>;
  run: RunState;
};

export type LeadRow = {
  lead_id: string;
  slug: string;
  business: string;
  vertical: string;
  site_url: string;
  email: string | null;
  location: string | null;
  phases: Record<PhaseKey, PhaseState>;
  problem_count: number;
  high_count: number;
  loss_low: number | null;
  loss_high: number | null;
  deploy_url: string | null;
  decision: Decision;
  updated_at: string | null;
};

export type Problem = { code: string; severity: "high" | "medium" | "low"; message: string; evidence?: string };

export type LeadDetail = {
  slug: string;
  phases: Record<PhaseKey, PhaseState>;
  audit: {
    url: string | null;
    vertical: string | null;
    audited_at: string | null;
    problems: Problem[];
    dollar_impact: { monthly_loss_low?: number; monthly_loss_high?: number } | null;
  };
  build: { deploy_url?: string | null } | null;
  decision: { decision: Decision; note: string; decided_at: string } | null;
  files: { audit_pdf: boolean; proposal_pdf: boolean; site: boolean };
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function detailMessage(body: unknown, status: number): string {
  const d = (body as { detail?: unknown })?.detail;
  if (typeof d === "string") return d;
  if (d && typeof d === "object" && "errors" in d) {
    const e = d as { errors: string[]; error_count: number };
    return e.errors.join("\n") + (e.error_count > e.errors.length ? `\n…and ${e.error_count - e.errors.length} more` : "");
  }
  return `Request failed (${status})`;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/pc/${path}`, { cache: "no-store", ...init });
  const body = await res.json().catch(() => null);
  if (res.status === 401) {
    // Full reload on purpose: drops all client state after session expiry.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
  }
  if (!res.ok) throw new ApiError(res.status, detailMessage(body, res.status));
  return body as T;
}

export function apiFile(slug: string, name: "audit.pdf" | "proposal.pdf" | "site") {
  return `/api/pc/leads/${encodeURIComponent(slug)}/file/${name}`;
}

/** Fetch + poll. Pauses while the tab is hidden. */
export function usePoll<T>(path: string | null, intervalMs = 5000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const alive = useRef(true);

  const load = useCallback(async () => {
    if (!path) return;
    try {
      const d = await api<T>(path);
      if (!alive.current) return;
      setData(d);
      setError(null);
    } catch (e) {
      if (alive.current) setError(e instanceof ApiError ? e : new ApiError(0, String(e)));
    } finally {
      if (alive.current) setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    alive.current = true;
    const first = setTimeout(load, 0);
    const t = setInterval(() => {
      if (document.visibilityState === "visible") load();
    }, intervalMs);
    return () => {
      alive.current = false;
      clearTimeout(first);
      clearInterval(t);
    };
  }, [load, intervalMs]);

  return { data, error, loading, reload: load };
}

export const money = (n: number | null | undefined) =>
  n == null ? "—" : n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function batchName(id: string) {
  // "20261117-0930-may-dentists" → "may dentists"
  const m = id.match(/^\d{8}-\d{4}-(.+)$/);
  return (m ? m[1] : id).replace(/[-_]+/g, " ");
}
