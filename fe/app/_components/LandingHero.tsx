import Button from "@/app/components/ui/Button";
import Icon from "@/app/components/ui/Icon";
import AvatarGroup from "@/app/components/ui/AvatarGroup";
import { AVATARS } from "@/app/lib/data/landing";
import ChatPreviewCard from "./ChatPreviewCard";

export default function LandingHero() {
  return (
    <section style={{ position: "relative", background: "radial-gradient(900px 520px at 88% -8%, var(--teal-50) 0%, rgba(236,248,248,0) 60%), radial-gradient(620px 460px at 6% 18%, var(--sun-50) 0%, rgba(255,244,236,0) 55%)", overflow: "hidden" }}>
      <div style={{ maxWidth: 1180, margin: "0 auto", padding: "72px 24px 60px", display: "grid", gridTemplateColumns: "1.04fr .96fr", gap: 52, alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: 54, lineHeight: 1.07, margin: "20px 0 18px", color: "var(--text-strong)" }}>
            Chọn trường tiểu học cho con,<br />
            <span style={{ color: "var(--brand)" }}>nhẹ tênh</span> cùng <span style={{ color: "var(--accent)" }}>LuminaAi</span>
          </h1>
          <p style={{ fontSize: 20, color: "var(--text-muted)", lineHeight: 1.55, maxWidth: 520, margin: "0 0 30px" }}>
            Trợ lý AI trả lời mọi thắc mắc về điều kiện nhập học, hồ sơ, học phí và giúp ba mẹ đặt lịch tham quan trường — 24/7, hoàn toàn miễn phí.
          </p>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <Button href="/chat" variant="accent" size="lg" iconRight={<Icon name="arrow-right" />}>Bắt đầu tư vấn</Button>
            <Button href="#cachhoatdong" variant="secondary" size="lg" iconLeft={<Icon name="play" />}>Xem cách hoạt động</Button>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 30 }}>
            <AvatarGroup items={AVATARS} size={38} overlap={11} border="2px solid var(--surface-page)" fontSize={14} />
            <div style={{ fontSize: 14, color: "var(--text-muted)" }}>
              <strong style={{ color: "var(--text-strong)" }}>12.000+</strong> ba mẹ đã được LuminaAi hỗ trợ
            </div>
          </div>
        </div>

        <ChatPreviewCard />
      </div>
    </section>
  );
}
