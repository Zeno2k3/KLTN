import type { CSSProperties } from "react";

interface AvatarProps {
  initials: string;
  bg: string;
  color?: string;
  size?: number;
  /** "circle" → bo tròn; "rounded" → bo góc theo `radius`. */
  shape?: "circle" | "rounded";
  radius?: number;
  border?: string;
  fontSize?: number;
  style?: CSSProperties;
}

/** Avatar chữ cái (vòng tròn hoặc bo góc). */
export default function Avatar({
  initials,
  bg,
  color = "#fff",
  size = 38,
  shape = "circle",
  radius = 11,
  border,
  fontSize = 14,
  style,
}: AvatarProps) {
  return (
    <span
      style={{
        flex: "0 0 auto",
        width: size,
        height: size,
        borderRadius: shape === "circle" ? "50%" : radius,
        background: bg,
        color,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "var(--font-display)",
        fontWeight: 800,
        fontSize,
        ...(border ? { border } : {}),
        ...style,
      }}
    >
      {initials}
    </span>
  );
}
