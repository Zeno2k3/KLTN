"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import AppHeader from "@/app/components/common/AppHeader";
import LogoBadge from "@/app/components/common/LogoBadge";
import UserMenu from "@/app/components/common/UserMenu";
import { useChat } from "@/app/hooks/useChat";
import { TOPICS } from "@/app/lib/data/chat";
import { useAuth } from "@/app/_providers/AuthProvider";
import ChatSidebar from "./_components/ChatSidebar";
import ChatThread from "./_components/ChatThread";
import Composer from "./_components/Composer";

export default function ChatPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const chat = useChat(user?.name);

  // Chat cá nhân hoá + lịch sử cần đăng nhập; chưa đăng nhập → về trang /auth.
  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/auth");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-body)", color: "var(--text-muted)" }}>
        Đang tải…
      </div>
    );
  }

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
        right={<UserMenu />}
      />

      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        <ChatSidebar convos={chat.convos} activeId={chat.activeId} onOpen={chat.openConvo} onNew={chat.newChat} onRename={chat.renameConvo} onDelete={chat.deleteConvo} />

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
          {chat.error && (
            <div style={{ margin: "0 clamp(18px,6vw,90px) 4px", padding: "8px 12px", background: "var(--surface-card)", border: "1px solid var(--danger-500)", color: "var(--danger-500)", borderRadius: "var(--radius-sm)", fontSize: 13, textAlign: "center" }}>
              {chat.error}
            </div>
          )}
          <Composer value={chat.text} onChange={chat.setText} onSend={() => chat.send()} disabled={chat.typing} />
        </main>
      </div>
    </div>
  );
}
