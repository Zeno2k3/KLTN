"use client";

import type { Doc } from "@/app/types/admin";
import Icon from "@/app/components/ui/Icon";
import DocRow from "./DocRow";
import PdfDropzone from "./PdfDropzone";

interface DocsViewProps {
  docs: Doc[];
  onPick: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDelete: (id: number) => void;
  onDeleteAll: () => void;
  onOpen: (doc: Doc, download: boolean) => void;
  onRename: (id: number, name: string) => void;
  loading?: boolean;
  error?: string | null;
}

/** Tab "Cơ sở kiến thức": vùng tải PDF + danh sách tài liệu. */
export default function DocsView({ docs, onPick, onDelete, onDeleteAll, onOpen, onRename, loading, error }: DocsViewProps) {
  function handleDeleteAll() {
    if (window.confirm(`Xoá tất cả ${docs.length} tài liệu? Hành động này không thể hoàn tác.`)) {
      onDeleteAll();
    }
  }

  return (
    <div className="ad-view">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, margin: "0 0 5px", color: "var(--text-strong)" }}>Cơ sở kiến thức</h1>
        <p style={{ margin: 0, fontSize: 15, color: "var(--text-muted)" }}>Thêm tài liệu PDF để LuminaAi học và trả lời ba mẹ chính xác hơn.</p>
      </div>

      <PdfDropzone onPick={onPick} />

      {error && (
        <div role="alert" style={{ marginTop: 16, padding: "12px 16px", borderRadius: "var(--radius-lg)", background: "var(--danger-50)", color: "var(--danger-600)", fontSize: 14 }}>{error}</div>
      )}

      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", margin: "28px 0 14px" }}>
        <h2 style={{ fontSize: 18, margin: 0, color: "var(--text-strong)" }}>Tài liệu đã thêm <span style={{ color: "var(--text-subtle)", fontWeight: 600 }}>({docs.length})</span></h2>
        {docs.length > 0 && (
          <button onClick={handleDeleteAll} style={{ display: "inline-flex", alignItems: "center", gap: 7, padding: "8px 14px", borderRadius: 10, border: "1px solid var(--danger-200, var(--border-strong))", background: "transparent", color: "var(--danger-600)", fontSize: 14, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>
            <Icon name="trash" size={16} />
            Xoá tất cả
          </button>
        )}
      </div>

      <div className="gw-card" style={{ padding: 0, overflow: "hidden" }}>
        {docs.map((d) => (
          <DocRow key={d.id} doc={d} onDelete={onDelete} onOpen={onOpen} onRename={onRename} />
        ))}
        {docs.length === 0 && (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text-subtle)", fontSize: 15 }}>
            {loading ? "Đang tải danh sách tài liệu…" : "Chưa có tài liệu nào. Thêm PDF đầu tiên ở trên nhé!"}
          </div>
        )}
      </div>
    </div>
  );
}
