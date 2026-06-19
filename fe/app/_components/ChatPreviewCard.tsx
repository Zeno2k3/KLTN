import Badge from "@/app/components/ui/Badge";
import LogoBadge from "@/app/components/common/LogoBadge";

/** Thẻ minh hoạ cuộc trò chuyện ở cột phải của hero. */
export default function ChatPreviewCard() {
  return (
    <div style={{ position: "relative" }}>
      <div style={{ position: "absolute", width: 120, height: 120, right: -26, top: -30, background: "var(--sun-200)", borderRadius: "42% 58% 60% 40%/45% 45% 55% 55%", opacity: 0.7, animation: "lp-float-a 7s ease-in-out infinite" }} />
      <div style={{ position: "absolute", width: 86, height: 86, left: -30, bottom: 24, background: "var(--teal-200)", borderRadius: "50%", opacity: 0.7, animation: "lp-float-b 6s ease-in-out infinite" }} />
      <div className="gw-card gw-card--raised" style={{ position: "relative", padding: 0, overflow: "hidden" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "14px 18px", borderBottom: "1px solid var(--border-subtle)" }}>
          <LogoBadge logoSize={26} radius={12} pad={5} />
          <strong style={{ fontFamily: "var(--font-display)", fontSize: 16 }}>LuminaAi</strong>
          <Badge tone="success" dot style={{ marginLeft: "auto" }}>trực tuyến</Badge>
        </div>
        <div style={{ padding: 18, display: "flex", flexDirection: "column", gap: 12, background: "var(--ink-100)" }}>
          <div style={{ alignSelf: "flex-start", maxWidth: "86%", background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)", borderBottomLeftRadius: 6, padding: "12px 16px", fontSize: 15, boxShadow: "var(--shadow-xs)" }}>Chào ba mẹ! 👋 Bé nhà mình sinh năm bao nhiêu để mình kiểm tra độ tuổi vào lớp 1 nhé?</div>
          <div style={{ alignSelf: "flex-end", maxWidth: "86%", background: "var(--brand)", color: "#fff", borderRadius: "var(--radius-lg)", borderBottomRightRadius: 6, padding: "12px 16px", fontSize: 15, boxShadow: "var(--shadow-brand)" }}>Bé sinh 2020 ạ</div>
          <div style={{ alignSelf: "flex-start", maxWidth: "86%", background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)", borderBottomLeftRadius: 6, padding: "12px 16px", fontSize: 15, boxShadow: "var(--shadow-xs)" }}>Dạ bé đủ tuổi vào lớp 1 năm nay! Ba mẹ muốn tìm trường gần khu vực nào ạ? 🎒</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", paddingTop: 2 }}>
            {["Quận 7", "Gần nhà mình", "Học phí dưới 5 triệu"].map((c) => (
              <span key={c} style={{ fontFamily: "var(--font-body)", fontWeight: 600, fontSize: 13, color: "var(--brand-strong)", background: "var(--surface-card)", border: "1.5px solid var(--border-brand)", borderRadius: "var(--radius-pill)", padding: "7px 13px" }}>{c}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
