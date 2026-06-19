"use client";

import type { Doc } from "@/app/types/admin";
import DocRow from "./DocRow";
import PdfDropzone from "./PdfDropzone";

interface DocsViewProps {
  docs: Doc[];
  onPick: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDelete: (id: number) => void;
}

/** Tab "Cơ sở kiến thức": vùng tải PDF + danh sách tài liệu. */
export default function DocsView({ docs, onPick, onDelete }: DocsViewProps) {
  return (
    <div className="ad-view">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, margin: "0 0 5px", color: "var(--text-strong)" }}>Cơ sở kiến thức</h1>
        <p style={{ margin: 0, fontSize: 15, color: "var(--text-muted)" }}>Thêm tài liệu PDF để LuminaAi học và trả lời ba mẹ chính xác hơn.</p>
      </div>

      <PdfDropzone onPick={onPick} />

      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", margin: "28px 0 14px" }}>
        <h2 style={{ fontSize: 18, margin: 0, color: "var(--text-strong)" }}>Tài liệu đã thêm <span style={{ color: "var(--text-subtle)", fontWeight: 600 }}>({docs.length})</span></h2>
      </div>

      <div className="gw-card" style={{ padding: 0, overflow: "hidden" }}>
        {docs.map((d) => (
          <DocRow key={d.id} doc={d} onDelete={onDelete} />
        ))}
        {docs.length === 0 && (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text-subtle)", fontSize: 15 }}>Chưa có tài liệu nào. Thêm PDF đầu tiên ở trên nhé!</div>
        )}
      </div>
    </div>
  );
}
