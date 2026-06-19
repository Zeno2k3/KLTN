import IconBox from "@/app/components/ui/IconBox";
import SectionHeading from "@/app/components/ui/SectionHeading";
import { STEPS } from "@/app/lib/data/landing";

export default function HowItWorksSection() {
  return (
    <section id="cachhoatdong" style={{ maxWidth: 1180, margin: "0 auto", padding: "64px 24px 20px" }}>
      <SectionHeading eyebrow="Đơn giản như nhắn tin" title="Chỉ 3 bước, ba mẹ an tâm" />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 22 }}>
        {STEPS.map((s) => (
          <div key={s.n} className="gw-card gw-card--pad" style={{ position: "relative" }}>
            <span style={{ position: "absolute", top: 18, right: 20, fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 46, color: s.numColor, lineHeight: 1 }}>{s.n}</span>
            <IconBox size={50} bg={s.bg} color="#fff" style={{ marginBottom: 16 }}>
              <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{s.icon}</svg>
            </IconBox>
            <h3 style={{ fontSize: 20, margin: "0 0 8px", color: "var(--text-strong)" }}>{s.title}</h3>
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 15, lineHeight: 1.55 }}>{s.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
