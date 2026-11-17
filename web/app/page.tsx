import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Logo } from "@/components/ui";
import { Compare } from "@/components/landing/compare";
import { Count } from "@/components/landing/count";
import { Compose } from "@/components/landing/compose";

export const metadata = {
  title: "Pitchcraft · Win the client before the first call",
  description:
    "Pitchcraft audits a local business's website and builds the one they should have, so your agency opens with the finished work.",
  robots: { index: true, follow: true },
  alternates: { canonical: "/" },
  openGraph: {
    url: "/",
    siteName: "Pitchcraft",
    type: "website",
    title: "Win the client before the first call.",
    description: "Every lead arrives with an audit of their site and a live redesign. You open with the work.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Win the client before the first call.",
    description: "Every lead arrives with an audit of their site and a live redesign. You open with the work.",
  },
};

function Cta({ invert = false }: { invert?: boolean }) {
  return (
    <Link
      href="/sign-up"
      className={`pc-press inline-flex h-12 items-center gap-3 px-6 text-[15px] font-semibold text-white ${
        invert ? "bg-ink hover:bg-ink/85" : "bg-action hover:bg-action-hover"
      }`}
    >
      Request access <ArrowRight className="size-4" strokeWidth={2.25} />
    </Link>
  );
}

const HERO = ["Win the", "client", "before the", "first call."];

const STEPS = [
  ["Audit", "Find what’s costing them customers.", "Speed, mobile, calls to action and trust, scored against their vertical."],
  ["Redesign", "Build the site they should have.", "A brief from their own content, shaped into a live, multi-page prototype."],
  ["Approve", "Send only what you’d sign.", "Review each one beside its audit. Nothing reaches a prospect without you."],
];

const LOSSES: [string, number][] = [
  ["No reservation button on mobile", 1200],
  ["Phone number only in the footer", 600],
  ["No reviews on the homepage", 300],
];

export default function Landing() {
  return (
    <div className="bg-ground text-ink">
      <header className="sticky top-0 z-30 border-b border-ink bg-ground">
        <div className="mx-auto flex h-16 max-w-[1320px] items-center gap-8 px-5 sm:px-10">
          <Logo />
          <nav className="ml-auto flex items-center gap-7 text-sm font-medium">
            <a href="#how" className="hidden hover:text-action sm:inline">
              How it works
            </a>
            <Link href="/login" className="hover:text-action">
              Sign in
            </Link>
            <Link href="/sign-up" className="pc-press inline-flex h-9 items-center bg-action px-4 font-semibold text-white hover:bg-action-hover">
              Request access
            </Link>
          </nav>
        </div>
      </header>

      <main>
        <section className="mx-auto max-w-[1320px] px-5 pb-16 pt-10 sm:px-10">
          <div className="pc-rule grid grid-cols-12 gap-x-4 gap-y-10 pt-6 [--rule-w:3px]">
            <h1 className="col-span-12 text-[clamp(56px,8vw,136px)] font-black leading-[0.86] tracking-[-0.06em] lg:col-span-9">
              {HERO.map((l, i) => (
                <span key={l} className="pc-line">
                  <span style={{ animationDelay: `${150 + i * 80}ms` }}>{l}</span>
                </span>
              ))}
            </h1>
            <div className="pc-stamp col-span-3 hidden self-stretch [animation-delay:900ms] lg:block">
              <Compose />
            </div>

            <p className="pc-rule col-span-12 pt-3 text-[17px] leading-snug text-ink-2 [animation-delay:600ms] sm:col-span-7 lg:col-span-5">
              <span className="pc-after block [animation-delay:800ms]">
                Every lead arrives with an audit of their site and a live redesign. You open with the work.
              </span>
            </p>
            <div className="pc-rule col-span-12 flex flex-wrap items-start gap-3 pt-3 [animation-delay:680ms] sm:col-span-5 lg:col-span-4 lg:col-start-9">
              <div className="pc-after flex flex-wrap gap-3 [animation-delay:880ms]">
                <Cta />
                <a href="#how" className="pc-press inline-flex h-12 items-center border border-ink px-6 text-[15px] font-semibold hover:bg-sunken">
                  How it works
                </a>
              </div>
            </div>
          </div>

          <div className="pc-after mt-14 [animation-delay:1000ms]">
            <Compare />
          </div>
        </section>

        <section id="how" className="scroll-mt-16 border-y-[3px] border-ink">
          <div className="mx-auto max-w-[1320px] px-5 py-20 sm:px-10">
            <h2 className="max-w-3xl text-[clamp(40px,5.6vw,84px)] font-black leading-[0.9] tracking-[-0.055em] text-balance">
              From a list of leads to work worth sending.
            </h2>
            <div className="mt-14 grid border-t border-ink md:grid-cols-3">
              {STEPS.map(([k, title, body], i) => (
                <article
                  key={k}
                  className={`pc-reveal pb-8 pt-5 md:px-6 md:pb-0 ${i === 0 ? "md:pl-0" : "md:border-l md:border-ink"} ${i === 2 ? "md:pr-0" : ""}`}
                >
                  <p className="num text-sm font-semibold">
                    <span className="text-ink-3">0{i + 1}</span> <span className="text-action">{k}</span>
                  </p>
                  <h3 className="mt-3 text-[28px] font-extrabold leading-[1] tracking-[-0.035em] text-balance">{title}</h3>
                  <p className="mt-3 max-w-[36ch] text-[15px] leading-relaxed text-ink-2 text-pretty">{body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1320px] px-5 py-20 sm:px-10">
          <div className="grid gap-12 lg:grid-cols-12 lg:items-end">
            <div className="lg:col-span-5">
              <h2 className="text-[clamp(40px,5.2vw,78px)] font-black leading-[0.9] tracking-[-0.055em] text-balance">
                Numbers that show their working.
              </h2>
              <p className="mt-6 max-w-[38ch] text-[17px] leading-relaxed text-ink-2 text-pretty">
                Each prototype ships with a revenue audit and a one-page proposal, ready to attach.
              </p>
            </div>
            <div className="pc-reveal border-[3px] border-ink p-8 lg:col-span-6 lg:col-start-7">
              <div className="flex items-baseline justify-between gap-4 border-b border-ink pb-4">
                <p className="text-lg font-extrabold tracking-[-0.02em]">Revenue audit · Casa Olivo Trattoria</p>
                <span className="text-xs text-ink-3">Sample</span>
              </div>
              <p className="mt-6 text-sm text-ink-2">Estimated revenue lost each month</p>
              <p className="mt-1 text-[clamp(44px,5vw,72px)] font-black leading-none tracking-[-0.05em]">
                <Count to={2100} prefix="$" />–<Count to={2600} />
              </p>
              <div className="mt-8 border-t border-ink text-sm">
                {LOSSES.map(([t, v]) => (
                  <div key={t} className="pc-row flex items-baseline gap-4 border-b border-line py-3">
                    <span className="text-ink-2">{t}</span>
                    <span className="ml-auto shrink-0 font-semibold">
                      <Count to={v} prefix="$" />
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="bg-action text-white">
          <div className="mx-auto grid max-w-[1320px] gap-10 px-5 py-20 sm:px-10 lg:grid-cols-12 lg:items-end">
            <h2 className="text-[clamp(44px,7vw,116px)] font-black leading-[0.86] tracking-[-0.06em] text-balance lg:col-span-9">
              They already have a website. Show them the next one.
            </h2>
            <div className="lg:col-span-3">
              <p className="mb-6 text-[15px] text-white/85">Invite-only while we onboard our first agencies.</p>
              <Cta invert />
            </div>
          </div>
        </section>
      </main>

      <footer className="mx-auto flex max-w-[1320px] flex-wrap items-center justify-between gap-4 px-5 py-8 text-sm sm:px-10">
        <span className="font-black tracking-[-0.03em]">Pitchcraft</span>
        <Link href="/login" className="text-ink-2 hover:text-action">
          Sign in
        </Link>
      </footer>
    </div>
  );
}
