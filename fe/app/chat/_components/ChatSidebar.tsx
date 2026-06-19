"use client";

import type { Convo } from "@/app/types/chat";
import Icon from "@/app/components/ui/Icon";
import ConversationItem from "./ConversationItem";
import UserCard from "./UserCard";

interface ChatSidebarProps {
  convos: Convo[];
  activeId: string;
  onOpen: (id: string) => void;
  onNew: () => void;
}

/** Sidebar trái: nút tạo mới + danh sách cuộc trò chuyện + thẻ người dùng. */
export default function ChatSidebar({ convos, activeId, onOpen, onNew }: ChatSidebarProps) {
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
          <ConversationItem key={c.id} convo={c} active={c.id === activeId} onClick={() => onOpen(c.id)} />
        ))}
      </div>

      <UserCard />
    </aside>
  );
}
