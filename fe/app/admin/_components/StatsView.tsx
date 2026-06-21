"use client";

import { useState } from "react";
import type {
  ChartBar,
  ChartBucketDTO,
  DeltaTone,
  StatCardData,
  StatRange,
  StatsDTO,
  TopicProgress,
} from "@/app/types/admin";
import { useStats } from "@/app/hooks/useStats";
import AdminStatCard from "./AdminStatCard";
import BarChart from "./BarChart";
import TopicProgressList from "./TopicProgressList";

const RANGES: { key: StatRange; label: string }[] = [
  { key: "24h", label: "24 giờ" },
  { key: "7d", label: "7 ngày" },
  { key: "30d", label: "30 ngày" },
];

const SUBTITLE: Record<StatRange, string> = {
  "24h": "trong 24 giờ qua",
  "7d": "trong 7 ngày qua",
  "30d": "trong 30 ngày qua",
};

const CAPTION: Record<StatRange, string> = {
  "24h": "24 giờ qua",
  "7d": "7 ngày qua",
  "30d": "30 ngày qua",
};

const nf = new Intl.NumberFormat("vi-VN");

/** Badge delta: "+12%"/"-8%" (so kỳ trước), "mới" (kỳ trước = 0 nhưng kỳ này có), "—" (không có). */
function deltaInfo(pct: number | null, value: number): { text: string; tone: DeltaTone } {
  if (pct === null) return { text: value > 0 ? "mới" : "—", tone: "neutral" };
  const r = Math.round(pct * 10) / 10;
  const num = Number.isInteger(r) ? String(r) : r.toFixed(1);
  if (r > 0) return { text: `+${num}%`, tone: "up" };
  if (r < 0) return { text: `${num}%`, tone: "down" };
  return { text: "0%", tone: "neutral" };
}

function toCards(s: StatsDTO): StatCardData[] {
  const ap = deltaInfo(s.active_parents.delta_pct, s.active_parents.value);
  const cv = deltaInfo(s.conversations.delta_pct, s.conversations.value);
  const aq = deltaInfo(s.answered_questions.delta_pct, s.answered_questions.value);
  return [
    { label: "Phụ huynh hoạt động", value: nf.format(s.active_parents.value), delta: ap.text, deltaTone: ap.tone, icon: "users", tint: "var(--teal-50)", fg: "var(--brand)" },
    { label: "Lượt trò chuyện", value: nf.format(s.conversations.value), delta: cv.text, deltaTone: cv.tone, icon: "chat", tint: "var(--sky-50)", fg: "var(--sky-600)" },
    { label: "Câu hỏi đã giải đáp", value: nf.format(s.answered_questions.value), delta: aq.text, deltaTone: aq.tone, icon: "q", tint: "var(--sun-50)", fg: "var(--sun-600)" },
    { label: "Tài liệu kiến thức", value: nf.format(s.total_documents), delta: "cập nhật", deltaTone: "neutral", icon: "doc", tint: "var(--brand-subtle)", fg: "var(--brand-strong)" },
  ];
}

function toBars(buckets: ChartBucketDTO[]): ChartBar[] {
  const max = Math.max(1, ...buckets.map((b) => b.count));
  return buckets.map((b) => ({
    label: b.label,
    value: nf.format(b.count),
    h: Math.round((b.count / max) * 100) + "%",
  }));
}

function toTopics(s: StatsDTO): TopicProgress[] {
  return [
    { label: s.topic.label, pct: "100%", value: `${nf.format(s.topic.count)} lượt`, color: "var(--brand)" },
  ];
}

/** Tab "Thống kê": bộ chọn mốc thời gian + lưới thẻ số liệu + biểu đồ + chủ đề (dữ liệu thật). */
export default function StatsView() {
  const [range, setRange] = useState<StatRange>("30d");
  const { stats, loading, error } = useStats(range);

  return (
    <div className="ad-view">
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ fontSize: 28, margin: "0 0 5px", color: "var(--text-strong)" }}>Thống kê tổng quan</h1>
          <p style={{ margin: 0, fontSize: 15, color: "var(--text-muted)" }}>Số liệu hoạt động của trợ lý LuminaAi {SUBTITLE[range]}.</p>
        </div>
        <div role="tablist" aria-label="Mốc thời gian" style={{ display: "inline-flex", background: "var(--surface-sunken)", borderRadius: "var(--radius-pill)", padding: 4, gap: 2 }}>
          {RANGES.map((r) => {
            const active = r.key === range;
            return (
              <button
                key={r.key}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setRange(r.key)}
                style={{ border: "none", cursor: "pointer", fontFamily: "var(--font-body)", fontSize: 13.5, fontWeight: 600, padding: "7px 16px", borderRadius: "var(--radius-pill)", color: active ? "var(--brand-strong)" : "var(--text-muted)", background: active ? "var(--white)" : "transparent", boxShadow: active ? "var(--shadow-xs)" : "none" }}
              >
                {r.label}
              </button>
            );
          })}
        </div>
      </div>

      {error ? (
        <div className="gw-card gw-card--pad" style={{ color: "var(--text-danger)" }}>{error}</div>
      ) : !stats ? (
        <div style={{ color: "var(--text-muted)", padding: "40px 0", textAlign: "center" }}>Đang tải số liệu…</div>
      ) : (
        <div style={{ opacity: loading ? 0.55 : 1, transition: "opacity .15s" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 22 }}>
            {toCards(stats).map((s) => (
              <AdminStatCard key={s.label} stat={s} />
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1.55fr 1fr", gap: 16 }}>
            <BarChart bars={toBars(stats.chart)} caption={CAPTION[range]} />
            <TopicProgressList topics={toTopics(stats)} />
          </div>
        </div>
      )}
    </div>
  );
}
