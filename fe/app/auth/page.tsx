"use client";

import { useState, type CSSProperties } from "react";
import Link from "next/link";
import LuminaLogo from "../_components/LuminaLogo";

const inputStyle: CSSProperties = {
  height: 48,
  padding: "0 15px",
  border: "1.5px solid var(--border-default)",
  borderRadius: "var(--radius-lg)",
  fontFamily: "var(--font-body)",
  fontSize: 15,
  color: "var(--text-strong)",
  background: "var(--surface-card)",
  transition: "border-color .15s, box-shadow .15s",
};

const labelText: CSSProperties = { fontSize: 13.5, fontWeight: 700, color: "var(--text-strong)" };

const tabBase: CSSProperties = {
  flex: 1,
  height: 38,
  border: "none",
  borderRadius: "var(--radius-pill)",
  cursor: "pointer",
  fontFamily: "var(--font-body)",
  fontWeight: 700,
  fontSize: 14.5,
};
const activeTab: CSSProperties = { ...tabBase, background: "var(--surface-card)", color: "var(--brand-strong)", boxShadow: "var(--shadow-xs)" };
const idleTab: CSSProperties = { ...tabBase, background: "transparent", color: "var(--text-muted)" };

const benefits = [
  "Tư vấn riêng theo khu vực & học phí",
  "Lưu hồ sơ & nhắc lịch qua Zalo",
  "Miễn phí, riêng tư, sẵn sàng 24/7",
];

const heroAvatars = [
  { t: "AN", bg: "var(--teal-400)" },
  { t: "BÌ", bg: "var(--sun-400)" },
  { t: "CH", bg: "var(--sky-400)" },
];

export default function AuthPage() {
  const [mode, setMode] = useState<"register" | "login">("register");
  const isRegister = mode === "register";

  return (
    <div style={{ minHeight: "100vh", display: "flex", fontFamily: "var(--font-body)", color: "var(--text-body)" }}>
      {/* ===== LEFT · BRAND PANEL ===== */}
      <aside className="az-brand" style={{ position: "relative", flex: "0 0 44%", background: "var(--brand)", overflow: "hidden", padding: "48px 52px", flexDirection: "column", display: "flex" }}>
        <div style={{ position: "absolute", inset: 0, background: "radial-gradient(560px 420px at 78% 6%, rgba(255,255,255,.16) 0%, rgba(255,255,255,0) 60%)" }} />
        <div style={{ position: "absolute", width: 170, height: 170, right: -44, top: "34%", background: "var(--sun-400)", borderRadius: "46% 54% 60% 40%/52% 44% 56% 48%", opacity: 0.85, animation: "az-fa 8s ease-in-out infinite" }} />
        <div style={{ position: "absolute", width: 96, height: 96, left: -30, bottom: "14%", background: "rgba(255,255,255,.16)", borderRadius: "50%", animation: "az-fb 7s ease-in-out infinite" }} />

        <Link href="/" style={{ position: "relative", display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
          <LuminaLogo size={36} tone="white" />
          <span style={{ fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 22, color: "#fff" }}>LuminaAi</span>
        </Link>

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
                  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12 5 5L20 7" /></svg>
                </span>
                {b}
              </li>
            ))}
          </ul>
        </div>

        <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 11 }}>
          <div style={{ display: "flex" }}>
            {heroAvatars.map((a, i) => (
              <span key={a.t} style={{ width: 32, height: 32, borderRadius: "50%", background: a.bg, color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 12, border: "2px solid var(--brand)", marginLeft: i === 0 ? 0 : -10 }}>{a.t}</span>
            ))}
          </div>
          <span style={{ color: "var(--teal-50)", fontSize: 14 }}><strong style={{ color: "#fff" }}>12.000+</strong> ba mẹ đã tin dùng</span>
        </div>
      </aside>

      {/* ===== RIGHT · FORM ===== */}
      <main style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 24px", background: "radial-gradient(600px 380px at 90% -10%, var(--brand-subtle) 0%, rgba(247,250,250,0) 60%)" }}>
        <div style={{ width: "100%", maxWidth: 412 }}>
          {/* Tabs */}
          <div style={{ display: "flex", gap: 4, padding: 4, background: "var(--ink-100)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-pill)", marginBottom: 26 }}>
            <button onClick={() => setMode("register")} style={isRegister ? activeTab : idleTab}>Đăng ký</button>
            <button onClick={() => setMode("login")} style={isRegister ? idleTab : activeTab}>Đăng nhập</button>
          </div>

          <h1 style={{ fontSize: 28, margin: "0 0 6px", color: "var(--text-strong)" }}>{isRegister ? "Tạo tài khoản" : "Chào mừng trở lại"}</h1>
          <p style={{ fontSize: 15, color: "var(--text-muted)", margin: "0 0 24px" }}>{isRegister ? "Bắt đầu hành trình tìm trường cho con cùng LuminaAi." : "Đăng nhập để tiếp tục cuộc trò chuyện của bạn."}</p>

          {/* Google */}
          <button className="az-google" style={{ width: "100%", height: 50, display: "flex", alignItems: "center", justifyContent: "center", gap: 11, background: "var(--surface-card)", border: "1.5px solid var(--border-default)", borderRadius: "var(--radius-lg)", fontFamily: "var(--font-body)", fontWeight: 700, fontSize: 15, color: "var(--text-strong)", cursor: "pointer", transition: "background .15s, border-color .15s" }}>
            <svg width="20" height="20" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.7-6.1 8-11.3 8a12 12 0 1 1 7.9-21l5.7-5.7A20 20 0 1 0 24 44a20 20 0 0 0 19.6-23.5Z" /><path fill="#FF3D00" d="m6.3 14.7 6.6 4.8A12 12 0 0 1 24 12c3 0 5.8 1.2 7.9 3l5.7-5.7A20 20 0 0 0 6.3 14.7Z" /><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2A12 12 0 0 1 12.7 28l-6.5 5C9.6 39.6 16.3 44 24 44Z" /><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3a12 12 0 0 1-4.1 5.6l6.2 5.2C39 39.9 44 33.6 44 24c0-1.2-.1-2.4-.4-3.5Z" /></svg>
            Tiếp tục với Google
          </button>

          {/* divider */}
          <div style={{ display: "flex", alignItems: "center", gap: 14, margin: "20px 0" }}>
            <span style={{ flex: 1, height: 1, background: "var(--border-subtle)" }} />
            <span style={{ fontSize: 13, color: "var(--text-subtle)" }}>hoặc dùng email</span>
            <span style={{ flex: 1, height: 1, background: "var(--border-subtle)" }} />
          </div>

          {/* form */}
          <form onSubmit={(e) => e.preventDefault()} style={{ display: "flex", flexDirection: "column", gap: 15 }}>
            {isRegister && (
              <label style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                <span style={labelText}>Họ và tên</span>
                <input className="az-input" type="text" placeholder="Nguyễn Thu Hà" style={inputStyle} />
              </label>
            )}
            <label style={{ display: "flex", flexDirection: "column", gap: 7 }}>
              <span style={labelText}>Email</span>
              <input className="az-input" type="email" placeholder="bame@email.com" style={inputStyle} />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 7 }}>
              <span style={{ ...labelText, display: "flex", alignItems: "center" }}>
                Mật khẩu
                {!isRegister && <a href="#" style={{ marginLeft: "auto", fontWeight: 600, fontSize: 13, color: "var(--brand-strong)", textDecoration: "none" }}>Quên mật khẩu?</a>}
              </span>
              <input className="az-input" type="password" placeholder="Tối thiểu 8 ký tự" style={inputStyle} />
            </label>

            {isRegister && (
              <label style={{ display: "flex", alignItems: "flex-start", gap: 10, fontSize: 13.5, color: "var(--text-muted)", lineHeight: 1.5, marginTop: 1 }}>
                <input type="checkbox" style={{ width: 18, height: 18, marginTop: 1, accentColor: "var(--brand)", flex: "0 0 auto" }} />
                <span>Tôi đồng ý với <a href="#" style={{ color: "var(--brand-strong)", fontWeight: 600, textDecoration: "none" }}>Điều khoản</a> và <a href="#" style={{ color: "var(--brand-strong)", fontWeight: 600, textDecoration: "none" }}>Chính sách bảo mật</a> của LuminaAi.</span>
              </label>
            )}

            <Link href="/chat" className="gw-btn gw-btn--primary gw-btn--lg" style={{ width: "100%", marginTop: 6 }}>
              {isRegister ? "Tạo tài khoản" : "Đăng nhập"}
              <span className="gw-btn__icon"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg></span>
            </Link>
          </form>

          <p style={{ textAlign: "center", fontSize: 14.5, color: "var(--text-muted)", margin: "22px 0 0" }}>
            {isRegister ? "Đã có tài khoản?" : "Chưa có tài khoản?"}{" "}
            <a href="#" onClick={(e) => { e.preventDefault(); setMode(isRegister ? "login" : "register"); }} style={{ color: "var(--brand-strong)", fontWeight: 700, textDecoration: "none" }}>
              {isRegister ? "Đăng nhập" : "Đăng ký ngay"}
            </a>
          </p>
        </div>
      </main>
    </div>
  );
}
