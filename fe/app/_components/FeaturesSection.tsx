import IconBox from "@/app/components/ui/IconBox";
import SectionHeading from "@/app/components/ui/SectionHeading";
import { FEATURES } from "@/app/lib/data/landing";

export default function FeaturesSection() {
  return (
    <section id="tinhnang" style={{ maxWidth: 1180, margin: "0 auto", padding: "64px 24px 20px" }}>
      <SectionHeading eyebrow="LuminaAi giúp được gì" title="Đồng hành cùng ba mẹ từ A đến Z" />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 20 }}>
        {FEATURES.map((f) => (
          <div key={f.title} className="gw-card gw-card--pad gw-card--interactive">
            <IconBox size={54} bg={f.tint} color={f.fg} style={{ marginBottom: 16 }}>
              <svg viewBox="0 0 24 24" width="27" height="27" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{f.icon}</svg>
            </IconBox>
            <h3 style={{ fontSize: 19, margin: "0 0 8px", color: "var(--text-strong)" }}>{f.title}</h3>
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 15, lineHeight: 1.5 }}>{f.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
