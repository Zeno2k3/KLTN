import type { ReactNode } from "react";

interface SectionHeadingProps {
  eyebrow: string;
  title: ReactNode;
  subtitle?: string;
  titleSize?: number;
  marginBottom?: number;
}

/** Tiêu đề khối căn giữa: eyebrow + heading (+ mô tả tuỳ chọn). */
export default function SectionHeading({ eyebrow, title, subtitle, titleSize = 40, marginBottom = 42 }: SectionHeadingProps) {
  return (
    <div style={{ textAlign: "center", marginBottom }}>
      <span className="gw-eyebrow">{eyebrow}</span>
      <h2 style={{ fontSize: titleSize, margin: subtitle ? "10px 0 8px" : "10px 0 0", color: "var(--text-strong)" }}>{title}</h2>
      {subtitle && <p style={{ fontSize: 16, color: "var(--text-muted)", margin: 0 }}>{subtitle}</p>}
    </div>
  );
}
