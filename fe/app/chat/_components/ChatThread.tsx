"use client";

import type { RefObject } from "react";
import type { Msg } from "@/app/types/chat";
import EmptyState from "./EmptyState";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";

interface ChatThreadProps {
  scrollRef: RefObject<HTMLDivElement | null>;
  msgs: Msg[];
  isEmpty: boolean;
  typing: boolean;
  greetingText: string;
  greetingSub: string;
  topics: string[];
  onTopic: (t: string) => void;
}

/** Vùng cuộn chứa lời chào / danh sách tin nhắn / hiệu ứng đang gõ. */
export default function ChatThread({ scrollRef, msgs, isEmpty, typing, greetingText, greetingSub, topics, onTopic }: ChatThreadProps) {
  return (
    <div ref={scrollRef} className="ch-scroll" style={{ flex: 1, overflowY: "auto", overflowX: "hidden", padding: "24px clamp(18px,6vw,90px)", display: "flex", flexDirection: "column", gap: 14, background: "var(--ink-100)" }}>
      {!isEmpty && (
        <div style={{ alignSelf: "center", fontSize: 12, color: "var(--text-subtle)", background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-pill)", padding: "5px 14px", marginBottom: 2 }}>Hôm nay</div>
      )}

      {isEmpty && <EmptyState greetingText={greetingText} greetingSub={greetingSub} topics={topics} onTopic={onTopic} />}

      {msgs.map((m, i) => (
        <MessageBubble key={i} message={m} showAvatar={i === 0 || msgs[i - 1].from !== m.from} />
      ))}

      {typing && <TypingIndicator />}
    </div>
  );
}
