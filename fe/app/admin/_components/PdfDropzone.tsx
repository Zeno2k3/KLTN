"use client";

import Icon from "@/app/components/ui/Icon";
import IconBox from "@/app/components/ui/IconBox";

/** Vùng kéo-thả / chọn tệp PDF. */
export default function PdfDropzone({ onPick }: { onPick: (e: React.ChangeEvent<HTMLInputElement>) => void }) {
  return (
    <label className="ad-drop" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, padding: "40px 24px", background: "var(--surface-card)", border: "2px dashed var(--border-strong)", borderRadius: "var(--radius-xl)", cursor: "pointer", transition: "border-color .15s, background .15s", textAlign: "center" }}>
      <input type="file" accept="application/pdf" multiple onChange={onPick} style={{ display: "none" }} />
      <IconBox size={56} radius={16} bg="var(--brand-subtle)" color="var(--brand)">
        <Icon name="upload" size={28} />
      </IconBox>
      <div>
        <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 16, color: "var(--text-strong)" }}>Kéo thả PDF vào đây hoặc <span style={{ color: "var(--brand-strong)" }}>chọn tệp</span></div>
        <div style={{ marginTop: 5, fontSize: 13.5, color: "var(--text-muted)" }}>Hỗ trợ tệp .pdf · tối đa 25 MB mỗi tệp</div>
      </div>
    </label>
  );
}
