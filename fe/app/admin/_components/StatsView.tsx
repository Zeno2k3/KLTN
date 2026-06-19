import type { StatCardData } from "@/app/types/admin";
import { CHART, TOPICS } from "@/app/lib/data/admin";
import AdminStatCard from "./AdminStatCard";
import BarChart from "./BarChart";
import TopicProgressList from "./TopicProgressList";

/** Tab "Thống kê": lưới thẻ số liệu + biểu đồ + chủ đề. */
export default function StatsView({ stats }: { stats: StatCardData[] }) {
  return (
    <div className="ad-view">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, margin: "0 0 5px", color: "var(--text-strong)" }}>Thống kê tổng quan</h1>
        <p style={{ margin: 0, fontSize: 15, color: "var(--text-muted)" }}>Số liệu hoạt động của trợ lý LuminaAi trong 30 ngày qua.</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 22 }}>
        {stats.map((s) => (
          <AdminStatCard key={s.label} stat={s} />
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.55fr 1fr", gap: 16 }}>
        <BarChart bars={CHART} />
        <TopicProgressList topics={TOPICS} />
      </div>
    </div>
  );
}
