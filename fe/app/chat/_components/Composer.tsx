"use client";

import Icon from "@/app/components/ui/Icon";

interface ComposerProps {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
}

/** Khung soạn tin nhắn: nút đính kèm, ô nhập, nút gửi. */
export default function Composer({ value, onChange, onSend }: ComposerProps) {
  return (
    <div style={{ padding: "14px clamp(18px,6vw,90px) 16px", background: "var(--surface-card)", borderTop: "1px solid var(--border-subtle)" }}>
      <div className="ch-composer" style={{ display: "flex", alignItems: "flex-end", gap: 8, background: "var(--surface-card)", border: "1.5px solid var(--border-default)", borderRadius: "var(--radius-xl)", padding: 7, transition: "border-color .15s, box-shadow .15s" }}>
        <button aria-label="Đính kèm" className="ch-attach" style={{ flex: "0 0 auto", width: 40, height: 40, borderRadius: "50%", border: "none", background: "transparent", color: "var(--text-muted)", display: "inline-flex", alignItems: "center", justifyContent: "center", cursor: "pointer", transition: "background .15s" }}>
          <Icon name="paperclip" size={20} />
        </button>
        <textarea
          className="ch-input"
          rows={1}
          placeholder="Nhập câu hỏi cho LuminaAi…"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          style={{ flex: 1, border: 0, resize: "none", background: "transparent", fontFamily: "var(--font-body)", fontSize: 15, lineHeight: 1.5, color: "var(--text-strong)", padding: "9px 6px", maxHeight: 120 }}
        />
        <button onClick={onSend} className="ch-send" aria-label="Gửi" style={{ flex: "0 0 auto", width: 44, height: 44, borderRadius: "50%", border: "none", background: "var(--brand)", color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center", cursor: "pointer", boxShadow: "var(--shadow-brand)", transition: "background .15s" }}>
          <Icon name="send" size={20} />
        </button>
      </div>
      <div style={{ textAlign: "center", fontSize: 11.5, color: "var(--text-subtle)", marginTop: 9 }}>LuminaAi có thể nhầm lẫn. Ba mẹ vui lòng xác nhận thông tin với nhà trường.</div>
    </div>
  );
}
