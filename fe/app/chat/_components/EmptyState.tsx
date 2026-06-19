"use client";

import LogoBadge from "@/app/components/common/LogoBadge";

interface EmptyStateProps {
  greetingText: string;
  greetingSub: string;
  topics: string[];
  onTopic: (t: string) => void;
}

/** Màn hình chào khi cuộc trò chuyện chưa có tin nhắn nào. */
export default function EmptyState({ greetingText, greetingSub, topics, onTopic }: EmptyStateProps) {
  return (
    <div style={{ margin: "auto", maxWidth: 560, padding: "24px 0", display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
      <LogoBadge logoSize={58} radius={24} pad={15} shadow animate />
      <h2 style={{ fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 30, color: "var(--text-strong)", margin: "22px 0 8px" }}>{greetingText}</h2>
      <p style={{ fontSize: 16, color: "var(--text-muted)", lineHeight: 1.55, margin: "0 0 26px", maxWidth: 430 }}>{greetingSub}</p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, justifyContent: "center" }}>
        {topics.map((t) => (
          <button key={t} className="ch-chip" onClick={() => onTopic(t)} style={{ fontFamily: "var(--font-body)", fontWeight: 600, fontSize: 14, color: "var(--brand-strong)", background: "var(--surface-card)", border: "1.5px solid var(--border-brand)", borderRadius: "var(--radius-pill)", padding: "9px 15px", cursor: "pointer", transition: "transform .12s, background .15s" }}>{t}</button>
        ))}
      </div>
    </div>
  );
}
