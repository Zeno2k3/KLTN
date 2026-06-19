import Button from "@/app/components/ui/Button";
import Icon from "@/app/components/ui/Icon";
import LuminaLogo from "@/app/components/ui/LuminaLogo";

export default function LandingCTA() {
  return (
    <section style={{ maxWidth: 1180, margin: "60px auto 64px", padding: "0 24px" }}>
      <div style={{ position: "relative", background: "var(--brand)", borderRadius: "var(--radius-2xl)", padding: "48px 44px", display: "flex", alignItems: "center", gap: 34, boxShadow: "var(--shadow-brand-lg)", overflow: "hidden" }}>
        <div style={{ position: "absolute", width: 220, height: 220, right: -40, top: -60, background: "rgba(255,255,255,.1)", borderRadius: "50%" }} />
        <div style={{ flex: "0 0 auto", display: "inline-flex", animation: "lp-bob 4.5s ease-in-out infinite" }}>
          <LuminaLogo size={116} tone="white" />
        </div>
        <div style={{ flex: 1, position: "relative" }}>
          <h2 style={{ color: "#fff", fontSize: 34, margin: "0 0 10px" }}>Sẵn sàng tìm trường cho con?</h2>
          <p style={{ color: "var(--teal-50)", fontSize: 18, margin: 0, maxWidth: 560 }}>Trò chuyện với LuminaAi ngay hôm nay — miễn phí, riêng tư, và luôn sẵn sàng 24/7.</p>
        </div>
        <Button href="/chat" variant="accent" size="lg" style={{ position: "relative", flex: "0 0 auto" }} iconRight={<Icon name="arrow-right" />}>Hỏi LuminaAi ngay</Button>
      </div>
    </section>
  );
}
