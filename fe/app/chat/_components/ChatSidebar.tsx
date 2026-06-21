"use client";

import { useState } from "react";
import type { Convo } from "@/app/types/chat";
import Icon from "@/app/components/ui/Icon";
import ConfirmDialog from "@/app/components/common/ConfirmDialog";
import ConversationItem from "./ConversationItem";

interface ChatSidebarProps {
  convos: Convo[];
  activeId: string;
  onOpen: (id: string) => void;
  onNew: () => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
}

/** Sidebar trái: nút tạo mới + danh sách cuộc trò chuyện + thẻ người dùng. */
export default function ChatSidebar({ convos, activeId, onOpen, onNew, onRename, onDelete }: ChatSidebarProps) {
  const [pendingDelete, setPendingDelete] = useState<Convo | null>(null);

  return (
    <aside className="ch-side" style={{ flex: "0 0 290px", minWidth: 0, overflow: "hidden", display: "flex", flexDirection: "column", background: "var(--surface-card)", borderRight: "1px solid var(--border-subtle)" }}>
      <div style={{ padding: "14px 14px 8px" }}>
        <button onClick={onNew} className="ch-newchat" style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 8, height: 44, borderRadius: "var(--radius-pill)", background: "var(--brand)", color: "#fff", border: "none", cursor: "pointer", fontFamily: "var(--font-body)", fontWeight: 700, fontSize: 15, boxShadow: "var(--shadow-brand)", transition: "background .15s" }}>
          <Icon name="plus" size={18} />
          Cuộc trò chuyện mới
        </button>
      </div>

      <div style={{ padding: "12px 14px 6px", fontSize: 12, fontWeight: 800, letterSpacing: ".06em", textTransform: "uppercase", color: "var(--text-subtle)" }}>Gần đây</div>
      <div className="ch-scroll" style={{ flex: 1, overflowY: "auto", overflowX: "hidden", padding: "0 10px 14px", display: "flex", flexDirection: "column", gap: 3 }}>
        {convos.map((c) => (
          <ConversationItem
            key={c.id}
            convo={c}
            active={c.id === activeId}
            onClick={() => onOpen(c.id)}
            onRename={onRename}
            onRequestDelete={setPendingDelete}
          />
        ))}
      </div>

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Xóa cuộc trò chuyện"
        message={
          <>
            Bạn có chắc muốn xóa <strong style={{ color: "var(--text-strong)" }}>“{pendingDelete?.title}”</strong> không?
            <br />
            Hành động này không thể hoàn tác.
          </>
        }
        confirmLabel="Xóa"
        cancelLabel="Hủy"
        variant="danger"
        onConfirm={() => {
          if (pendingDelete) onDelete(pendingDelete.id);
          setPendingDelete(null);
        }}
        onCancel={() => setPendingDelete(null)}
      />
    </aside>
  );
}
