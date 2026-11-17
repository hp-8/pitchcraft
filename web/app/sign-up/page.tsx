import Link from "next/link";
import { Logo } from "@/components/ui";

export const metadata = { title: "Request access" };

// chisle: placeholder until Clerk's <Waitlist /> is installed.
export default function SignUpPage() {
  return (
    <div className="flex min-h-dvh flex-col px-6 py-8 sm:px-12">
      <Logo />
      <div className="m-auto w-full max-w-md py-16 text-center">
        <h1 className="text-[36px] font-black leading-[0.95] tracking-[-0.03em] [word-spacing:0.06em] text-balance">Pitchcraft is invite-only for now.</h1>
        <p className="mt-3 text-[15px] leading-relaxed text-ink-2 text-pretty">
          We&apos;re onboarding a small group of agencies first. The request form opens here shortly.
        </p>
        <p className="mt-8 text-sm text-ink-3">
          Already have access?{" "}
          <Link href="/login" className="font-medium text-ink underline decoration-line-strong underline-offset-4 hover:decoration-ink">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
