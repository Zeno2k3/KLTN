import type { TopicProgress } from "@/app/types/admin";

/** Danh sách chủ đề được hỏi nhiều (thanh tiến độ). */
export default function TopicProgressList({ topics }: { topics: TopicProgress[] }) {
  return (
    <div className="gw-card gw-card--pad">
      <h2 style={{ fontSize: 17, margin: "0 0 16px", color: "var(--text-strong)" }}>Chủ đề được hỏi nhiều</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 15 }}>
        {topics.map((t) => (
          <div key={t.label}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14, marginBottom: 6 }}>
              <span style={{ color: "var(--text-body)", fontWeight: 600 }}>{t.label}</span>
              <span style={{ color: "var(--text-subtle)" }}>{t.pct}</span>
            </div>
            <div style={{ height: 9, borderRadius: "var(--radius-pill)", background: "var(--ink-100)", overflow: "hidden" }}>
              <div style={{ height: "100%", width: t.pct, background: t.color, borderRadius: "var(--radius-pill)" }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
