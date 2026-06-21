"use client";

import type { CSSProperties } from "react";
import Icon from "@/app/components/ui/Icon";

interface CitationChipProps {
  /** Tên tài liệu hiển thị trên chip. */
  label: string;
  /** Tooltip (thường là đoạn trích) — hữu ích khi chip không bấm được. */
  title?: string;
  /** Bấm chip → mở bảng tài liệu. Bỏ trống + `disabled` nếu nguồn không có tài liệu. */
  onClick?: () => void;
  /** Không gắn được tài liệu (document_id null) → chip tĩnh, không bấm. */
  disabled?: boolean;
}

const base: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 5,
  fontSize: 12,
  fontFamily: "var(--font-body)",
  fontWeight: 700,
  color: "var(--brand-strong)",
  background: "var(--brand-subtle)",
  border: "1px solid var(--teal-200)",
  borderRadius: "var(--radius-pill)",
  padding: "3px 10px",
  maxWidth: 240,
};

const labelStyle: CSSProperties = {
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis",
  minWidth: 0,
};

/** Chip nguồn dạng pill (icon tài liệu + tên), bấm để mở bảng trích dẫn. Tái sử dụng được. */
export default function CitationChip({ label, title, onClick, disabled }: CitationChipProps) {
  const icon = <Icon name="file" size={12} style={{ flex: "0 0 auto" }} />;

  if (disabled) {
    return (
      <span title={title} style={{ ...base, color: "var(--text-muted)", cursor: "default" }}>
        {icon}
        <span style={labelStyle}>{label}</span>
      </span>
    );
  }

  return (
    <button
      type="button"
      className="ch-cite-chip"
      title={title}
      onClick={onClick}
      style={{ ...base, cursor: "pointer" }}
    >
      {icon}
      <span style={labelStyle}>{label}</span>
    </button>
  );
}
