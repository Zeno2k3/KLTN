import type { CSSProperties } from "react";
import LuminaLogo from "@/app/components/ui/LuminaLogo";

interface LogoBadgeProps {
  logoSize?: number;
  radius?: number;
  /** Kiểu padding (mặc định). Bỏ qua nếu truyền `size`. */
  pad?: number;
  /** Kích thước cố định (w=h), căn giữa logo — thay cho `pad`. */
  size?: number;
  shadow?: boolean;
  flex?: boolean;
  /** Bật hiệu ứng nhún `ch-bob` (dùng cho empty-state chat). */
  animate?: boolean;
  style?: CSSProperties;
}

/** Logo LuminaAi đặt trong ô teal bo góc (header chat/admin, hero, avatar bot…). */
export default function LogoBadge({
  logoSize = 28,
  radius = 13,
  pad = 6,
  size,
  shadow,
  flex,
  animate,
  style,
}: LogoBadgeProps) {
  return (
    <span
      style={{
        background: "var(--brand)",
        display: "inline-flex",
        borderRadius: radius,
        ...(size
          ? { width: size, height: size, alignItems: "center", justifyContent: "center" }
          : { padding: pad }),
        ...(shadow ? { boxShadow: "var(--shadow-brand)" } : {}),
        ...(flex ? { flex: "0 0 auto" } : {}),
        ...(animate ? { animation: "ch-bob 4.5s ease-in-out infinite" } : {}),
        ...style,
      }}
    >
      <LuminaLogo size={logoSize} tone="white" />
    </span>
  );
}
