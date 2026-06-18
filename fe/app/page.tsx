import Link from "next/link";
import LuminaLogo from "./_components/LuminaLogo";

const PARTNERS = [
  { name: "Vinschool", initial: "V" },
  { name: "Hệ thống EMASI", initial: "E" },
  { name: "TH Lê Quý Đôn", initial: "LQ" },
  { name: "Quốc tế Á Châu", initial: "ÁC" },
  { name: "Wellspring Saigon", initial: "W" },
  { name: "TH Nguyễn Bỉnh Khiêm", initial: "NBK" },
  { name: "TH Kim Đồng", initial: "KĐ" },
  { name: "Sở GD&ĐT TP.HCM", initial: "GD" },
];

const REVIEWS = [
  { name: "Chị Hồng Nhung", area: "Phụ huynh bé Bốp · Quận 7", initial: "HN", color: "var(--teal-400)", quote: "Lần đầu cho con vào lớp 1 mình rất lo, LuminaAi giải thích từng bước rõ ràng và nhẹ nhàng. Yên tâm hẳn." },
  { name: "Anh Minh Tuấn", area: "Phụ huynh bé Su · TP. Thủ Đức", initial: "MT", color: "var(--sky-400)", quote: "Hỏi lúc nửa đêm vẫn được trả lời ngay. Tiết kiệm bao nhiêu thời gian gọi tổng đài tuyển sinh." },
  { name: "Chị Thu Hà", area: "Phụ huynh bé Nhím · Bình Thạnh", initial: "TH", color: "var(--sun-400)", quote: "Được gợi ý 3 trường gần nhà đúng tầm học phí, lại còn đặt lịch tham quan giúp mình luôn." },
  { name: "Chị Lan Anh", area: "Phụ huynh bé Kem · Gò Vấp", initial: "LA", color: "var(--teal-500)", quote: "Danh sách hồ sơ rất chi tiết, mình chuẩn bị đầy đủ không thiếu một loại giấy tờ nào." },
  { name: "Anh Đức Thành", area: "Phụ huynh bé Bin · Quận 1", initial: "ĐT", color: "var(--sky-500)", quote: "Giao diện dễ thương, con mình mê cái robot. Tư vấn nhiệt tình mà lại hoàn toàn miễn phí." },
  { name: "Chị Phương Mai", area: "Phụ huynh bé Na · Tân Bình", initial: "PM", color: "var(--sun-500)", quote: "Mình hỏi về tuyển sinh trái tuyến, LuminaAi hướng dẫn cặn kẽ và rất trung thực. Cảm ơn nhiều!" },
];

const STATS = [
  { value: "12.000+", label: "ba mẹ đã được hỗ trợ", color: "var(--brand)" },
  { value: "350+", label: "trường tiểu học trong dữ liệu", color: "var(--accent)" },
  { value: "50.000+", label: "câu hỏi đã được giải đáp", color: "var(--sky-500)" },
  { value: "24/7", label: "luôn sẵn sàng trả lời", color: "var(--brand)" },
];

const ArrowRight = () => (
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
);
const Star = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12 3l2.7 5.5 6 .9-4.3 4.2 1 6-5.4-2.8L6.6 19.6l1-6L3.3 9.4l6-.9Z" /></svg>
);

const AVATARS = [
  { t: "AN", bg: "var(--teal-400)" },
  { t: "BÌ", bg: "var(--sky-400)" },
  { t: "CH", bg: "var(--sun-400)" },
  { t: "DU", bg: "var(--teal-500)" },
];

const FEATURES = [
  {
    tint: "var(--teal-50)", fg: "var(--brand)", title: "Hỏi đáp tức thì",
    body: "Trả lời ngay mọi câu hỏi về tuyển sinh, không cần chờ tổng đài hay xếp hàng.",
    icon: <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />,
  },
  {
    tint: "var(--sun-50)", fg: "var(--accent)", title: "Gợi ý trường phù hợp",
    body: "Đề xuất trường theo khu vực, học phí và mong muốn riêng của từng gia đình.",
    icon: <><path d="M22 10 12 5 2 10l10 5 10-5Z" /><path d="M6 12v5c0 1.4 2.7 3 6 3s6-1.6 6-3v-5" /></>,
  },
  {
    tint: "var(--sky-50)", fg: "var(--sky-500)", title: "Hướng dẫn hồ sơ",
    body: "Danh sách giấy tờ cần chuẩn bị và mẫu đơn, hướng dẫn từng bước rõ ràng.",
    icon: <><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" /><rect x="9" y="3" width="6" height="4" rx="1" /><path d="m9 14 2 2 4-4" /></>,
  },
  {
    tint: "var(--teal-50)", fg: "var(--brand)", title: "Đặt lịch tham quan",
    body: "Chọn lịch tham quan trường và nhận nhắc nhở nhẹ nhàng qua Zalo.",
    icon: <><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /><path d="m9 16 2 2 4-4" /></>,
  },
];

const STEPS = [
  {
    n: "01", numColor: "var(--teal-100)", bg: "var(--brand)", title: "Đặt câu hỏi",
    body: "Nhắn cho LuminaAi bất cứ điều gì về tuyển sinh lớp 1 — bằng tiếng Việt, tự nhiên như trò chuyện.",
    icon: <><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /><path d="M8 9h8M8 13h5" /></>,
  },
  {
    n: "02", numColor: "var(--sun-100)", bg: "var(--accent)", title: "Cá nhân hóa tư vấn",
    body: "LuminaAi gợi ý trường, giải thích hồ sơ và học phí phù hợp với khu vực và mong muốn của gia đình.",
    icon: <><path d="M15 14c.2-1 .7-1.7 1.5-2.5A4.5 4.5 0 1 0 7.5 11.5c.8.8 1.3 1.5 1.5 2.5" /><path d="M9 18h6M10 22h4" /></>,
  },
  {
    n: "03", numColor: "var(--sky-100)", bg: "var(--sky-500)", title: "Đặt lịch & đăng ký",
    body: "Đặt lịch tham quan và hoàn tất hồ sơ đăng ký ngay trong vài phút, có nhắc nhở qua Zalo.",
    icon: <><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /><path d="m9 16 2 2 4-4" /></>,
  },
];

const navLink = { padding: "8px 13px", borderRadius: "var(--radius-pill)", color: "var(--text-muted)", fontWeight: 700, fontSize: 15, textDecoration: "none" } as const;

export default function LandingPage() {
  return (
    <div style={{ fontFamily: "var(--font-body)", color: "var(--text-body)", background: "var(--surface-page)", overflowX: "hidden" }}>
      {/* ============ NAV ============ */}
      <header style={{ position: "sticky", top: 0, zIndex: 30, background: "rgba(247,250,250,.82)", backdropFilter: "blur(10px)", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ maxWidth: 1180, margin: "0 auto", padding: "13px 24px", display: "flex", alignItems: "center", gap: 22 }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
            <LuminaLogo size={34} tone="brand" />
            <span style={{ fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 22, letterSpacing: "-.02em", color: "var(--text-strong)" }}>LuminaAi</span>
          </Link>
          <nav style={{ display: "flex", gap: 2, marginLeft: 8 }}>
            <a href="#tinhnang" style={navLink}>Tính năng</a>
            <a href="#cachhoatdong" style={navLink}>Cách hoạt động</a>
            <a href="#donvi" style={navLink}>Đồng hành</a>
            <a href="#danhgia" style={navLink}>Đánh giá</a>
          </nav>
          <div style={{ marginLeft: "auto", display: "flex", gap: 10, alignItems: "center" }}>
            <Link href="/auth" className="gw-btn gw-btn--ghost gw-btn--sm">Đăng ký</Link>
            <Link href="/chat" className="gw-btn gw-btn--primary gw-btn--sm">
              <span className="gw-btn__icon"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" /></svg></span>
              Hỏi LuminaAi
            </Link>
          </div>
        </div>
      </header>

      {/* ============ HERO · SPLIT ============ */}
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
              <Link href="/chat" className="gw-btn gw-btn--lg gw-btn--accent">Bắt đầu tư vấn<span className="gw-btn__icon"><ArrowRight /></span></Link>
              <a href="#cachhoatdong" className="gw-btn gw-btn--secondary gw-btn--lg">
                <span className="gw-btn__icon"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M7 4v16l13-8Z" /></svg></span>
                Xem cách hoạt động
              </a>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 30 }}>
              <div style={{ display: "flex" }}>
                {AVATARS.map((a, i) => (
                  <span key={a.t} style={{ width: 38, height: 38, borderRadius: "50%", background: a.bg, color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 14, border: "2px solid var(--surface-page)", marginLeft: i === 0 ? 0 : -11 }}>{a.t}</span>
                ))}
              </div>
              <div style={{ fontSize: 14, color: "var(--text-muted)" }}><strong style={{ color: "var(--text-strong)" }}>12.000+</strong> ba mẹ đã được LuminaAi hỗ trợ</div>
            </div>
          </div>

          <div style={{ position: "relative" }}>
            <div style={{ position: "absolute", width: 120, height: 120, right: -26, top: -30, background: "var(--sun-200)", borderRadius: "42% 58% 60% 40%/45% 45% 55% 55%", opacity: 0.7, animation: "lp-float-a 7s ease-in-out infinite" }} />
            <div style={{ position: "absolute", width: 86, height: 86, left: -30, bottom: 24, background: "var(--teal-200)", borderRadius: "50%", opacity: 0.7, animation: "lp-float-b 6s ease-in-out infinite" }} />
            <div className="gw-card gw-card--raised" style={{ position: "relative", padding: 0, overflow: "hidden" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "14px 18px", borderBottom: "1px solid var(--border-subtle)" }}>
                <span style={{ background: "var(--brand)", borderRadius: 12, padding: 5, display: "inline-flex" }}><LuminaLogo size={26} tone="white" /></span>
                <strong style={{ fontFamily: "var(--font-display)", fontSize: 16 }}>LuminaAi</strong>
                <span className="gw-badge gw-badge--success gw-badge--dot" style={{ marginLeft: "auto" }}>trực tuyến</span>
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
        </div>
      </section>

      {/* ============ STATS ============ */}
      <section style={{ maxWidth: 1180, margin: "0 auto", padding: "46px 24px 8px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 18 }}>
          {STATS.map((s) => (
            <div key={s.label} className="gw-card gw-card--pad" style={{ textAlign: "center" }}>
              <div style={{ fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 38, color: s.color, lineHeight: 1 }}>{s.value}</div>
              <div style={{ marginTop: 8, fontSize: 15, color: "var(--text-muted)" }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ============ FEATURES ============ */}
      <section id="tinhnang" style={{ maxWidth: 1180, margin: "0 auto", padding: "64px 24px 20px" }}>
        <div style={{ textAlign: "center", marginBottom: 42 }}>
          <span className="gw-eyebrow">LuminaAi giúp được gì</span>
          <h2 style={{ fontSize: 40, margin: "10px 0 0", color: "var(--text-strong)" }}>Đồng hành cùng ba mẹ từ A đến Z</h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 20 }}>
          {FEATURES.map((f) => (
            <div key={f.title} className="gw-card gw-card--pad gw-card--interactive">
              <span style={{ display: "inline-flex", width: 54, height: 54, borderRadius: "var(--radius-lg)", background: f.tint, color: f.fg, alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
                <svg viewBox="0 0 24 24" width="27" height="27" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{f.icon}</svg>
              </span>
              <h3 style={{ fontSize: 19, margin: "0 0 8px", color: "var(--text-strong)" }}>{f.title}</h3>
              <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 15, lineHeight: 1.5 }}>{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ============ HOW IT WORKS ============ */}
      <section id="cachhoatdong" style={{ maxWidth: 1180, margin: "0 auto", padding: "64px 24px 20px" }}>
        <div style={{ textAlign: "center", marginBottom: 42 }}>
          <span className="gw-eyebrow">Đơn giản như nhắn tin</span>
          <h2 style={{ fontSize: 40, margin: "10px 0 0", color: "var(--text-strong)" }}>Chỉ 3 bước, ba mẹ an tâm</h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 22 }}>
          {STEPS.map((s) => (
            <div key={s.n} className="gw-card gw-card--pad" style={{ position: "relative" }}>
              <span style={{ position: "absolute", top: 18, right: 20, fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 46, color: s.numColor, lineHeight: 1 }}>{s.n}</span>
              <span style={{ display: "inline-flex", width: 50, height: 50, borderRadius: "var(--radius-lg)", background: s.bg, color: "#fff", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
                <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{s.icon}</svg>
              </span>
              <h3 style={{ fontSize: 20, margin: "0 0 8px", color: "var(--text-strong)" }}>{s.title}</h3>
              <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 15, lineHeight: 1.55 }}>{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ============ PARTNERS ============ */}
      <section id="donvi" style={{ maxWidth: 1180, margin: "0 auto", padding: "64px 24px 20px" }}>
        <div style={{ textAlign: "center", marginBottom: 36 }}>
          <span className="gw-eyebrow">Đơn vị đồng hành</span>
          <h2 style={{ fontSize: 34, margin: "10px 0 8px", color: "var(--text-strong)" }}>Tin cậy bởi các trường &amp; tổ chức giáo dục</h2>
          <p style={{ fontSize: 16, color: "var(--text-muted)", margin: 0 }}>Dữ liệu tuyển sinh được cập nhật cùng các đơn vị đồng hành trên toàn quốc.</p>
        </div>
        <div className="lp-marquee-mask" style={{ position: "relative", WebkitMaskImage: "linear-gradient(90deg, transparent, #000 9%, #000 91%, transparent)", maskImage: "linear-gradient(90deg, transparent, #000 9%, #000 91%, transparent)" }}>
          <div className="lp-marquee-track">
            {[...PARTNERS, ...PARTNERS].map((p, i) => (
              <div key={`${p.name}-${i}`} className="gw-card gw-card--pad" style={{ flex: "0 0 auto", display: "flex", alignItems: "center", gap: 13, padding: "16px 22px" }}>
                <span style={{ flex: "0 0 auto", width: 44, height: 44, borderRadius: 13, background: "var(--brand-subtle)", color: "var(--brand-strong)", display: "inline-flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 16 }}>{p.initial}</span>
                <span style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 15, color: "var(--text-strong)", lineHeight: 1.25, whiteSpace: "nowrap" }}>{p.name}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ REVIEWS ============ */}
      <section id="danhgia" style={{ maxWidth: 1180, margin: "0 auto", padding: "64px 24px 20px" }}>
        <div style={{ textAlign: "center", marginBottom: 42 }}>
          <span className="gw-eyebrow">Ba mẹ nói gì</span>
          <h2 style={{ fontSize: 40, margin: "10px 0 0", color: "var(--text-strong)" }}>Hàng nghìn gia đình đã an tâm hơn</h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 20 }}>
          {REVIEWS.map((r) => (
            <div key={r.name} className="gw-card gw-card--pad" style={{ display: "flex", flexDirection: "column" }}>
              <div style={{ display: "flex", gap: 3, color: "var(--accent)", marginBottom: 12 }}>
                {Array.from({ length: 5 }).map((_, i) => <Star key={i} />)}
              </div>
              <p style={{ margin: "0 0 18px", fontSize: 15.5, lineHeight: 1.6, color: "var(--text-body)", textWrap: "pretty" }}>“{r.quote}”</p>
              <div style={{ display: "flex", alignItems: "center", gap: 11, marginTop: "auto" }}>
                <span style={{ flex: "0 0 auto", width: 42, height: 42, borderRadius: "50%", background: r.color, color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 15 }}>{r.initial}</span>
                <span>
                  <span style={{ display: "block", fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 15, color: "var(--text-strong)" }}>{r.name}</span>
                  <span style={{ display: "block", fontSize: 13, color: "var(--text-subtle)" }}>{r.area}</span>
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ============ CTA ============ */}
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
          <Link href="/chat" className="gw-btn gw-btn--accent gw-btn--lg" style={{ position: "relative", flex: "0 0 auto" }}>Hỏi LuminaAi ngay<span className="gw-btn__icon"><ArrowRight /></span></Link>
        </div>
      </section>

      {/* ============ FOOTER ============ */}
      <footer style={{ borderTop: "1px solid var(--border-subtle)", background: "var(--surface-card)" }}>
        <div style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 24px", display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
          <LuminaLogo size={30} tone="brand" />
          <span style={{ fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 18, color: "var(--text-strong)" }}>LuminaAi</span>
          <span style={{ color: "var(--text-subtle)", fontSize: 14 }}>· Trợ lý tư vấn tuyển sinh tiểu học</span>
          <div style={{ marginLeft: "auto", display: "flex", gap: 18, fontSize: 14, color: "var(--text-muted)" }}>
            <a href="#" style={{ color: "inherit", textDecoration: "none" }}>Về LuminaAi</a>
            <a href="#" style={{ color: "inherit", textDecoration: "none" }}>Bảo mật</a>
            <a href="#" style={{ color: "inherit", textDecoration: "none" }}>Liên hệ</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
