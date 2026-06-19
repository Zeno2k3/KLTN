"use client";

import type { CSSProperties } from "react";
import Icon from "@/app/components/ui/Icon";

const navBase: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 12,
  width: "100%",
  textAlign: "left",
  padding: "11px 13px",
  border: "none",
  borderRadius: 12,
  cursor: "pointer",
  fontFamily: "var(--font-body)",
  fontWeight: 700,
  fontSize: 15,
  transition: "background .15s, color .15s",
};
const navActive: CSSProperties = { ...navBase, background: "var(--brand)", color: "#fff", boxShadow: "var(--shadow-brand)" };
const navIdle: CSSProperties = { ...navBase, background: "transparent", color: "var(--text-muted)" };

interface AdminSidebarProps {
  tab: "stats" | "docs";
  onTab: (t: "stats" | "docs") => void;
  docCount: number;
}

/** Sidebar trái: điều hướng tab + thẻ trạng thái. */
export default function AdminSidebar({ tab, onTab, docCount }: AdminSidebarProps) {
  const isStats = tab === "stats";
  return (
    <aside className="ad-side" style={{ flex: "0 0 252px", minWidth: 0, overflow: "hidden", display: "flex", flexDirection: "column", background: "var(--surface-card)", borderRight: "1px solid var(--border-subtle)", padding: "16px 14px" }}>
      <div style={{ padding: "6px 12px 10px", fontSize: 12, fontWeight: 800, letterSpacing: ".06em", textTransform: "uppercase", color: "var(--text-subtle)" }}>Chức năng</div>
      <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <button className="ad-nav" onClick={() => onTab("stats")} style={isStats ? navActive : navIdle}>
          <span style={{ flex: "0 0 auto", display: "inline-flex" }}><Icon name="bar-chart" size={20} /></span>
          Thống kê
        </button>
        <button className="ad-nav" onClick={() => onTab("docs")} style={isStats ? navIdle : navActive}>
          <span style={{ flex: "0 0 auto", display: "inline-flex" }}><Icon name="book" size={20} /></span>
          Cơ sở kiến thức
        </button>
      </nav>
      <div style={{ marginTop: "auto", padding: 14, borderRadius: "var(--radius-lg)", background: "var(--brand-subtle)", border: "1px solid var(--border-brand)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 14, color: "var(--brand-strong)" }}>
          <Icon name="info" size={17} />
          Trạng thái
        </div>
        <p style={{ margin: "8px 0 0", fontSize: 13, color: "var(--brand-strong)", lineHeight: 1.5 }}>Cơ sở kiến thức đang hoạt động. Bot trả lời dựa trên {docCount} tài liệu.</p>
      </div>
    </aside>
  );
}
