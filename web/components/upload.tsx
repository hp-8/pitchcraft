"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FileUp, Loader2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";

const COLUMNS = "lead_id, business, vertical, site_url";

export function UploadBatch({ compact = false }: { compact?: boolean }) {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(file: File | undefined) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("That file isn't a CSV. Export your lead list as .csv and try again.");
      return;
    }
    setBusy(true);
    setError(null);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await api<{ id: string }>("batches", { method: "POST", body: fd });
      router.push(`/batches/${res.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Upload failed. Try again.");
      setBusy(false);
    } finally {
      if (input.current) input.current.value = "";
    }
  }

  return (
    <div>
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          send(e.dataTransfer.files[0]);
        }}
        className={`group flex cursor-pointer items-center gap-4 rounded-xl border border-dashed px-5 transition-colors ${
          compact ? "py-4" : "py-6"
        } ${over ? "border-action bg-action-tint" : "border-line-strong bg-surface hover:border-ink-3"}`}
      >
        <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-sunken text-ink-2 transition-colors group-hover:text-ink">
          {busy ? <Loader2 className="size-5 animate-spin" /> : <FileUp className="size-5" strokeWidth={1.75} />}
        </span>
        <span className="min-w-0">
          <span className="block text-[15px] font-medium text-ink">
            {busy ? "Checking your leads…" : "Drop a lead CSV, or choose a file"}
          </span>
          <span className="mt-0.5 block text-sm text-ink-3">
            Needs <span className="font-mono text-[13px] text-ink-2">{COLUMNS}</span>. Email, location and name are optional.
          </span>
        </span>
        <input
          ref={input}
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          disabled={busy}
          onChange={(e) => send(e.target.files?.[0])}
        />
      </label>
      {error && (
        <p role="alert" className="mt-3 whitespace-pre-line rounded-lg bg-fail-tint px-4 py-3 text-sm text-fail">
          {error}
        </p>
      )}
    </div>
  );
}
