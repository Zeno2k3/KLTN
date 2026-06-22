"use client";

import { useEffect, useRef, useState } from "react";
import type { CSSProperties, KeyboardEvent } from "react";
import type { Doc } from "@/app/types/admin";
import Avatar from "@/app/components/ui/Avatar";
import Badge from "@/app/components/ui/Badge";
import Icon from "@/app/components/ui/Icon";

const actionBtn: CSSProperties = { flex: "0 0 auto", width: 38, height: 38, borderRadius: 10, border: "none", background: "transparent", color: "var(--text-subtle)", display: "inline-flex", alignItems: "center", justifyContent: "center", cursor: "pointer", transition: "background .12s, color .12s" };

interface DocRowProps {
  doc: Doc;
  onDelete: (id: number) => void;
  onOpen: (doc: Doc, download: boolean) => void;
  onRename: (id: number, name: string) => void;
}

/** Một dòng tài liệu (badge PDF + tên + trạng thái + nút đổi tên/xem/tải/xoá). */
export default function DocRow({ doc, onDelete, onOpen, onRename }: DocRowProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(doc.name);
  const inputRef = useRef<HTMLInputElement>(null);
  // Đảm bảo kết thúc sửa chỉ chạy 1 lần (tránh blur kích hoạt lại sau Enter/Esc).
  const editingRef = useRef(false);

  // Vào chế độ sửa → focus + chọn toàn bộ tên.
  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  function beginEdit() {
    setDraft(doc.name);
    editingRef.current = true;
    setEditing(true);
  }

  function endEdit(save: boolean) {
    if (!editingRef.current) return; // đã kết thúc rồi → bỏ qua (blur sau Enter/Esc)
    editingRef.current = false;
    setEditing(false);
    if (save) {
      const next = draft.trim();
      if (next && next !== doc.name) onRename(doc.id, next);
    }
  }

  function onInputKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      endEdit(true);
    } else if (e.key === "Escape") {
      e.preventDefault();
      endEdit(false);
    }
  }

  return (
    <div className="ad-row" style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 18px", borderBottom: "1px solid var(--border-subtle)", transition: "background .12s" }}>
      <Avatar initials="PDF" bg="var(--danger-50)" color="var(--danger-600)" size={42} shape="rounded" radius={11} fontSize={11} />
      <span style={{ flex: 1, minWidth: 0 }}>
        {editing ? (
          <input
            ref={inputRef}
            value={draft}
            maxLength={255}
            aria-label="Tên tài liệu"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onInputKeyDown}
            onBlur={() => endEdit(true)}
            style={{ display: "block", width: "100%", fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 15, color: "var(--text-strong)", border: "1px solid var(--brand)", borderRadius: 8, padding: "3px 8px", outline: "none", background: "var(--surface-card)" }}
          />
        ) : (
          <span style={{ display: "block", fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 15, color: "var(--text-strong)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{doc.name}</span>
        )}
        <span style={{ display: "block", fontSize: 13, color: "var(--text-subtle)", marginTop: 2 }}>{doc.meta}</span>
      </span>
      <span style={{ flex: "0 0 auto" }}>
        {doc.status === "ready" ? (
          <Badge tone="success" dot>Đã sẵn sàng</Badge>
        ) : doc.status === "failed" ? (
          <span title={doc.error ?? "Xử lý tài liệu thất bại"}>
            <Badge tone="danger" dot>Lỗi xử lý</Badge>
          </span>
        ) : (
          <Badge tone="warning" dot>Đang xử lý</Badge>
        )}
      </span>
      {/* Ẩn nút action khi đang sửa tên: tránh race blur-lưu khi bấm thẳng Xoá/Xem
          (mousedown làm input blur → lưu rename TRƯỚC onClick). Mirror ConversationItem. */}
      {!editing && (
        <>
          <button className="ad-act" aria-label="Đổi tên" title="Đổi tên" onClick={beginEdit} style={actionBtn}>
            <Icon name="edit" size={17} />
          </button>
          <button className="ad-act" aria-label="Xem" title="Xem tài liệu" onClick={() => onOpen(doc, false)} style={actionBtn}>
            <Icon name="eye" size={18} />
          </button>
          <button className="ad-act" aria-label="Tải xuống" title="Tải lại tài liệu" onClick={() => onOpen(doc, true)} style={actionBtn}>
            <Icon name="download" size={18} />
          </button>
          <button className="ad-del" aria-label="Xoá" onClick={() => onDelete(doc.id)} style={actionBtn}>
            <Icon name="trash" size={18} />
          </button>
        </>
      )}
    </div>
  );
}
