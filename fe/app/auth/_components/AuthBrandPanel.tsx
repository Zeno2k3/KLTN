import AvatarGroup from "@/app/components/ui/AvatarGroup";
import Icon from "@/app/components/ui/Icon";
import LuminaLogo from "@/app/components/ui/LuminaLogo";
import LogoLockup from "@/app/components/common/LogoLockup";
import { benefits, heroAvatars } from "@/app/lib/data/auth";

/** Panel thương hiệu bên trái trang auth. */
export default function AuthBrandPanel() {
  return (
    <aside className="az-brand" style={{ position: "relative", flex: "0 0 44%", background: "var(--brand)", overflow: "hidden", padding: "48px 52px", flexDirection: "column", display: "flex" }}>
      <div style={{ position: "absolute", inset: 0, background: "radial-gradient(560px 420px at 78% 6%, rgba(255,255,255,.16) 0%, rgba(255,255,255,0) 60%)" }} />
      <div style={{ position: "absolute", width: 170, height: 170, right: -44, top: "34%", background: "var(--sun-400)", borderRadius: "46% 54% 60% 40%/52% 44% 56% 48%", opacity: 0.85, animation: "az-fa 8s ease-in-out infinite" }} />
      <div style={{ position: "absolute", width: 96, height: 96, left: -30, bottom: "14%", background: "rgba(255,255,255,.16)", borderRadius: "50%", animation: "az-fb 7s ease-in-out infinite" }} />

      <LogoLockup href="/" logoSize={36} tone="white" wordmarkColor="#fff" wordmarkSize={22} style={{ position: "relative" }} />

      <div style={{ position: "relative", marginTop: "auto", marginBottom: "auto" }}>
        <div style={{ display: "inline-flex", animation: "az-bob 4.5s ease-in-out infinite", marginBottom: 20 }}>
          <LuminaLogo size={92} tone="white" style={{ filter: "drop-shadow(0 16px 30px rgba(7,40,40,.34))" }} />
        </div>
        <h2 style={{ fontSize: 34, lineHeight: 1.18, color: "#fff", margin: "0 0 14px" }}>Người bạn AI đồng hành cùng ba mẹ mùa vào lớp 1</h2>
        <p style={{ fontSize: 17, color: "var(--teal-50)", lineHeight: 1.55, margin: "0 0 26px", maxWidth: 380 }}>Tạo tài khoản để lưu lại cuộc trò chuyện, danh sách trường yêu thích và lịch tham quan của bé.</p>
        <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 13 }}>
          {benefits.map((b) => (
            <li key={b} style={{ display: "flex", alignItems: "center", gap: 11, color: "#fff", fontSize: 15.5 }}>
              <span style={{ flex: "0 0 auto", width: 26, height: 26, borderRadius: "50%", background: "rgba(255,255,255,.18)", display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
                <Icon name="check" size={15} />
              </span>
              {b}
            </li>
          ))}
        </ul>
      </div>

      <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 11 }}>
        <AvatarGroup items={heroAvatars} size={32} overlap={10} border="2px solid var(--brand)" fontSize={12} />
        <span style={{ color: "var(--teal-50)", fontSize: 14 }}><strong style={{ color: "#fff" }}>12.000+</strong> ba mẹ đã tin dùng</span>
      </div>
    </aside>
  );
}
