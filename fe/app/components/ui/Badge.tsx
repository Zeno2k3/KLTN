import type { CSSProperties, ReactNode } from "react";

type Tone = "brand" | "neutral" | "success" | "warning" | "danger" | "info" | "accent" | "solid";

interface BadgeProps {
  tone: Tone;
  dot?: boolean;
  className?: string;
  style?: CSSProperties;
  children: ReactNode;
}

/** Bọc hệ thống nhãn `gw-badge`. */
export default function Badge({ tone, dot, className, style, children }: BadgeProps) {
  const cls = ["gw-badge", `gw-badge--${tone}`, dot && "gw-badge--dot", className].filter(Boolean).join(" ");
  return (
    <span className={cls} style={style}>
      {children}
    </span>
  );
}
