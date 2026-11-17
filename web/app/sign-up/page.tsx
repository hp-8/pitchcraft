import Link from "next/link";
import { ClerkProvider, Waitlist } from "@clerk/nextjs";
import { Logo } from "@/components/ui";
import { Compose } from "@/components/landing/compose";

export const metadata = {
  title: "Request access",
  description: "Pitchcraft is invite-only while we onboard our first agencies. Join the waitlist.",
};

// Swiss: square, black ink, one orange action. Clerk's chrome stripped to the form.
const appearance = {
  variables: {
    colorPrimary: "#ff3b00",
    colorForeground: "#0a0a0a",
    colorMutedForeground: "#737373",
    colorBackground: "#ffffff",
    colorInput: "#ffffff",
    colorInputForeground: "#0a0a0a",
    colorBorder: "#0a0a0a",
    borderRadius: "0px",
    fontFamily: "var(--font-archivo)",
    fontSize: "15px",
  },
  elements: {
    rootBox: "w-full!",
    cardBox: "w-full! max-w-none! shadow-none! border-0! bg-transparent!",
    card: "shadow-none! border-0! px-0! py-0! bg-transparent!",
    // Header only carries text on the success view (start-view title/subtitle are blanked below).
    header: "items-start! text-left! gap-2!",
    headerTitle: "text-[32px]! font-black! leading-[0.95]! tracking-[-0.04em]! text-ink!",
    headerSubtitle: "text-[15px]! text-ink-2!",
    footer: "hidden!",
    formFieldLabel: "text-sm! font-semibold!",
    formFieldInput: "h-12! border! border-ink! px-4! text-[15px]! shadow-none!",
    formFieldErrorText: "text-action! text-sm! font-medium!",
    alert: "border! border-action! bg-action-tint! shadow-none! text-ink!",
    // 19px bold = WCAG "large text", so white on #ff3b00 (3.4:1) meets the 3:1 floor.
    formButtonPrimary: "pc-press h-12! bg-action! bg-none! text-[19px]! font-bold! normal-case! shadow-none! hover:bg-action-hover!",
  },
};

const localization = {
  waitlist: {
    start: { title: "", subtitle: "", formButton: "Join the waitlist" },
    success: {
      title: "You’re on the list.",
      subtitle: "We’ll email you an invite when your spot opens.",
      message: "Keep an eye on your inbox.",
    },
  },
};

export default function SignUpPage() {
  return (
    <div className="flex min-h-dvh flex-col px-5 py-6 sm:px-10">
      <Logo />
      <div className="m-auto grid w-full max-w-[1240px] gap-10 py-16 lg:grid-cols-12 lg:items-start">
        <div className="pc-rule pt-5 [--rule-w:3px] lg:col-span-6">
          <h1 className="text-[clamp(44px,6vw,92px)] font-black leading-[0.88] tracking-[-0.055em]">
            <span className="pc-line">
              <span>Join the</span>
            </span>
            <span className="pc-line">
              <span style={{ animationDelay: "80ms" }}>waitlist.</span>
            </span>
          </h1>
          <p className="pc-after mt-6 max-w-[38ch] text-[17px] leading-snug text-ink-2 [animation-delay:300ms]">
            Pitchcraft is invite-only while we onboard our first agencies. Leave your email and we&apos;ll send an invite when your spot opens.
          </p>
          <div className="pc-after mt-10 hidden h-[100px] w-[280px] [animation-delay:600ms] lg:block">
            <Compose wide speed={0.66} />
          </div>
        </div>
        <div className="pc-after [animation-delay:400ms] lg:col-span-5 lg:col-start-8 lg:pt-6">
          <ClerkProvider appearance={appearance} localization={localization}>
            <Waitlist />
          </ClerkProvider>
          <p className="mt-6 text-sm text-ink-3">
            Already invited?{" "}
            <Link href="/login" className="font-medium text-ink underline underline-offset-4 hover:text-action">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
