import {
  AbsoluteFill,
  Easing,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont as loadPlayfair } from "@remotion/google-fonts/PlayfairDisplay";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadJetBrains } from "@remotion/google-fonts/JetBrainsMono";

const { fontFamily: PLAYFAIR } = loadPlayfair("normal", {
  weights: ["500", "700", "900"],
});
const { fontFamily: PLAYFAIR_IT } = loadPlayfair("italic", {
  weights: ["500"],
});
const { fontFamily: INTER } = loadInter("normal", { weights: ["400", "600", "800"] });
const { fontFamily: MONO } = loadJetBrains("normal", { weights: ["400", "700"] });

const INK = "#0F2A44";
const PAPER = "#FAF8F4";
const GOLD = "#C9A24B";
const HOT = "#FF4D2E";
const EASE = Easing.bezier(0.16, 1, 0.3, 1);
const EASE_PUNCH = Easing.bezier(0.34, 1.56, 0.64, 1);

// ============================================================================
// Helpers
// ============================================================================

const useFps = () => useVideoConfig().fps;

const StaggerLetters: React.FC<{
  text: string;
  startFrame: number;
  perLetter: number;
  style?: React.CSSProperties;
  punch?: boolean;
}> = ({ text, startFrame, perLetter, style, punch = false }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <div style={{ display: "flex", ...style }}>
      {Array.from(text).map((char, i) => {
        const localStart = startFrame + i * perLetter;
        const s = punch
          ? spring({ frame: frame - localStart, fps, config: { damping: 9, stiffness: 200, mass: 0.7 } })
          : interpolate(frame, [localStart, localStart + 0.4 * fps], [0, 1], {
              extrapolateRight: "clamp",
              extrapolateLeft: "clamp",
              easing: EASE,
            });
        const op = punch
          ? interpolate(frame, [localStart, localStart + 0.25 * fps], [0, 1], {
              extrapolateRight: "clamp",
              extrapolateLeft: "clamp",
            })
          : s;
        const scale = punch ? 0.6 + s * 0.4 : 1;
        const y = punch ? 0 : (1 - s) * 30;
        return (
          <span
            key={i}
            style={{
              opacity: op,
              display: "inline-block",
              transform: `translateY(${y}px) scale(${scale})`,
              whiteSpace: "pre",
            }}
          >
            {char}
          </span>
        );
      })}
    </div>
  );
};

// ============================================================================
// Scene 1: Hard punch open (0 -> 1.7s)
// ============================================================================

const Scene1Punch: React.FC = () => {
  const frame = useCurrentFrame();
  const fps = useFps();
  // Flash from black to paper at frame 8
  const flash = interpolate(frame, [6, 12], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  const goldRule = interpolate(frame, [25, 45], [0, 600], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: EASE,
  });
  return (
    <AbsoluteFill
      style={{
        background: `rgba(${interpolate(flash, [0, 1], [15, 250])}, ${interpolate(flash, [0, 1], [15, 248])}, ${interpolate(flash, [0, 1], [15, 244])}, 1)`,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
      }}
    >
      <StaggerLetters
        text="PITCHCRAFT"
        startFrame={8}
        perLetter={2}
        punch
        style={{
          fontFamily: PLAYFAIR,
          fontWeight: 900,
          fontSize: 220,
          letterSpacing: "-0.06em",
          color: INK,
          lineHeight: 1,
        }}
      />
      <div style={{ width: goldRule, height: 4, background: GOLD, marginTop: 24 }} />
    </AbsoluteFill>
  );
};

// ============================================================================
// Scene 2: Tagline cascade (1.7 -> 3.2s)
// ============================================================================

const Scene2Tagline: React.FC = () => {
  const frame = useCurrentFrame();
  const fps = useFps();
  // Two phrases stack-swap
  const phrase1Op = interpolate(frame, [0, 0.3 * fps, 0.9 * fps, 1.1 * fps], [0, 1, 1, 0], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: EASE,
  });
  const phrase1Y = interpolate(frame, [0, 0.4 * fps, 0.9 * fps, 1.1 * fps], [40, 0, 0, -40], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: EASE,
  });
  const phrase2Op = interpolate(frame, [0.9 * fps, 1.2 * fps], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: EASE,
  });
  const phrase2Y = interpolate(frame, [0.9 * fps, 1.3 * fps], [40, 0], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: EASE,
  });
  return (
    <AbsoluteFill
      style={{
        background: PAPER,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        position: "relative",
      }}
    >
      <div style={{ position: "absolute", fontFamily: PLAYFAIR, fontSize: 140, fontWeight: 700, color: INK, opacity: phrase1Op, transform: `translateY(${phrase1Y}px)`, letterSpacing: "-0.03em" }}>
        Cold leads <span style={{ fontFamily: PLAYFAIR_IT, fontWeight: 500, color: HOT }}>in.</span>
      </div>
      <div style={{ position: "absolute", fontFamily: PLAYFAIR, fontSize: 140, fontWeight: 700, color: INK, opacity: phrase2Op, transform: `translateY(${phrase2Y}px)`, letterSpacing: "-0.03em" }}>
        Polished pitches <span style={{ fontFamily: PLAYFAIR_IT, fontWeight: 500, color: GOLD }}>out.</span>
      </div>
    </AbsoluteFill>
  );
};

// ============================================================================
// Scene 3: Revenue count-up (3.2 -> 4.8s)
// ============================================================================

const Scene3Revenue: React.FC = () => {
  const frame = useCurrentFrame();
  const fps = useFps();
  const value = Math.floor(
    interpolate(frame, [0.2 * fps, 1.1 * fps], [0, 4000], {
      extrapolateRight: "clamp",
      extrapolateLeft: "clamp",
      easing: EASE,
    }),
  );
  const labelOp = interpolate(frame, [0, 0.4 * fps], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const flash = interpolate(frame, [1.1 * fps, 1.2 * fps, 1.3 * fps], [0, 1, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  return (
    <AbsoluteFill style={{ background: INK, alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
      <div style={{ position: "absolute", inset: 0, background: HOT, opacity: flash * 0.25 }} />
      <div style={{ fontFamily: INTER, fontSize: 22, color: GOLD, letterSpacing: "0.3em", textTransform: "uppercase", opacity: labelOp, marginBottom: 32 }}>
        Average revenue leak per lead
      </div>
      <div style={{ fontFamily: PLAYFAIR, fontWeight: 700, fontSize: 320, color: PAPER, letterSpacing: "-0.04em", lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>
        ${value.toLocaleString()}
      </div>
      <div style={{ fontFamily: INTER, fontSize: 28, color: "rgba(250,248,244,0.6)", marginTop: 24, letterSpacing: "0.15em", textTransform: "uppercase", opacity: labelOp }}>
        Per month. Quantified.
      </div>
    </AbsoluteFill>
  );
};

// ============================================================================
// Scene 4: Pipeline marquee (4.8 -> 6.4s)
// ============================================================================

const STAGES = [
  { label: "AUDIT", desc: "Firecrawl + PageSpeed" },
  { label: "POLISH", desc: "Lenis, GSAP, hero video" },
  { label: "DEPLOY", desc: "Vercel" },
  { label: "SEND", desc: "PDF + bundle" },
];

const Scene4Pipeline: React.FC = () => {
  const frame = useCurrentFrame();
  const fps = useFps();
  return (
    <AbsoluteFill style={{ background: PAPER, alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 64 }}>
      <div style={{ fontFamily: INTER, fontSize: 22, color: GOLD, letterSpacing: "0.3em", textTransform: "uppercase", opacity: interpolate(frame, [0, 0.3 * fps], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" }) }}>
        One row in. Four stages out.
      </div>
      <div style={{ display: "flex", gap: 28 }}>
        {STAGES.map((stage, i) => {
          const delay = i * 0.12 * fps;
          const s = spring({ frame: frame - delay, fps, config: { damping: 11, stiffness: 180 } });
          return (
            <div
              key={stage.label}
              style={{
                opacity: s,
                transform: `translateY(${(1 - s) * 60}px) scale(${0.85 + s * 0.15})`,
                padding: "28px 36px",
                background: INK,
                color: PAPER,
                borderRadius: 6,
                display: "flex",
                flexDirection: "column",
                gap: 8,
                minWidth: 240,
              }}
            >
              <div style={{ fontFamily: MONO, fontSize: 16, color: GOLD, fontWeight: 700 }}>0{i + 1}</div>
              <div style={{ fontFamily: INTER, fontWeight: 800, fontSize: 44, letterSpacing: "0.02em" }}>{stage.label}</div>
              <div style={{ fontFamily: INTER, fontSize: 18, color: "rgba(250,248,244,0.6)" }}>{stage.desc}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ============================================================================
// Scene 5: Stats slam (6.4 -> 8.4s)
// ============================================================================

const StatBlock: React.FC<{
  number: string;
  label: string;
  delay: number;
}> = ({ number, label, delay }) => {
  const frame = useCurrentFrame();
  const fps = useFps();
  const s = spring({ frame: frame - delay, fps, config: { damping: 9, stiffness: 200, mass: 0.6 } });
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", opacity: s, transform: `scale(${0.5 + s * 0.5})` }}>
      <div style={{ fontFamily: PLAYFAIR, fontWeight: 900, fontSize: 220, color: INK, lineHeight: 1, letterSpacing: "-0.05em", fontVariantNumeric: "tabular-nums" }}>
        {number}
      </div>
      <div style={{ fontFamily: INTER, fontSize: 20, color: INK, letterSpacing: "0.25em", textTransform: "uppercase", marginTop: 12 }}>
        {label}
      </div>
    </div>
  );
};

const Scene5Stats: React.FC = () => {
  const frame = useCurrentFrame();
  const fps = useFps();
  return (
    <AbsoluteFill style={{ background: PAPER, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 80 }}>
      <StatBlock number="1" label="CSV" delay={0} />
      <div style={{ fontFamily: PLAYFAIR, fontSize: 120, color: GOLD, fontWeight: 700, opacity: interpolate(frame, [0.3 * fps, 0.5 * fps], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" }) }}>→</div>
      <StatBlock number="N" label="Sites" delay={0.35 * fps} />
      <div style={{ fontFamily: PLAYFAIR, fontSize: 120, color: GOLD, fontWeight: 700, opacity: interpolate(frame, [0.6 * fps, 0.8 * fps], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" }) }}>→</div>
      <StatBlock number="2N" label="PDFs" delay={0.7 * fps} />
    </AbsoluteFill>
  );
};

// ============================================================================
// Scene 6: Brand strip marquee (8.4 -> 9.6s)
// ============================================================================

const CHIPS = ["Realtor", "Restaurant", "Dental", "F&B", "Local Service", "Realtor", "Restaurant", "Dental", "F&B", "Local Service"];

const Scene6Marquee: React.FC = () => {
  const frame = useCurrentFrame();
  const fps = useFps();
  const x = interpolate(frame, [0, 1.2 * fps], [0, -1200], { easing: Easing.linear });
  const op = interpolate(frame, [0, 0.3 * fps, 0.9 * fps, 1.2 * fps], [0, 1, 1, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  return (
    <AbsoluteFill style={{ background: INK, alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 48, opacity: op }}>
      <div style={{ fontFamily: INTER, fontSize: 22, color: GOLD, letterSpacing: "0.3em", textTransform: "uppercase" }}>
        Built for every vertical
      </div>
      <div style={{ width: "100%", overflow: "hidden" }}>
        <div style={{ display: "flex", gap: 48, transform: `translateX(${x}px)` }}>
          {CHIPS.concat(CHIPS).map((chip, i) => (
            <div key={i} style={{ fontFamily: PLAYFAIR, fontStyle: "italic", fontSize: 96, color: PAPER, whiteSpace: "nowrap" }}>
              {chip}
              <span style={{ color: GOLD, marginLeft: 36 }}>·</span>
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============================================================================
// Scene 7: Outro (9.6 -> 12s)
// ============================================================================

const Scene7Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const fps = useFps();
  const op = interpolate(frame, [0, 0.5 * fps], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp", easing: EASE });
  const ruleW = interpolate(frame, [0.4 * fps, 1.2 * fps], [0, 320], { extrapolateRight: "clamp", extrapolateLeft: "clamp", easing: EASE });
  const urlOp = interpolate(frame, [0.7 * fps, 1.1 * fps], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const fadeOut = interpolate(frame, [2.0 * fps, 2.4 * fps], [1, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  return (
    <AbsoluteFill style={{ background: PAPER, alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 28, opacity: op * fadeOut }}>
      <div style={{ fontFamily: PLAYFAIR, fontWeight: 700, fontSize: 200, color: INK, letterSpacing: "-0.05em", lineHeight: 1 }}>
        Pitchcraft
      </div>
      <div style={{ width: ruleW, height: 3, background: GOLD }} />
      <div style={{ fontFamily: PLAYFAIR_IT, fontWeight: 500, fontSize: 38, color: INK, marginTop: 18, opacity: urlOp }}>
        Open source. MIT licensed.
      </div>
      <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 32, color: HOT, marginTop: 24, opacity: urlOp }}>
        github.com/hp-8/pitchcraft
      </div>
      <div style={{ fontFamily: INTER, fontSize: 18, color: "rgba(15,42,68,0.6)", marginTop: 32, letterSpacing: "0.25em", textTransform: "uppercase", opacity: urlOp }}>
        Built by Harsh Patadia
      </div>
    </AbsoluteFill>
  );
};

// ============================================================================
// Composition
// ============================================================================

export const Intro: React.FC = () => {
  const fps = useFps();
  return (
    <AbsoluteFill>
      <Sequence durationInFrames={1.7 * fps} layout="none">
        <Scene1Punch />
      </Sequence>
      <Sequence from={1.7 * fps} durationInFrames={1.5 * fps} layout="none">
        <Scene2Tagline />
      </Sequence>
      <Sequence from={3.2 * fps} durationInFrames={1.6 * fps} layout="none">
        <Scene3Revenue />
      </Sequence>
      <Sequence from={4.8 * fps} durationInFrames={1.6 * fps} layout="none">
        <Scene4Pipeline />
      </Sequence>
      <Sequence from={6.4 * fps} durationInFrames={2.0 * fps} layout="none">
        <Scene5Stats />
      </Sequence>
      <Sequence from={8.4 * fps} durationInFrames={1.2 * fps} layout="none">
        <Scene6Marquee />
      </Sequence>
      <Sequence from={9.6 * fps} durationInFrames={2.4 * fps} layout="none">
        <Scene7Outro />
      </Sequence>
    </AbsoluteFill>
  );
};
