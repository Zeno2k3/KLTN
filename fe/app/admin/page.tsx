"use client";

import { useState, type CSSProperties, type ReactNode } from "react";
import Link from "next/link";
import LuminaLogo from "../_components/LuminaLogo";

type Status = "ready" | "processing";
type Doc = { id: number; name: string; meta: string; status: Status };

const ICONS: Record<string, ReactNode> = {
  chat: <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />,
  users: <><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>,
  q: <><circle cx="12" cy="12" r="10" /><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3" /><path d="M12 17h.01" /></>,
  doc: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /></>,
};

const StatIcon = ({ name }: { name: string }) => (
  <svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{ICONS[name]}</svg>
);

const CHART_RAW = [
  { label: "Tuần 1", v: 820 }, { label: "Tuần 2", v: 1040 }, { label: "Tuần 3", v: 960 },
  { label: "Tuần 4", v: 1380 }, { label: "Tuần 5", v: 1610 }, { label: "Tuần 6", v: 1920 },
];
const CHART_MAX = Math.max(...CHART_RAW.map((r) => r.v));
const CHART = CHART_RAW.map((r) => ({ label: r.label, value: (r.v / 1000).toFixed(1).replace(".", ",") + "K", h: Math.round((r.v / CHART_MAX) * 100) + "%" }));

const TOPICS = [
  { label: "Điều kiện nhập học", pct: "82%", color: "var(--brand)" },
  { label: "Hồ sơ & giấy tờ", pct: "64%", color: "var(--sky-500)" },
  { label: "Học phí", pct: "53%", color: "var(--sun-400)" },
  { label: "Lịch tham quan", pct: "37%", color: "var(--teal-400)" },
];

const SEED_DOCS: Doc[] = [
  { id: 1, name: "Quy chế tuyển sinh lớp 1 năm 2026.pdf", meta: "1,8 MB · thêm 12/06/2026", status: "ready" },
  { id: 2, name: "Hướng dẫn chuẩn bị hồ sơ nhập học.pdf", meta: "920 KB · thêm 12/06/2026", status: "ready" },
  { id: 3, name: "Biểu phí các trường tiểu học Q.7.pdf", meta: "2,3 MB · thêm 10/06/2026", status: "ready" },
  { id: 4, name: "Danh sách trường & chỉ tiêu 2026.pdf", meta: "1,1 MB · thêm 08/06/2026", status: "processing" },
];

const navBase: CSSProperties = {
  display: "flex", alignItems: "center", gap: 12, width: "100%", textAlign: "left", padding: "11px 13px",
  border: "none", borderRadius: 12, cursor: "pointer", fontFamily: "var(--font-body)", fontWeight: 700, fontSize: 15,
  transition: "background .15s, color .15s",
};
const navActive: CSSProperties = { ...navBase, background: "var(--brand)", color: "#fff", boxShadow: "var(--shadow-brand)" };
const navIdle: CSSProperties = { ...navBase, background: "transparent", color: "var(--text-muted)" };

export default function AdminPage() {
  const [tab, setTab] = useState<"stats" | "docs">("stats");
  const [docs, setDocs] = useState<Doc[]>(SEED_DOCS);
  const [nextId, setNextId] = useState(5);
  const isStats = tab === "stats";

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;
    const today = new Date();
    const dd = String(today.getDate()).padStart(2, "0") + "/" + String(today.getMonth() + 1).padStart(2, "0") + "/" + today.getFullYear();
    let id = nextId;
    const added: Doc[] = files.map((f) => {
      const mb = f.size / (1024 * 1024);
      const size = mb >= 1 ? mb.toFixed(1).replace(".", ",") + " MB" : Math.round(f.size / 1024) + " KB";
      return { id: id++, name: f.name, meta: size + " · thêm " + dd, status: "processing" as Status };
    });
    setDocs((prev) => [...added, ...prev]);
    setNextId(id);
    e.target.value = "";
    setTimeout(() => setDocs((prev) => prev.map((d) => (d.status === "processing" ? { ...d, status: "ready" } : d))), 2200);
  }

  function deleteDoc(id: number) {
    setDocs((prev) => prev.filter((d) => d.id !== id));
  }

  const stats = [
    { label: "Phụ huynh hoạt động", value: "2.847", delta: "+12%", icon: "users", tint: "var(--teal-50)", fg: "var(--brand)" },
    { label: "Lượt trò chuyện", value: "9.130", delta: "+8%", icon: "chat", tint: "var(--sky-50)", fg: "var(--sky-600)" },
    { label: "Câu hỏi đã giải đáp", value: "24.6K", delta: "+18%", icon: "q", tint: "var(--sun-50)", fg: "var(--sun-600)" },
    { label: "Tài liệu kiến thức", value: String(docs.length), delta: "cập nhật", icon: "doc", tint: "var(--brand-subtle)", fg: "var(--brand-strong)" },
  ];

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", fontFamily: "var(--font-body)", color: "var(--text-body)", background: "var(--ink-100)" }}>
      {/* ===== TOP HEADER ===== */}
      <header style={{ flex: "0 0 auto", display: "flex", alignItems: "center", gap: 12, padding: "13px 22px", background: "var(--surface-card)", borderBottom: "1px solid var(--border-subtle)", zIndex: 5 }}>
        <span style={{ flex: "0 0 auto", background: "var(--brand)", borderRadius: 13, padding: 6, display: "inline-flex", boxShadow: "var(--shadow-brand)" }}>
          <LuminaLogo size={28} tone="white" />
        </span>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 17, color: "var(--text-strong)", lineHeight: 1 }}>LuminaAi <span style={{ color: "var(--text-subtle)", fontWeight: 600 }}>· Quản trị</span></div>
          <div style={{ marginTop: 4, fontSize: 13, color: "var(--text-muted)" }}>Bảng điều khiển hệ thống tư vấn tuyển sinh</div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 11 }}>
          <span style={{ flex: "0 0 auto", width: 38, height: 38, borderRadius: "50%", background: "var(--brand)", color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 14 }}>QT</span>
          <span style={{ display: "flex", flexDirection: "column", lineHeight: 1.25 }}>
            <span style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 14, color: "var(--text-strong)" }}>Quản trị viên</span>
            <span style={{ fontSize: 12, color: "var(--text-subtle)" }}>admin@luminaai.vn</span>
          </span>
          <Link href="/auth" aria-label="Đăng xuất" title="Đăng xuất" className="ad-logout" style={{ flex: "0 0 auto", marginLeft: 6, width: 40, height: 40, borderRadius: 10, border: "1px solid var(--border-default)", background: "var(--surface-card)", color: "var(--text-muted)", display: "inline-flex", alignItems: "center", justifyContent: "center", textDecoration: "none", transition: "background .15s, color .15s, border-color .15s" }}>
            <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="M16 17l5-5-5-5M21 12H9" /></svg>
          </Link>
        </div>
      </header>

      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        {/* ===== SIDEBAR ===== */}
        <aside className="ad-side" style={{ flex: "0 0 252px", minWidth: 0, overflow: "hidden", display: "flex", flexDirection: "column", background: "var(--surface-card)", borderRight: "1px solid var(--border-subtle)", padding: "16px 14px" }}>
          <div style={{ padding: "6px 12px 10px", fontSize: 12, fontWeight: 800, letterSpacing: ".06em", textTransform: "uppercase", color: "var(--text-subtle)" }}>Chức năng</div>
          <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <button className="ad-nav" onClick={() => setTab("stats")} style={isStats ? navActive : navIdle}>
              <span style={{ flex: "0 0 auto", display: "inline-flex" }}><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18" /><rect x="7" y="11" width="3" height="6" rx="1" /><rect x="12" y="7" width="3" height="10" rx="1" /><rect x="17" y="13" width="3" height="4" rx="1" /></svg></span>
              Thống kê
            </button>
            <button className="ad-nav" onClick={() => setTab("docs")} style={isStats ? navIdle : navActive}>
              <span style={{ flex: "0 0 auto", display: "inline-flex" }}><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" /><path d="M9 7h7M9 11h5" /></svg></span>
              Cơ sở kiến thức
            </button>
          </nav>
          <div style={{ marginTop: "auto", padding: 14, borderRadius: "var(--radius-lg)", background: "var(--brand-subtle)", border: "1px solid var(--border-brand)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 14, color: "var(--brand-strong)" }}>
              <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" /></svg>
              Trạng thái
            </div>
            <p style={{ margin: "8px 0 0", fontSize: 13, color: "var(--brand-strong)", lineHeight: 1.5 }}>Cơ sở kiến thức đang hoạt động. Bot trả lời dựa trên {docs.length} tài liệu.</p>
          </div>
        </aside>

        {/* ===== CONTENT ===== */}
        <main className="ad-scroll" style={{ flex: 1, minWidth: 0, overflowY: "auto", overflowX: "hidden", padding: "30px clamp(20px,4vw,44px) 44px" }}>
          {isStats ? (
            <div className="ad-view">
              <div style={{ marginBottom: 24 }}>
                <h1 style={{ fontSize: 28, margin: "0 0 5px", color: "var(--text-strong)" }}>Thống kê tổng quan</h1>
                <p style={{ margin: 0, fontSize: 15, color: "var(--text-muted)" }}>Số liệu hoạt động của trợ lý LuminaAi trong 30 ngày qua.</p>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 22 }}>
                {stats.map((s) => (
                  <div key={s.label} className="gw-card gw-card--pad">
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <span style={{ width: 42, height: 42, borderRadius: 12, background: s.tint, color: s.fg, display: "inline-flex", alignItems: "center", justifyContent: "center" }}><StatIcon name={s.icon} /></span>
                      <span style={{ fontFamily: "var(--font-body)", fontWeight: 700, fontSize: 12.5, color: "var(--success-600)", background: "var(--success-50)", borderRadius: "var(--radius-pill)", padding: "3px 9px" }}>{s.delta}</span>
                    </div>
                    <div style={{ fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 32, color: "var(--text-strong)", lineHeight: 1, marginTop: 16 }}>{s.value}</div>
                    <div style={{ marginTop: 6, fontSize: 14, color: "var(--text-muted)" }}>{s.label}</div>
                  </div>
                ))}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1.55fr 1fr", gap: 16 }}>
                {/* bar chart */}
                <div className="gw-card gw-card--pad">
                  <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 4 }}>
                    <h2 style={{ fontSize: 17, margin: 0, color: "var(--text-strong)" }}>Lượt trò chuyện theo tuần</h2>
                    <span style={{ fontSize: 13, color: "var(--text-subtle)" }}>6 tuần gần nhất</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "flex-end", gap: 14, height: 210, paddingTop: 22 }}>
                    {CHART.map((b) => (
                      <div key={b.label} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 9, height: "100%", justifyContent: "flex-end" }}>
                        <span style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 13, color: "var(--text-muted)" }}>{b.value}</span>
                        <div className="ad-bar" style={{ width: "100%", maxWidth: 46, height: b.h, background: "linear-gradient(180deg, var(--teal-400), var(--brand))", borderRadius: "10px 10px 4px 4px" }} />
                        <span style={{ fontSize: 12.5, color: "var(--text-subtle)" }}>{b.label}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* top topics */}
                <div className="gw-card gw-card--pad">
                  <h2 style={{ fontSize: 17, margin: "0 0 16px", color: "var(--text-strong)" }}>Chủ đề được hỏi nhiều</h2>
                  <div style={{ display: "flex", flexDirection: "column", gap: 15 }}>
                    {TOPICS.map((t) => (
                      <div key={t.label}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14, marginBottom: 6 }}>
                          <span style={{ color: "var(--text-body)", fontWeight: 600 }}>{t.label}</span>
                          <span style={{ color: "var(--text-subtle)" }}>{t.pct}</span>
                        </div>
                        <div style={{ height: 9, borderRadius: "var(--radius-pill)", background: "var(--ink-100)", overflow: "hidden" }}>
                          <div style={{ height: "100%", width: t.pct, background: t.color, borderRadius: "var(--radius-pill)" }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="ad-view">
              <div style={{ marginBottom: 24 }}>
                <h1 style={{ fontSize: 28, margin: "0 0 5px", color: "var(--text-strong)" }}>Cơ sở kiến thức</h1>
                <p style={{ margin: 0, fontSize: 15, color: "var(--text-muted)" }}>Thêm tài liệu PDF để LuminaAi học và trả lời ba mẹ chính xác hơn.</p>
              </div>

              {/* dropzone */}
              <label className="ad-drop" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, padding: "40px 24px", background: "var(--surface-card)", border: "2px dashed var(--border-strong)", borderRadius: "var(--radius-xl)", cursor: "pointer", transition: "border-color .15s, background .15s", textAlign: "center" }}>
                <input type="file" accept="application/pdf" multiple onChange={onPick} style={{ display: "none" }} />
                <span style={{ width: 56, height: 56, borderRadius: 16, background: "var(--brand-subtle)", color: "var(--brand)", display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
                  <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="M12 3v13M7 8l5-5 5 5" /></svg>
                </span>
                <div>
                  <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 16, color: "var(--text-strong)" }}>Kéo thả PDF vào đây hoặc <span style={{ color: "var(--brand-strong)" }}>chọn tệp</span></div>
                  <div style={{ marginTop: 5, fontSize: 13.5, color: "var(--text-muted)" }}>Hỗ trợ tệp .pdf · tối đa 25 MB mỗi tệp</div>
                </div>
              </label>

              <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", margin: "28px 0 14px" }}>
                <h2 style={{ fontSize: 18, margin: 0, color: "var(--text-strong)" }}>Tài liệu đã thêm <span style={{ color: "var(--text-subtle)", fontWeight: 600 }}>({docs.length})</span></h2>
              </div>

              <div className="gw-card" style={{ padding: 0, overflow: "hidden" }}>
                {docs.map((d) => (
                  <div key={d.id} className="ad-row" style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 18px", borderBottom: "1px solid var(--border-subtle)", transition: "background .12s" }}>
                    <span style={{ flex: "0 0 auto", width: 42, height: 42, borderRadius: 11, background: "var(--danger-50)", color: "var(--danger-600)", display: "inline-flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 11 }}>PDF</span>
                    <span style={{ flex: 1, minWidth: 0 }}>
                      <span style={{ display: "block", fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 15, color: "var(--text-strong)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{d.name}</span>
                      <span style={{ display: "block", fontSize: 13, color: "var(--text-subtle)", marginTop: 2 }}>{d.meta}</span>
                    </span>
                    <span style={{ flex: "0 0 auto" }}>
                      {d.status === "ready"
                        ? <span className="gw-badge gw-badge--success gw-badge--dot">Đã sẵn sàng</span>
                        : <span className="gw-badge gw-badge--warning gw-badge--dot">Đang xử lý</span>}
                    </span>
                    <button className="ad-del" aria-label="Xoá" onClick={() => deleteDoc(d.id)} style={{ flex: "0 0 auto", width: 38, height: 38, borderRadius: 10, border: "none", background: "transparent", color: "var(--text-subtle)", display: "inline-flex", alignItems: "center", justifyContent: "center", cursor: "pointer", transition: "background .12s, color .12s" }}>
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" /></svg>
                    </button>
                  </div>
                ))}
                {docs.length === 0 && (
                  <div style={{ padding: 40, textAlign: "center", color: "var(--text-subtle)", fontSize: 15 }}>Chưa có tài liệu nào. Thêm PDF đầu tiên ở trên nhé!</div>
                )}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
