import Link from "next/link";
import { ArrowRight, Check } from "lucide-react";
import { Logo } from "@/components/ui";
import { Compare } from "@/components/landing/compare";

export const metadata = {
  title: "Pitchcraft · Pitch with the finished work",
  description:
    "Pitchcraft audits a local business's website, designs a better one, and hands your agency the proof before the first call.",
  robots: { index: true, follow: true },
};

function Cta({ label = "Request access", invert = false }: { label?: string; invert?: boolean }) {
  return (
    <Link
      href="/sign-up"
      className={`group inline-flex h-12 items-center gap-3 px-6 text-[15px] font-semibold transition-colors ${
        invert ? "bg-ink text-white hover:bg-ink/85" : "bg-action text-white hover:bg-action-hover"
      }`}
    >
      {label} <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" strokeWidth={2.25} />
    </Link>
  );
}

const STEPS = [
  {
    k: "Audit",
    title: "Find what’s costing them customers.",
    body: "Speed, mobile layout, calls to action, trust signals and search markup, scored against what works in their vertical.",
    rows: [
      ["High", "No booking button above the fold"],
      ["High", "5.8s to load on mobile"],
      ["Med", "No reviews on the homepage"],
    ],
  },
  {
    k: "Redesign",
    title: "Build the site they should have.",
    body: "A brand brief from their own content, then a multi-page prototype, polished and deployed to a live link.",
    rows: [
      ["Brief", "Voice, palette, type, structure"],
      ["Pages", "Home, services, about, contact"],
      ["Live", "casa-olivo.vercel.app"],
    ],
  },
  {
    k: "Approve",
    title: "Send only what you’d sign.",
    body: "Review each prototype beside its audit and proposal. Approve with one key. Nothing reaches a prospect without you.",
    rows: [
      ["Yes", "Bluebell Dental Studio"],
      ["Yes", "Harbor Point Realty"],
      ["—", "Copper Kettle Coffee"],
    ],
  },
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
            <Link href="/sign-up" className="inline-flex h-9 items-center bg-action px-4 font-semibold text-white transition-colors hover:bg-action-hover">
              Request access
            </Link>
          </nav>
        </div>
      </header>

      <main>
        <section className="mx-auto max-w-[1320px] px-5 pb-16 pt-10 sm:px-10">
          <div className="grid grid-cols-12 gap-x-4 gap-y-8 border-t-[3px] border-ink pt-6">
            <h1 className="pc-rise col-span-12 text-[clamp(60px,10.6vw,172px)] font-black leading-[0.82] tracking-[-0.06em] lg:col-span-9">
              Pitch with the finished work.
            </h1>
            <div className="pc-rise col-span-3 hidden aspect-square self-start bg-action [animation-delay:120ms] lg:block" aria-hidden />

            <p className="col-span-12 border-t border-ink pt-3 text-[17px] leading-snug text-ink-2 sm:col-span-6 lg:col-span-4">
              Pitchcraft audits a local business’s website, designs the one they should have, and hands your agency the proof before the
              first call.
            </p>
            <div className="col-span-12 flex flex-wrap items-start gap-3 border-t border-ink pt-3 sm:col-span-6 lg:col-span-5">
              <Cta />
              <a href="#how" className="inline-flex h-12 items-center border border-ink px-6 text-[15px] font-semibold hover:bg-sunken">
                See how it works
              </a>
            </div>
            <dl className="col-span-12 grid grid-cols-3 border-t border-ink pt-3 text-sm lg:col-span-3">
              <div>
                <dt className="text-ink-3">Audit</dt>
                <dd className="font-semibold">Automated</dd>
              </div>
              <div>
                <dt className="text-ink-3">Prototype</dt>
                <dd className="font-semibold">Live link</dd>
              </div>
              <div>
                <dt className="text-ink-3">Access</dt>
                <dd className="font-semibold">Invite</dd>
              </div>
            </dl>
          </div>

          <div className="pc-rise mt-14 [animation-delay:200ms]">
            <Compare />
          </div>
        </section>

        <section id="how" className="scroll-mt-16 border-y-[3px] border-ink">
          <div className="mx-auto max-w-[1320px] px-5 py-20 sm:px-10">
            <h2 className="max-w-4xl text-[clamp(40px,6vw,88px)] font-black leading-[0.88] tracking-[-0.055em] text-balance">
              From a list of leads to pitches you’d sign.
            </h2>
            <div className="mt-14 grid border-t border-ink md:grid-cols-3">
              {STEPS.map((s, i) => (
                <article
                  key={s.k}
                  className={`pc-reveal pb-8 pt-5 md:px-6 md:pb-0 ${i === 0 ? "md:pl-0" : "md:border-l md:border-ink"} ${i === 2 ? "md:pr-0" : ""}`}
                >
                  <p className="text-sm font-semibold text-action">{s.k}</p>
                  <h3 className="mt-2 text-[28px] font-extrabold leading-[1] tracking-[-0.035em] text-balance">{s.title}</h3>
                  <p className="mt-3 text-[15px] leading-relaxed text-ink-2 text-pretty">{s.body}</p>
                  <dl className="mt-6 border-t border-ink text-sm">
                    {s.rows.map(([a, b]) => (
                      <div key={b} className="flex gap-4 border-b border-line py-2.5">
                        <dt className={`w-12 shrink-0 font-semibold ${a === "High" ? "text-action" : ""}`}>{a}</dt>
                        <dd className="truncate text-ink-2">{b}</dd>
                      </div>
                    ))}
                  </dl>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1320px] px-5 py-20 sm:px-10">
          <div className="grid gap-12 lg:grid-cols-12">
            <div className="lg:col-span-5">
              <h2 className="text-[clamp(40px,5.4vw,80px)] font-black leading-[0.88] tracking-[-0.055em] text-balance">
                Every pitch arrives with its evidence.
              </h2>
              <p className="mt-6 max-w-[42ch] text-[17px] leading-relaxed text-ink-2 text-pretty">
                A revenue audit and a one-page growth proposal for each lead, ready to attach. The numbers show their working, so the owner can
                check them.
              </p>
              <ul className="mt-8 border-t border-ink text-[15px] font-medium">
                {["Live prototype link", "Revenue audit PDF", "Growth proposal PDF", "First email, drafted for you"].map((t) => (
                  <li key={t} className="flex items-center gap-3 border-b border-line py-3">
                    <Check className="size-4" strokeWidth={2.5} /> {t}
                  </li>
                ))}
              </ul>
            </div>
            <div className="pc-reveal border-[3px] border-ink p-8 lg:col-span-6 lg:col-start-7">
              <div className="flex items-baseline justify-between gap-4 border-b border-ink pb-4">
                <p className="text-lg font-extrabold tracking-[-0.02em]">Revenue audit · Casa Olivo Trattoria</p>
                <span className="text-xs text-ink-3">Sample</span>
              </div>
              <p className="mt-6 text-sm text-ink-2">Estimated revenue lost each month</p>
              <p className="num mt-1 text-[clamp(44px,5vw,72px)] font-black leading-none tracking-[-0.05em]">$2,100–2,600</p>
              <div className="mt-8 border-t border-ink text-sm">
                {[
                  ["No reservation button on mobile", "$1,200"],
                  ["Phone number only in the footer", "$600"],
                  ["No reviews or social proof on the homepage", "$300"],
                ].map(([t, v]) => (
                  <div key={t} className="flex items-baseline gap-4 border-b border-line py-3">
                    <span className="text-ink-2">{t}</span>
                    <span className="num ml-auto shrink-0 font-semibold">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="bg-action text-white">
          <div className="mx-auto grid max-w-[1320px] gap-10 px-5 py-20 sm:px-10 lg:grid-cols-12 lg:items-end">
            <h2 className="text-[clamp(44px,7.4vw,120px)] font-black leading-[0.84] tracking-[-0.06em] text-balance lg:col-span-9">
              Your next client already has a website. Show them a better one.
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
