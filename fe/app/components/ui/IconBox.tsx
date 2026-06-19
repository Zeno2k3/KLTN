import type { CSSProperties, ReactNode } from "react";

interface IconBoxProps {
  size: number;
  radius?: number | string;
  bg: string;
  color: string;
  children: ReactNode;
  style?: CSSProperties;
}

/** Ô vuông bo góc có màu, bọc 1 icon/SVG ở giữa. */
export default function IconBox({ size, radius = "var(--radius-lg)", bg, color, children, style }: IconBoxProps) {
  return (
    <span
      style={{
        display: "inline-flex",
        width: size,
        height: size,
        borderRadius: radius,
        background: bg,
        color,
        alignItems: "center",
        justifyContent: "center",
        ...style,
      }}
    >
      {children}
    </span>
  );
}
