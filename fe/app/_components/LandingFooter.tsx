import LuminaLogo from "@/app/components/ui/LuminaLogo";

export default function LandingFooter() {
  return (
    <footer style={{ borderTop: "1px solid var(--border-subtle)", background: "var(--surface-card)" }}>
      <div style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 24px", display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
        <LuminaLogo size={30} tone="brand" />
        <span style={{ fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 18, color: "var(--text-strong)" }}>LuminaAi</span>
        <span style={{ color: "var(--text-subtle)", fontSize: 14 }}>· Trợ lý tư vấn tuyển sinh tiểu học</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 18, fontSize: 14, color: "var(--text-muted)" }}>
          <a href="#" style={{ color: "inherit", textDecoration: "none" }}>Về LuminaAi</a>
          <a href="#" style={{ color: "inherit", textDecoration: "none" }}>Bảo mật</a>
          <a href="#" style={{ color: "inherit", textDecoration: "none" }}>Liên hệ</a>
        </div>
      </div>
    </footer>
  );
}
