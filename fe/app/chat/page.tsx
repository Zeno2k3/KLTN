"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import LuminaLogo from "../_components/LuminaLogo";

type Msg = { from: "bot" | "user"; text: string; time: string };
type Convo = { id: string; title: string; time: string; tint: string; fg: string; messages: Msg[] };

const SCRIPTED: Record<string, string> = {
  "Điều kiện nhập học": "Để vào lớp 1, bé cần đủ 6 tuổi tính theo năm (sinh năm 2020 cho năm học 2026–2027) ạ. Ba mẹ chỉ cần giấy khai sinh và sổ hộ khẩu/giấy tạm trú là đủ điều kiện nộp hồ sơ rồi nhé! 🎒",
  "Hồ sơ cần chuẩn bị": "Hồ sơ tuyển sinh lớp 1 gồm: (1) Đơn đăng ký, (2) Bản sao giấy khai sinh, (3) Sổ hộ khẩu hoặc giấy tạm trú. Một số trường cần thêm 2 ảnh 3×4. Ba mẹ muốn mình gửi mẫu đơn không ạ?",
  "Học phí 2026": "Học phí khối tiểu học dao động khá rộng tuỳ trường: trường công thường rất thấp, trường tư từ 3–15 triệu/tháng. Ba mẹ cho mình biết khu vực và ngân sách mong muốn, mình gợi ý trường phù hợp nhé.",
  "Đặt lịch tham quan": "Tuyệt vời! Nhiều trường mở cửa tham quan vào Thứ 7 hàng tuần. Ba mẹ muốn tham quan ở khu vực nào và khoảng thời gian nào ạ? Mình sẽ giúp đặt lịch và nhắc qua Zalo.",
};
const DEFAULT_REPLY = "Cảm ơn ba mẹ đã chia sẻ! Mình đã ghi nhận. Ba mẹ có thể chọn một trong các chủ đề bên dưới, hoặc nhắn câu hỏi cụ thể để mình tư vấn kỹ hơn nhé. 💬";
const TOPICS = ["Điều kiện nhập học", "Hồ sơ cần chuẩn bị", "Học phí 2026", "Đặt lịch tham quan"];
const USER_NAME = "chị Hồng Nhung";

const SEED: Convo[] = [
  { id: "c1", title: "Tuyển sinh lớp 1 Q.7", time: "09:24", tint: "var(--brand-subtle)", fg: "var(--brand-strong)", messages: [
    { from: "bot", text: "Chào ba mẹ! Mình là LuminaAi 👋 Mình hỗ trợ tư vấn tuyển sinh lớp 1. Mình giúp gì cho bé nhà mình ạ?", time: "09:20" },
    { from: "user", text: "Bé nhà mình sinh năm 2020 ạ", time: "09:21" },
    { from: "bot", text: "Dạ bé sinh 2020 năm nay vừa đủ 6 tuổi, đúng độ tuổi vào lớp 1 ạ! Ba mẹ muốn tìm trường gần khu vực nào để mình gợi ý nhé? 🎒", time: "09:21" },
    { from: "user", text: "Khu vực Quận 7 ạ", time: "09:23" },
    { from: "bot", text: "Quận 7 có nhiều trường tốt như TH Nguyễn Thị Định, Vinschool Central Park, Quốc tế Á Châu… Ba mẹ cho mình biết ngân sách học phí mong muốn, mình lọc giúp ạ.", time: "09:24" },
  ] },
  { id: "c2", title: "Hồ sơ nhập học", time: "Hôm qua", tint: "var(--sun-50)", fg: "var(--sun-600)", messages: [
    { from: "user", text: "Hồ sơ cần chuẩn bị gồm những gì ạ?", time: "20:10" },
    { from: "bot", text: "Hồ sơ tuyển sinh lớp 1 gồm: (1) Đơn đăng ký, (2) Bản sao giấy khai sinh, (3) Sổ hộ khẩu hoặc giấy tạm trú. Một số trường cần thêm 2 ảnh 3×4 ạ.", time: "20:10" },
    { from: "user", text: "Cho mình xin mẫu đơn với ạ", time: "20:12" },
    { from: "bot", text: "Dạ mình gửi ba mẹ mẫu Đơn đăng ký tuyển sinh lớp 1 qua Zalo nhé. Ba mẹ chỉ cần điền thông tin bé và ký tên là xong ạ. ✅", time: "20:12" },
  ] },
  { id: "c3", title: "Học phí trường tư", time: "T4", tint: "var(--sky-50)", fg: "var(--sky-600)", messages: [
    { from: "user", text: "Học phí trường tư khoảng bao nhiêu ạ?", time: "15:30" },
    { from: "bot", text: "Học phí khối tiểu học trường tư dao động khá rộng, thường từ 3–15 triệu/tháng tuỳ trường và chương trình. Ba mẹ cho mình biết ngân sách mong muốn, mình gợi ý trường phù hợp nhé.", time: "15:30" },
  ] },
  { id: "c4", title: "Lịch tham quan Wellspring", time: "T2", tint: "var(--ink-100)", fg: "var(--text-muted)", messages: [
    { from: "user", text: "Mình muốn đặt lịch tham quan trường", time: "10:02" },
    { from: "bot", text: "Tuyệt vời! Nhiều trường mở cửa tham quan vào Thứ 7 hàng tuần. Ba mẹ muốn tham quan trường nào và khoảng thời gian nào ạ?", time: "10:02" },
    { from: "user", text: "Wellspring Saigon, sáng Thứ 7 này", time: "10:05" },
    { from: "bot", text: "Dạ mình đã đặt lịch tham quan Wellspring Saigon lúc 9h sáng Thứ 7 này cho ba mẹ. Mình sẽ nhắc lại qua Zalo trước 1 ngày nhé! 📅", time: "10:05" },
  ] },
  { id: "c5", title: "Tuyển sinh trái tuyến", time: "12/6", tint: "var(--ink-100)", fg: "var(--text-muted)", messages: [
    { from: "user", text: "Bé học trái tuyến có được không ạ?", time: "09:00" },
    { from: "bot", text: "Dạ được ạ. Tuyển sinh trái tuyến phụ thuộc chỉ tiêu còn lại của trường sau khi nhận đúng tuyến. Ba mẹ nên nộp đơn sớm và chuẩn bị giấy tạm trú nếu có. Mình hướng dẫn chi tiết từng bước nhé.", time: "09:01" },
  ] },
];

const now = () => {
  const d = new Date();
  return String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
};

const bubbleBase: CSSProperties = {
  fontFamily: "var(--font-body)", fontSize: 15, lineHeight: 1.55, padding: "11px 15px",
  borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-xs)", wordWrap: "break-word", textWrap: "pretty", maxWidth: 560,
};

function BotAvatar() {
  return (
    <span style={{ flex: "0 0 auto", width: 36, height: 36, borderRadius: 11, background: "var(--brand)", display: "inline-flex", alignItems: "center", justifyContent: "center", boxShadow: "var(--shadow-brand)" }}>
      <LuminaLogo size={22} tone="white" />
    </span>
  );
}

export default function ChatPage() {
  const [convos, setConvos] = useState<Convo[]>(SEED);
  const [activeId, setActiveId] = useState("c1");
  const [text, setText] = useState("");
  const [typing, setTyping] = useState(false);
  const [newCount, setNewCount] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  const active = convos.find((c) => c.id === activeId) ?? convos[0];
  const msgs = active ? active.messages : [];
  const isEmpty = msgs.length === 0;

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [msgs.length, typing, activeId]);

  function botRespond(targetId: string, userText: string) {
    setTyping(true);
    setTimeout(() => {
      const reply = SCRIPTED[userText] || DEFAULT_REPLY;
      setTyping(false);
      setConvos((prev) => prev.map((c) => (c.id === targetId ? { ...c, messages: [...c.messages, { from: "bot", text: reply, time: now() }] } : c)));
    }, 1100);
  }

  function send(value?: string) {
    const v = (value ?? text).trim();
    if (!v) return;
    const id = activeId;
    setConvos((prev) => prev.map((c) => {
      if (c.id !== id) return c;
      const first = c.messages.length === 0;
      return { ...c, title: first ? (v.length > 26 ? v.slice(0, 26) + "…" : v) : c.title, time: now(), messages: [...c.messages, { from: "user", text: v, time: now() }] };
    }));
    setText("");
    botRespond(id, v);
  }

  function openConvo(id: string) {
    setActiveId(id);
    setText("");
    setTyping(false);
  }

  function newChat() {
    const id = "n" + (newCount + 1);
    const convo: Convo = { id, title: "Cuộc trò chuyện mới", time: "Bây giờ", tint: "var(--ink-100)", fg: "var(--text-muted)", messages: [] };
    setNewCount((n) => n + 1);
    setConvos((prev) => [convo, ...prev]);
    setActiveId(id);
    setText("");
    setTyping(false);
  }

  const hour = new Date().getHours();
  const part = hour < 11 ? "sáng" : hour < 18 ? "chiều" : "tối";
  const greetingText = `Xin chào buổi ${part}, ${USER_NAME} 👋`;
  const greetingSub = "Mình là LuminaAi — trợ lý tư vấn tuyển sinh lớp 1. Mình giúp gì cho bé nhà mình hôm nay ạ?";

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", fontFamily: "var(--font-body)", color: "var(--text-body)", background: "var(--ink-100)" }}>
      {/* ===== TOP HEADER ===== */}
      <header style={{ flex: "0 0 auto", display: "flex", alignItems: "center", gap: 12, padding: "13px 22px", background: "var(--surface-card)", borderBottom: "1px solid var(--border-subtle)", zIndex: 5 }}>
        <span style={{ flex: "0 0 auto", background: "var(--brand)", borderRadius: 13, padding: 6, display: "inline-flex", boxShadow: "var(--shadow-brand)" }}>
          <LuminaLogo size={28} tone="white" />
        </span>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 17, color: "var(--text-strong)", lineHeight: 1 }}>LuminaAi</div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4, fontSize: 13, color: "var(--text-muted)" }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--success-500)" }} />
            Trợ lý tuyển sinh · trực tuyến
          </div>
        </div>
      </header>

      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        {/* ===== SIDEBAR ===== */}
        <aside className="ch-side" style={{ flex: "0 0 290px", minWidth: 0, overflow: "hidden", display: "flex", flexDirection: "column", background: "var(--surface-card)", borderRight: "1px solid var(--border-subtle)" }}>
          <div style={{ padding: "14px 14px 8px" }}>
            <button onClick={newChat} className="ch-newchat" style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 8, height: 44, borderRadius: "var(--radius-pill)", background: "var(--brand)", color: "#fff", border: "none", cursor: "pointer", fontFamily: "var(--font-body)", fontWeight: 700, fontSize: 15, boxShadow: "var(--shadow-brand)", transition: "background .15s" }}>
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5v14M5 12h14" /></svg>
              Cuộc trò chuyện mới
            </button>
          </div>

          <div style={{ padding: "12px 14px 6px", fontSize: 12, fontWeight: 800, letterSpacing: ".06em", textTransform: "uppercase", color: "var(--text-subtle)" }}>Gần đây</div>
          <div className="ch-scroll" style={{ flex: 1, overflowY: "auto", overflowX: "hidden", padding: "0 10px 14px", display: "flex", flexDirection: "column", gap: 3 }}>
            {convos.map((c) => {
              const last = c.messages[c.messages.length - 1];
              const snippet = last ? (last.from === "user" ? "Ba mẹ: " : "") + last.text : "Bắt đầu trò chuyện…";
              const isActive = c.id === activeId;
              return (
                <div key={c.id} className="ch-convo" onClick={() => openConvo(c.id)} style={{ display: "flex", gap: 11, alignItems: "flex-start", padding: "10px 11px", borderRadius: 14, cursor: "pointer", transition: "background .15s", background: isActive ? "var(--brand-subtle)" : undefined }}>
                  <span style={{ flex: "0 0 auto", width: 36, height: 36, borderRadius: 11, background: c.tint, color: c.fg, display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                  </span>
                  <span style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ flex: 1, fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 14, color: "var(--text-strong)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{c.title}</span>
                      <span style={{ flex: "0 0 auto", fontSize: 11, color: "var(--text-subtle)" }}>{c.time}</span>
                    </span>
                    <span style={{ display: "block", fontSize: 12.5, color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", marginTop: 2 }}>{snippet}</span>
                  </span>
                </div>
              );
            })}
          </div>

          <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: 11 }}>
            <span style={{ flex: "0 0 auto", width: 38, height: 38, borderRadius: "50%", background: "var(--sky-400)", color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 14 }}>HN</span>
            <span style={{ flex: 1, minWidth: 0 }}>
              <span style={{ display: "block", fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 14, color: "var(--text-strong)" }}>Chị Hồng Nhung</span>
              <span style={{ display: "block", fontSize: 12, color: "var(--text-subtle)" }}>Phụ huynh bé Bốp</span>
            </span>
            <span style={{ flex: "0 0 auto", color: "var(--text-subtle)" }}>
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 8 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H2a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 3.6 8a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H8a1.65 1.65 0 0 0 1-1.51V2a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V8a1.65 1.65 0 0 0 1.51 1H22a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>
            </span>
          </div>
        </aside>

        {/* ===== CHAT ===== */}
        <main style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          <div ref={scrollRef} className="ch-scroll" style={{ flex: 1, overflowY: "auto", overflowX: "hidden", padding: "24px clamp(18px,6vw,90px)", display: "flex", flexDirection: "column", gap: 14, background: "var(--ink-100)" }}>
            {!isEmpty && (
              <div style={{ alignSelf: "center", fontSize: 12, color: "var(--text-subtle)", background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-pill)", padding: "5px 14px", marginBottom: 2 }}>Hôm nay</div>
            )}

            {isEmpty && (
              <div style={{ margin: "auto", maxWidth: 560, padding: "24px 0", display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
                <span style={{ background: "var(--brand)", borderRadius: 24, padding: 15, display: "inline-flex", boxShadow: "var(--shadow-brand)", animation: "ch-bob 4.5s ease-in-out infinite" }}>
                  <LuminaLogo size={58} tone="white" />
                </span>
                <h2 style={{ fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 30, color: "var(--text-strong)", margin: "22px 0 8px" }}>{greetingText}</h2>
                <p style={{ fontSize: 16, color: "var(--text-muted)", lineHeight: 1.55, margin: "0 0 26px", maxWidth: 430 }}>{greetingSub}</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10, justifyContent: "center" }}>
                  {TOPICS.map((t) => (
                    <button key={t} className="ch-chip" onClick={() => send(t)} style={{ fontFamily: "var(--font-body)", fontWeight: 600, fontSize: 14, color: "var(--brand-strong)", background: "var(--surface-card)", border: "1.5px solid var(--border-brand)", borderRadius: "var(--radius-pill)", padding: "9px 15px", cursor: "pointer", transition: "transform .12s, background .15s" }}>{t}</button>
                  ))}
                </div>
              </div>
            )}

            {msgs.map((m, i) => {
              const isBot = m.from === "bot";
              const showAvatar = i === 0 || msgs[i - 1].from !== m.from;
              return (
                <div key={i} className="ch-row" style={{ display: "flex", gap: 10, alignItems: "flex-end", alignSelf: isBot ? "flex-start" : "flex-end", flexDirection: isBot ? "row" : "row-reverse" }}>
                  {showAvatar && isBot && <BotAvatar />}
                  {showAvatar && !isBot && (
                    <span style={{ flex: "0 0 auto", width: 36, height: 36, borderRadius: "50%", background: "var(--sky-400)", color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 13 }}>BM</span>
                  )}
                  {!showAvatar && <span style={{ flex: "0 0 auto", width: 36 }} />}
                  <span style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
                    <span style={{ ...bubbleBase, ...(isBot
                      ? { background: "var(--surface-card)", color: "var(--text-body)", border: "1px solid var(--border-subtle)", borderBottomLeftRadius: 6 }
                      : { background: "var(--brand)", color: "#fff", borderBottomRightRadius: 6, boxShadow: "var(--shadow-brand)" }) }}>{m.text}</span>
                    <span style={{ fontSize: 12, color: "var(--text-subtle)", marginTop: 6, textAlign: isBot ? "left" : "right" }}>{m.time}</span>
                  </span>
                </div>
              );
            })}

            {typing && (
              <div style={{ display: "flex", gap: 10, alignItems: "flex-end", alignSelf: "flex-start", maxWidth: "78%" }}>
                <BotAvatar />
                <span style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "13px 16px", background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)", borderBottomLeftRadius: 6, boxShadow: "var(--shadow-xs)" }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--teal-400)", animation: "ch-typing 1.2s infinite" }} />
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--teal-400)", animation: "ch-typing 1.2s infinite .15s" }} />
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--teal-400)", animation: "ch-typing 1.2s infinite .3s" }} />
                </span>
              </div>
            )}
          </div>

          {/* composer */}
          <div style={{ padding: "14px clamp(18px,6vw,90px) 16px", background: "var(--surface-card)", borderTop: "1px solid var(--border-subtle)" }}>
            <div className="ch-composer" style={{ display: "flex", alignItems: "flex-end", gap: 8, background: "var(--surface-card)", border: "1.5px solid var(--border-default)", borderRadius: "var(--radius-xl)", padding: 7, transition: "border-color .15s, box-shadow .15s" }}>
              <button aria-label="Đính kèm" className="ch-attach" style={{ flex: "0 0 auto", width: 40, height: 40, borderRadius: "50%", border: "none", background: "transparent", color: "var(--text-muted)", display: "inline-flex", alignItems: "center", justifyContent: "center", cursor: "pointer", transition: "background .15s" }}>
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.4 11.05 12.25 20.2a5 5 0 0 1-7.07-7.07l9.19-9.19a3 3 0 0 1 4.24 4.24l-9.2 9.19a1 1 0 0 1-1.41-1.41l8.48-8.49" /></svg>
              </button>
              <textarea
                className="ch-input"
                rows={1}
                placeholder="Nhập câu hỏi cho LuminaAi…"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                style={{ flex: 1, border: 0, resize: "none", background: "transparent", fontFamily: "var(--font-body)", fontSize: 15, lineHeight: 1.5, color: "var(--text-strong)", padding: "9px 6px", maxHeight: 120 }}
              />
              <button onClick={() => send()} className="ch-send" aria-label="Gửi" style={{ flex: "0 0 auto", width: 44, height: 44, borderRadius: "50%", border: "none", background: "var(--brand)", color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center", cursor: "pointer", boxShadow: "var(--shadow-brand)", transition: "background .15s" }}>
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" /></svg>
              </button>
            </div>
            <div style={{ textAlign: "center", fontSize: 11.5, color: "var(--text-subtle)", marginTop: 9 }}>LuminaAi có thể nhầm lẫn. Ba mẹ vui lòng xác nhận thông tin với nhà trường.</div>
          </div>
        </main>
      </div>
    </div>
  );
}
