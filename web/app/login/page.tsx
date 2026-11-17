"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRight, Loader2 } from "lucide-react";
import { Logo } from "@/components/ui";

function LoginForm() {
  const router = useRouter();
  const next = useSearchParams().get("next") || "/";
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const res = await fetch("/api/auth", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (res.ok) {
      router.replace(next.startsWith("/") && !next.startsWith("//") ? next : "/");
      return;
    }
    const body = await res.json().catch(() => ({}));
    setError(body.detail ?? "Sign-in failed. Try again.");
    setBusy(false);
  }

  return (
    <form onSubmit={submit} className="mt-8 space-y-4">
      <div>
        <label htmlFor="pw" className="block text-sm font-medium text-ink">
          Password
        </label>
        <input
          id="pw"
          type="password"
          autoComplete="current-password"
          autoFocus
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          aria-invalid={!!error}
          aria-describedby={error ? "pw-err" : undefined}
          className="mt-1.5 h-11 w-full rounded-lg border border-line-strong bg-surface px-3 text-[15px] shadow-[inset_0_1px_2px_rgb(18_22_31/0.04)] outline-none transition-shadow placeholder:text-ink-3 focus:border-action focus:ring-4 focus:ring-action/15"
        />
        {error && (
          <p id="pw-err" role="alert" className="mt-2 text-sm text-fail">
            {error}
          </p>
        )}
      </div>
      <button
        type="submit"
        disabled={busy || !password}
        className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-ink text-[15px] font-medium text-white transition-colors hover:bg-ink/90 disabled:opacity-50"
      >
        {busy ? <Loader2 className="size-4 animate-spin" /> : null}
        Sign in
        {!busy && <ArrowRight className="size-4" strokeWidth={2} />}
      </button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <div className="grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <section className="flex flex-col px-6 py-8 sm:px-12">
        <Logo />
        <div className="my-auto w-full max-w-sm py-16">
          <h1 className="text-[28px] font-semibold tracking-[-0.02em] text-balance">Sign in to your console</h1>
          <p className="mt-2 text-[15px] text-ink-2">Review batches, approve prototypes and ship pitches.</p>
          <Suspense>
            <LoginForm />
          </Suspense>
        </div>
        <p className="text-xs text-ink-3">Private operator console.</p>
      </section>

      <aside className="relative hidden overflow-hidden border-l border-line bg-ink lg:block" aria-hidden>
        <div className="absolute inset-0 flex flex-col justify-center px-14">
          <p className="max-w-md text-[34px] leading-[1.15] font-semibold tracking-[-0.025em] text-white text-balance">
            Every prospect gets their new site before the first call.
          </p>
          <div className="mt-12 max-w-md space-y-2.5">
            {[
              ["Audit", "done"],
              ["References", "done"],
              ["Brief", "done"],
              ["Screens", "done"],
              ["Site", "done"],
              ["Deployed", "live"],
              ["PDFs", "next"],
            ].map(([label, s], i) => (
              <div
                key={label}
                className="flex items-center gap-4 rounded-lg border border-white/10 bg-white/[0.04] px-4 py-3"
                style={{ animation: `pc-in 600ms var(--ease-out-expo) ${i * 70}ms both` }}
              >
                <span
                  className={`size-2 rounded-full ${s === "done" ? "bg-[#5fd39a]" : s === "live" ? "pc-live bg-[#8d9bff]" : "bg-white/25"}`}
                />
                <span className="text-sm text-white/85">{label}</span>
                <span className="ml-auto font-mono text-xs text-white/45">
                  {s === "done" ? "complete" : s === "live" ? "in progress" : "queued"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
}
