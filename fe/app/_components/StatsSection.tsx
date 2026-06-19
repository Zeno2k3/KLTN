import { STATS } from "@/app/lib/data/landing";

export default function StatsSection() {
  return (
    <section style={{ maxWidth: 1180, margin: "0 auto", padding: "46px 24px 8px" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 18 }}>
        {STATS.map((s) => (
          <div key={s.label} className="gw-card gw-card--pad" style={{ textAlign: "center" }}>
            <div style={{ fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 38, color: s.color, lineHeight: 1 }}>{s.value}</div>
            <div style={{ marginTop: 8, fontSize: 15, color: "var(--text-muted)" }}>{s.label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
