import Avatar from "@/app/components/ui/Avatar";
import Icon from "@/app/components/ui/Icon";
import SectionHeading from "@/app/components/ui/SectionHeading";
import { REVIEWS } from "@/app/lib/data/landing";

export default function ReviewsSection() {
  return (
    <section id="danhgia" style={{ maxWidth: 1180, margin: "0 auto", padding: "64px 24px 20px" }}>
      <SectionHeading eyebrow="Ba mẹ nói gì" title="Hàng nghìn gia đình đã an tâm hơn" />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 20 }}>
        {REVIEWS.map((r) => (
          <div key={r.name} className="gw-card gw-card--pad" style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", gap: 3, color: "var(--accent)", marginBottom: 12 }}>
              {Array.from({ length: 5 }).map((_, i) => <Icon key={i} name="star" size={18} />)}
            </div>
            <p style={{ margin: "0 0 18px", fontSize: 15.5, lineHeight: 1.6, color: "var(--text-body)", textWrap: "pretty" }}>“{r.quote}”</p>
            <div style={{ display: "flex", alignItems: "center", gap: 11, marginTop: "auto" }}>
              <Avatar initials={r.initial} bg={r.color} size={42} fontSize={15} />
              <span>
                <span style={{ display: "block", fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 15, color: "var(--text-strong)" }}>{r.name}</span>
                <span style={{ display: "block", fontSize: 13, color: "var(--text-subtle)" }}>{r.area}</span>
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
