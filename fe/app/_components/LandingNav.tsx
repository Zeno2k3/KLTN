import type { CSSProperties } from "react";
import LogoLockup from "@/app/components/common/LogoLockup";
import LandingNavActions from "./LandingNavActions";

const navLink: CSSProperties = {
  padding: "8px 13px",
  borderRadius: "var(--radius-pill)",
  color: "var(--text-muted)",
  fontWeight: 700,
  fontSize: 15,
  textDecoration: "none",
};

export default function LandingNav() {
  return (
    <header style={{ position: "sticky", top: 0, zIndex: 30, background: "rgba(247,250,250,.82)", backdropFilter: "blur(10px)", borderBottom: "1px solid var(--border-subtle)" }}>
      <div style={{ maxWidth: 1180, margin: "0 auto", padding: "13px 24px", display: "flex", alignItems: "center", gap: 22 }}>
        <LogoLockup href="/" logoSize={34} tone="brand" wordmarkSize={22} letterSpacing="-.02em" />
        <nav style={{ display: "flex", gap: 2, marginLeft: 8 }}>
          <a href="#tinhnang" style={navLink}>Tính năng</a>
          <a href="#cachhoatdong" style={navLink}>Cách hoạt động</a>
          <a href="#donvi" style={navLink}>Đồng hành</a>
          <a href="#danhgia" style={navLink}>Đánh giá</a>
        </nav>
        <div style={{ marginLeft: "auto", display: "flex", gap: 10, alignItems: "center" }}>
          <LandingNavActions />
        </div>
      </div>
    </header>
  );
}
