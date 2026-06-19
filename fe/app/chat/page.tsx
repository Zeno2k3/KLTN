"use client";

import AppHeader from "@/app/components/common/AppHeader";
import LogoBadge from "@/app/components/common/LogoBadge";
import { useChat } from "@/app/hooks/useChat";
import { TOPICS } from "@/app/lib/data/chat";
import ChatSidebar from "./_components/ChatSidebar";
import ChatThread from "./_components/ChatThread";
import Composer from "./_components/Composer";

export default function ChatPage() {
  const chat = useChat();

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", fontFamily: "var(--font-body)", color: "var(--text-body)", background: "var(--ink-100)" }}>
      <AppHeader
        badge={<LogoBadge logoSize={28} radius={13} pad={6} shadow flex />}
        title="LuminaAi"
        subtitle={
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--success-500)" }} />
            Trợ lý tuyển sinh · trực tuyến
          </span>
        }
      />

      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        <ChatSidebar convos={chat.convos} activeId={chat.activeId} onOpen={chat.openConvo} onNew={chat.newChat} />

        <main style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          <ChatThread
            scrollRef={chat.scrollRef}
            msgs={chat.msgs}
            isEmpty={chat.isEmpty}
            typing={chat.typing}
            greetingText={chat.greetingText}
            greetingSub={chat.greetingSub}
            topics={TOPICS}
            onTopic={(t) => chat.send(t)}
          />
          <Composer value={chat.text} onChange={chat.setText} onSend={() => chat.send()} />
        </main>
      </div>
    </div>
  );
}
