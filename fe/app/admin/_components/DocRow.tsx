"use client";

import type { Doc } from "@/app/types/admin";
import Avatar from "@/app/components/ui/Avatar";
import Badge from "@/app/components/ui/Badge";
import Icon from "@/app/components/ui/Icon";

/** Một dòng tài liệu (badge PDF + tên + trạng thái + nút xoá). */
export default function DocRow({ doc, onDelete }: { doc: Doc; onDelete: (id: number) => void }) {
  return (
    <div className="ad-row" style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 18px", borderBottom: "1px solid var(--border-subtle)", transition: "background .12s" }}>
      <Avatar initials="PDF" bg="var(--danger-50)" color="var(--danger-600)" size={42} shape="rounded" radius={11} fontSize={11} />
      <span style={{ flex: 1, minWidth: 0 }}>
        <span style={{ display: "block", fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 15, color: "var(--text-strong)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{doc.name}</span>
        <span style={{ display: "block", fontSize: 13, color: "var(--text-subtle)", marginTop: 2 }}>{doc.meta}</span>
      </span>
      <span style={{ flex: "0 0 auto" }}>
        {doc.status === "ready" ? (
          <Badge tone="success" dot>Đã sẵn sàng</Badge>
        ) : (
          <Badge tone="warning" dot>Đang xử lý</Badge>
        )}
      </span>
      <button className="ad-del" aria-label="Xoá" onClick={() => onDelete(doc.id)} style={{ flex: "0 0 auto", width: 38, height: 38, borderRadius: 10, border: "none", background: "transparent", color: "var(--text-subtle)", display: "inline-flex", alignItems: "center", justifyContent: "center", cursor: "pointer", transition: "background .12s, color .12s" }}>
        <Icon name="trash" size={18} />
      </button>
    </div>
  );
}
