import type { CSSProperties } from "react";
import type { Msg } from "@/app/types/chat";
import Avatar from "@/app/components/ui/Avatar";
import LogoBadge from "@/app/components/common/LogoBadge";

const bubbleBase: CSSProperties = {
  fontFamily: "var(--font-body)",
  fontSize: 15,
  lineHeight: 1.55,
  padding: "11px 15px",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-xs)",
  wordWrap: "break-word",
  textWrap: "pretty",
  maxWidth: 560,
};

/** Một bong bóng tin nhắn (bot hoặc user) kèm avatar & thời gian. */
export default function MessageBubble({ message, showAvatar }: { message: Msg; showAvatar: boolean }) {
  const isBot = message.from === "bot";
  return (
    <div className="ch-row" style={{ display: "flex", gap: 10, alignItems: "flex-end", alignSelf: isBot ? "flex-start" : "flex-end", flexDirection: isBot ? "row" : "row-reverse" }}>
      {showAvatar && isBot && <LogoBadge logoSize={22} radius={11} size={36} shadow flex />}
      {showAvatar && !isBot && <Avatar initials="BM" bg="var(--sky-400)" size={36} fontSize={13} />}
      {!showAvatar && <span style={{ flex: "0 0 auto", width: 36 }} />}
      <span style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
        <span
          style={{
            ...bubbleBase,
            ...(isBot
              ? { background: "var(--surface-card)", color: "var(--text-body)", border: "1px solid var(--border-subtle)", borderBottomLeftRadius: 6 }
              : { background: "var(--brand)", color: "#fff", borderBottomRightRadius: 6, boxShadow: "var(--shadow-brand)" }),
          }}
        >
          {message.text}
        </span>
        <span style={{ fontSize: 12, color: "var(--text-subtle)", marginTop: 6, textAlign: isBot ? "left" : "right" }}>{message.time}</span>
      </span>
    </div>
  );
}
