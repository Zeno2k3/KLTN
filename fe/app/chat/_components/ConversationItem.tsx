"use client";

import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import type { Convo } from "@/app/types/chat";
import Icon from "@/app/components/ui/Icon";
import IconBox from "@/app/components/ui/IconBox";

interface ConversationItemProps {
  convo: Convo;
  active: boolean;
  onClick: () => void;
  /** Đổi tên (inline) — gọi khi người dùng xác nhận tên mới. */
  onRename: (id: string, title: string) => void;
  /** Yêu cầu xóa — đẩy lên sidebar để mở hộp xác nhận. */
  onRequestDelete: (convo: Convo) => void;
}

/** Một mục trong danh sách cuộc trò chuyện ở sidebar (kèm menu 3 chấm). */
export default function ConversationItem({
  convo,
  active,
  onClick,
  onRename,
  onRequestDelete,
}: ConversationItemProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(convo.title);
  const menuRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // Đảm bảo kết thúc sửa chỉ chạy 1 lần (tránh blur kích hoạt lại sau Enter/Esc).
  const editingRef = useRef(false);

  const last = convo.messages[convo.messages.length - 1];
  const snippet = last
    ? (last.from === "user" ? "Ba mẹ: " : "") + last.text
    : (convo.preview ?? "Bắt đầu trò chuyện…");

  // Đóng menu khi bấm ra ngoài.
  useEffect(() => {
    if (!menuOpen) return;
    function onPointerDown(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [menuOpen]);

  // Vào chế độ sửa → focus + chọn toàn bộ tên.
  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  function beginEdit() {
    setMenuOpen(false);
    setDraft(convo.title);
    editingRef.current = true;
    setEditing(true);
  }

  function endEdit(save: boolean) {
    if (!editingRef.current) return; // đã kết thúc rồi → bỏ qua (blur sau Enter/Esc)
    editingRef.current = false;
    setEditing(false);
    if (save) {
      const next = draft.trim();
      if (next && next !== convo.title) onRename(convo.id, next);
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

  const menuItemBase = {
    width: "100%",
    display: "flex",
    alignItems: "center",
    gap: 9,
    padding: "8px 10px",
    border: "none",
    background: "transparent",
    borderRadius: 9,
    cursor: "pointer",
    fontFamily: "var(--font-body)",
    fontSize: 13.5,
    fontWeight: 600,
    textAlign: "left" as const,
  };

  return (
    <div
      className="ch-convo"
      onClick={editing ? undefined : onClick}
      style={{
        position: "relative",
        display: "flex",
        gap: 11,
        alignItems: "flex-start",
        padding: "10px 11px",
        borderRadius: 14,
        cursor: editing ? "default" : "pointer",
        transition: "background .15s",
        background: active ? "var(--brand-subtle)" : undefined,
      }}
    >
      <IconBox size={36} radius={11} bg={convo.tint} color={convo.fg} style={{ flex: "0 0 auto" }}>
        <Icon name="chat" size={18} />
      </IconBox>
      <span style={{ flex: 1, minWidth: 0 }}>
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {editing ? (
            <input
              ref={inputRef}
              value={draft}
              maxLength={255}
              aria-label="Tên cuộc trò chuyện"
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={onInputKeyDown}
              onBlur={() => endEdit(true)}
              onClick={(e) => e.stopPropagation()}
              style={{
                flex: 1,
                minWidth: 0,
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: 14,
                color: "var(--text-strong)",
                border: "1px solid var(--brand)",
                borderRadius: 8,
                padding: "2px 6px",
                outline: "none",
                background: "var(--surface-card)",
              }}
            />
          ) : (
            <>
              <span style={{ flex: 1, fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 14, color: "var(--text-strong)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{convo.title}</span>
              <span style={{ flex: "0 0 auto", fontSize: 11, color: "var(--text-subtle)" }}>{convo.time}</span>
              <div
                ref={menuRef}
                className="ch-convo__menu"
                style={{ position: "relative", flex: "0 0 auto", opacity: menuOpen || active ? 1 : undefined }}
              >
                <button
                  type="button"
                  className="ch-convo__menu-btn"
                  aria-label="Tùy chọn cuộc trò chuyện"
                  aria-haspopup="menu"
                  aria-expanded={menuOpen}
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen((o) => !o);
                  }}
                  style={{ width: 26, height: 26, display: "inline-flex", alignItems: "center", justifyContent: "center", border: "none", background: "transparent", color: "var(--text-subtle)", borderRadius: 7, cursor: "pointer" }}
                >
                  <Icon name="more-vertical" size={16} />
                </button>
                {menuOpen && (
                  <div
                    role="menu"
                    style={{ position: "absolute", top: "calc(100% + 4px)", right: 0, minWidth: 190, background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: 12, boxShadow: "var(--shadow-lg)", padding: 6, zIndex: 40, animation: "gw-msg-rise .15s ease" }}
                  >
                    <button
                      type="button"
                      role="menuitem"
                      className="ch-menu-item"
                      onClick={(e) => {
                        e.stopPropagation();
                        beginEdit();
                      }}
                      style={{ ...menuItemBase, color: "var(--text-strong)" }}
                    >
                      <Icon name="edit" size={16} />
                      Đổi tên
                    </button>
                    <button
                      type="button"
                      role="menuitem"
                      className="ch-menu-item ch-menu-item--danger"
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpen(false);
                        onRequestDelete(convo);
                      }}
                      style={{ ...menuItemBase, color: "var(--danger-500)" }}
                    >
                      <Icon name="trash" size={16} />
                      Xóa cuộc trò chuyện
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </span>
        {!editing && (
          <span style={{ display: "block", fontSize: 12.5, color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", marginTop: 2 }}>{snippet}</span>
        )}
      </span>
    </div>
  );
}
