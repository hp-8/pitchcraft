import { NextResponse } from "next/server";
import { SESSION_COOKIE, createSession, timingSafeEqual } from "@/lib/session";

export async function POST(request: Request) {
  const expected = process.env.OPERATOR_PASSWORD;
  if (!expected) {
    return NextResponse.json({ detail: "OPERATOR_PASSWORD is not set on the server." }, { status: 503 });
  }
  const { password } = (await request.json().catch(() => ({}))) as { password?: string };
  if (typeof password !== "string" || !timingSafeEqual(password, expected)) {
    // chisle: no rate limit; add Vercel Firewall rule if this gets hammered
    await new Promise((r) => setTimeout(r, 600));
    return NextResponse.json({ detail: "That password didn't match." }, { status: 401 });
  }
  const { value, maxAge } = await createSession();
  const res = NextResponse.json({ ok: true });
  res.cookies.set(SESSION_COOKIE, value, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge,
  });
  return res;
}

export async function DELETE() {
  const res = NextResponse.json({ ok: true });
  res.cookies.delete(SESSION_COOKIE);
  return res;
}
