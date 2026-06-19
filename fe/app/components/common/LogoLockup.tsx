import Link from "next/link";
import type { CSSProperties } from "react";
import LuminaLogo from "@/app/components/ui/LuminaLogo";

interface LogoLockupProps {
  /** Có `href` → bọc trong <Link>; không có → <span>. */
  href?: string;
  logoSize?: number;
  tone?: "brand" | "white";
  wordmarkColor?: string;
  wordmarkSize?: number;
  letterSpacing?: string;
  style?: CSSProperties;
}

/** Logo LuminaAi + chữ "LuminaAi" (dùng ở nav, panel auth…). */
export default function LogoLockup({
  href,
  logoSize = 34,
  tone = "brand",
  wordmarkColor = "var(--text-strong)",
  wordmarkSize = 22,
  letterSpacing,
  style,
}: LogoLockupProps) {
  const content = (
    <>
      <LuminaLogo size={logoSize} tone={tone} />
      <span
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 800,
          fontSize: wordmarkSize,
          color: wordmarkColor,
          ...(letterSpacing ? { letterSpacing } : {}),
        }}
      >
        LuminaAi
      </span>
    </>
  );
  const baseStyle: CSSProperties = { display: "flex", alignItems: "center", gap: 10, textDecoration: "none", ...style };

  if (href) {
    return (
      <Link href={href} style={baseStyle}>
        {content}
      </Link>
    );
  }
  return <span style={baseStyle}>{content}</span>;
}
