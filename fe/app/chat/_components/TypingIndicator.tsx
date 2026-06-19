import LogoBadge from "@/app/components/common/LogoBadge";

/** Hiệu ứng "đang gõ" của bot (3 chấm nhấp nháy). */
export default function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 10, alignItems: "flex-end", alignSelf: "flex-start", maxWidth: "78%" }}>
      <LogoBadge logoSize={22} radius={11} size={36} shadow flex />
      <span style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "13px 16px", background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)", borderBottomLeftRadius: 6, boxShadow: "var(--shadow-xs)" }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--teal-400)", animation: "ch-typing 1.2s infinite" }} />
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--teal-400)", animation: "ch-typing 1.2s infinite .15s" }} />
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--teal-400)", animation: "ch-typing 1.2s infinite .3s" }} />
      </span>
    </div>
  );
}
