"use client";

import { Download } from "lucide-react";
import { AppShell, Crumb } from "@/components/ui";

const PHASES = [
  ["Audit", "Crawls the current site, runs PageSpeed, and scores problems against what works in the vertical."],
  ["References", "Collects design references that fit the business's category and tone."],
  ["Brief", "Writes a brand brief: voice, palette, type and page structure."],
  ["Screens", "Generates page designs in Stitch. Runs from Claude Code with /stitch-batch, then you press Resume."],
  ["Site", "Polishes the screens into a fast, animated multi-page site."],
  ["Deployed", "Publishes the prototype to its own live link."],
  ["PDFs", "Renders the revenue audit and the growth proposal."],
] as const;

const COLUMNS = [
  ["lead_id", "Any unique ID", true],
  ["business", "Business name", true],
  ["vertical", "restaurant, dental, realtor or fnb", true],
  ["site_url", "Current website, with https://", true],
  ["email", "Owner or contact email", false],
  ["location", "City, State", false],
  ["name", "Contact's name", false],
] as const;

export default function GuidePage() {
  return (
    <AppShell header={<Crumb>How it works</Crumb>}>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <h1 className="text-[36px] font-black leading-[0.95] tracking-[-0.03em] [word-spacing:0.06em]">How it works</h1>
        <p className="mt-1 max-w-2xl text-[15px] text-ink-2">
          Every lead moves through seven steps. You only step in twice: once for Stitch screens, once to approve.
        </p>

        <div className="mt-8 grid gap-6 xl:grid-cols-[1.3fr_1fr]">
          <section className="border border-ink bg-surface" aria-label="Pipeline steps">
            <ol>
              {PHASES.map(([name, body], i) => (
                <li key={name} className="grid grid-cols-[28px_120px_1fr] items-baseline gap-3 border-b border-line px-5 py-3.5 text-sm last:border-0">
                  <span className="num text-ink-3">{i + 1}</span>
                  <span className="font-medium">{name}</span>
                  <span className="text-ink-2 text-pretty">{body}</span>
                </li>
              ))}
            </ol>
          </section>

          <section className="border border-ink bg-surface p-5" aria-label="CSV format">
            <div className="flex items-baseline justify-between gap-4">
              <h2 className="text-[15px] font-semibold">Lead CSV format</h2>
              <a href="/sample-leads.csv" download className="inline-flex items-center gap-1.5 text-sm text-ink-2 hover:text-ink">
                <Download className="size-3.5" strokeWidth={2} /> Sample
              </a>
            </div>
            <table className="mt-4 w-full text-left text-sm">
              <tbody>
                {COLUMNS.map(([col, desc, req]) => (
                  <tr key={col} className="border-b border-line last:border-0">
                    <td className="py-2.5 pr-3 font-mono text-[13px] text-ink">{col}</td>
                    <td className="py-2.5 pr-3 text-ink-2">{desc}</td>
                    <td className="py-2.5 text-right text-xs text-ink-3">{req ? "Required" : "Optional"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-4 text-xs leading-relaxed text-ink-3">UTF-8, up to 5 MB. Rows with problems are listed by row number so you can fix them.</p>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
