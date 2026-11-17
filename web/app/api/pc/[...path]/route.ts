// Forwards /api/pc/* to the Python pipeline API with the server-side token.
// Session is already enforced by proxy.ts.

async function forward(request: Request, path: string[]) {
  const base = process.env.PITCHCRAFT_API_URL;
  const token = process.env.PITCHCRAFT_API_TOKEN;
  if (!base || !token) {
    return Response.json(
      { detail: "Pipeline server not connected. Set PITCHCRAFT_API_URL and PITCHCRAFT_API_TOKEN." },
      { status: 503 },
    );
  }
  const url = new URL(`/api/${path.map(encodeURIComponent).join("/")}`, base);
  url.search = new URL(request.url).search;

  const headers = new Headers({ authorization: `Bearer ${token}` });
  const ct = request.headers.get("content-type");
  if (ct) headers.set("content-type", ct);

  try {
    const upstream = await fetch(url, {
      method: request.method,
      headers,
      body: request.method === "GET" ? undefined : await request.arrayBuffer(),
      cache: "no-store",
    });
    const out = new Headers();
    for (const h of ["content-type", "content-length", "content-disposition"]) {
      const v = upstream.headers.get(h);
      if (v) out.set(h, v);
    }
    return new Response(upstream.body, { status: upstream.status, headers: out });
  } catch {
    return Response.json({ detail: "Pipeline server is unreachable." }, { status: 502 });
  }
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(request: Request, { params }: Ctx) {
  return forward(request, (await params).path);
}

export async function POST(request: Request, { params }: Ctx) {
  return forward(request, (await params).path);
}
