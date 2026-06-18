import type { CSSProperties } from "react";

type Tone = "brand" | "white";

/**
 * LuminaAi mascot — a friendly teal robot.
 * `tone="brand"` → teal body with white features (use on light backgrounds).
 * `tone="white"` → white body with teal features (use on the brand background).
 */
export default function LuminaLogo({
  size = 34,
  tone = "brand",
  style,
}: {
  size?: number;
  tone?: Tone;
  style?: CSSProperties;
}) {
  const body = tone === "brand" ? "var(--brand)" : "#fff";
  const feat = tone === "brand" ? "#fff" : "var(--brand)";
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" fill="none" style={style} aria-hidden="true">
      <path
        d="M60 7 C30 7 7 30 7 60 C7 90 30 113 60 113 C90 113 113 90 113 60 C113 30 90 7 60 7 Z"
        fill={body}
      />
      <rect x="56.5" y="22" width="7" height="20" rx="3.5" fill={feat} />
      <circle cx="60" cy="17" r="7" fill={feat} />
      <rect x="15" y="53" width="14" height="27" rx="7" fill={feat} />
      <rect x="91" y="53" width="14" height="27" rx="7" fill={feat} />
      <ellipse cx="60" cy="66" rx="34" ry="28" fill="none" stroke={feat} strokeWidth="7" />
      <ellipse cx="60" cy="66" rx="39.5" ry="33.5" fill="none" stroke={feat} strokeWidth="2.5" />
      <rect x="44" y="52" width="15" height="27" rx="5" fill={feat} />
      <rect x="61" y="52" width="15" height="27" rx="5" fill={feat} />
    </svg>
  );
}
