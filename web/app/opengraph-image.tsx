import { ImageResponse } from "next/og";

export const alt = "Pitchcraft: Win the client before the first call.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

async function archivo(weight: number) {
  // chisle: fetched at build time; falls back to the default font if Google Fonts is unreachable.
  try {
    const css = await (await fetch(`https://fonts.googleapis.com/css2?family=Archivo:wght@${weight}`)).text();
    const url = css.match(/src: url\((.+?)\) format/)?.[1];
    return url ? await (await fetch(url)).arrayBuffer() : null;
  } catch {
    return null;
  }
}

export default async function Image() {
  const [black, semi] = await Promise.all([archivo(900), archivo(600)]);
  const fonts = [
    ...(black ? [{ name: "Archivo", data: black, weight: 900 as const }] : []),
    ...(semi ? [{ name: "Archivo", data: semi, weight: 600 as const }] : []),
  ];

  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", background: "#fff", color: "#0a0a0a", padding: "56px 64px", fontFamily: "Archivo" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 26, fontWeight: 600 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <svg width="40" height="40" viewBox="0 0 32 32">
              <rect width="32" height="32" fill="#0a0a0a" />
              <path d="M10 24V8h7.5a5.5 5.5 0 0 1 0 11H10" fill="none" stroke="#fff" strokeWidth="3.2" />
              <rect x="21" y="21" width="4" height="4" fill="#ff3b00" />
            </svg>
            Pitchcraft
          </div>
          <span style={{ color: "#737373" }}>pitchcraft.harshpatadia.com</span>
        </div>
        <div style={{ display: "flex", flex: 1, marginTop: 36, borderTop: "6px solid #0a0a0a", paddingTop: 28, gap: 40 }}>
          <div style={{ display: "flex", flexDirection: "column", flex: 1, fontSize: 112, fontWeight: 900, lineHeight: 0.88, letterSpacing: "-0.05em" }}>
            <span>Win the client</span>
            <span>before the</span>
            <span>first call.</span>
          </div>
          <div style={{ width: 230, height: 230, background: "#ff3b00", display: "flex" }} />
        </div>
        <div style={{ display: "flex", borderTop: "2px solid #0a0a0a", paddingTop: 16, fontSize: 26, color: "#3b3b3b" }}>
          Every lead arrives with an audit of their site and a live redesign.
        </div>
      </div>
    ),
    { ...size, fonts },
  );
}
