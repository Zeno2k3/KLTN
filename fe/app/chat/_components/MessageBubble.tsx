import type { CSSProperties } from "react";
import type { Msg, Source } from "@/app/types/chat";
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

/** Gộp nguồn trùng (theo document_id, fallback filename) để tránh hiện chip lặp. */
function dedupeSources(sources?: Source[]): Source[] {
  if (!sources?.length) return [];
  const seen = new Set<string>();
  const out: Source[] = [];
  for (const s of sources) {
    const key =
      s.document_id != null ? `d${s.document_id}` : (s.filename ?? `i${s.index}`);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(s);
  }
  return out;
}

function sourceLabel(s: Source): string {
  if (s.filename) return s.filename;
  if (s.document_id != null) return `Tài liệu #${s.document_id}`;
  return "Tài liệu";
}

/** Một bong bóng tin nhắn (bot hoặc user) kèm avatar, thời gian & chip nguồn (chỉ bot). */
export default function MessageBubble({ message, showAvatar }: { message: Msg; showAvatar: boolean }) {
  const isBot = message.from === "bot";
  const sources = isBot ? dedupeSources(message.sources) : [];
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

        {sources.length > 0 && (
          <span style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6, marginTop: 8 }}>
            <span style={{ fontSize: 11.5, color: "var(--text-subtle)" }}>Nguồn:</span>
            {sources.map((s, i) => (
              <span
                key={i}
                title={s.snippet ?? undefined}
                style={{ fontSize: 11.5, fontFamily: "var(--font-body)", color: "var(--brand-strong)", background: "var(--brand-subtle)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-pill)", padding: "3px 10px", maxWidth: 240, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
              >
                {sourceLabel(s)}
              </span>
            ))}
          </span>
        )}

        <span style={{ fontSize: 12, color: "var(--text-subtle)", marginTop: 6, textAlign: isBot ? "left" : "right" }}>{message.time}</span>
      </span>
    </div>
  );
}
