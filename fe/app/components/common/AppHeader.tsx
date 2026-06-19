import type { ReactNode } from "react";

interface AppHeaderProps {
  /** Ô logo bên trái (thường là <LogoBadge />). */
  badge: ReactNode;
  title: ReactNode;
  subtitle: ReactNode;
  /** Cụm bên phải (avatar, nút đăng xuất…). */
  right?: ReactNode;
}

/** Khung header sticky dùng chung cho trang chat & admin. */
export default function AppHeader({ badge, title, subtitle, right }: AppHeaderProps) {
  return (
    <header
      style={{
        flex: "0 0 auto",
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "13px 22px",
        background: "var(--surface-card)",
        borderBottom: "1px solid var(--border-subtle)",
        zIndex: 5,
      }}
    >
      {badge}
      <div style={{ minWidth: 0 }}>
        <div style={{ fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 17, color: "var(--text-strong)", lineHeight: 1 }}>
          {title}
        </div>
        <div style={{ marginTop: 4, fontSize: 13, color: "var(--text-muted)" }}>{subtitle}</div>
      </div>
      {right && <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 11 }}>{right}</div>}
    </header>
  );
}
