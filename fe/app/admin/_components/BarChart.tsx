import type { ChartBar } from "@/app/types/admin";

/** Biểu đồ cột lượt trò chuyện theo mốc thời gian; `caption` mô tả khoảng đang xem. */
export default function BarChart({ bars, caption = "6 mốc gần nhất" }: { bars: ChartBar[]; caption?: string }) {
  return (
    <div className="gw-card gw-card--pad">
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 4 }}>
        <h2 style={{ fontSize: 17, margin: 0, color: "var(--text-strong)" }}>Lượt trò chuyện</h2>
        <span style={{ fontSize: 13, color: "var(--text-subtle)" }}>{caption}</span>
      </div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 14, height: 210, paddingTop: 22 }}>
        {bars.map((b) => (
          <div key={b.label} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 9, height: "100%", justifyContent: "flex-end" }}>
            <span style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 13, color: "var(--text-muted)" }}>{b.value}</span>
            <div className="ad-bar" style={{ width: "100%", maxWidth: 46, height: b.h, background: "linear-gradient(180deg, var(--teal-400), var(--brand))", borderRadius: "10px 10px 4px 4px" }} />
            <span style={{ fontSize: 12.5, color: "var(--text-subtle)" }}>{b.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
