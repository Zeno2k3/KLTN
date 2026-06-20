"use client";

import type { Convo } from "@/app/types/chat";
import Icon from "@/app/components/ui/Icon";
import IconBox from "@/app/components/ui/IconBox";

interface ConversationItemProps {
  convo: Convo;
  active: boolean;
  onClick: () => void;
}

/** Một mục trong danh sách cuộc trò chuyện ở sidebar. */
export default function ConversationItem({ convo, active, onClick }: ConversationItemProps) {
  const last = convo.messages[convo.messages.length - 1];
  const snippet = last
    ? (last.from === "user" ? "Ba mẹ: " : "") + last.text
    : (convo.preview ?? "Bắt đầu trò chuyện…");

  return (
    <div className="ch-convo" onClick={onClick} style={{ display: "flex", gap: 11, alignItems: "flex-start", padding: "10px 11px", borderRadius: 14, cursor: "pointer", transition: "background .15s", background: active ? "var(--brand-subtle)" : undefined }}>
      <IconBox size={36} radius={11} bg={convo.tint} color={convo.fg} style={{ flex: "0 0 auto" }}>
        <Icon name="chat" size={18} />
      </IconBox>
      <span style={{ flex: 1, minWidth: 0 }}>
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ flex: 1, fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 14, color: "var(--text-strong)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{convo.title}</span>
          <span style={{ flex: "0 0 auto", fontSize: 11, color: "var(--text-subtle)" }}>{convo.time}</span>
        </span>
        <span style={{ display: "block", fontSize: 12.5, color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", marginTop: 2 }}>{snippet}</span>
      </span>
    </div>
  );
}
