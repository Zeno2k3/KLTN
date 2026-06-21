"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Convo, Msg } from "@/app/types/chat";
import { ApiError, chatApi } from "@/app/lib/api";
import { convoFromSummary, msgFromDTO, sourceFromDTO } from "@/app/lib/chat";
import { USER_NAME } from "@/app/lib/data/chat";
import { now, partOfDay } from "@/app/lib/time";

const NEW_TINT = "var(--ink-100)";
const NEW_FG = "var(--text-muted)";

function freshConvo(id: string): Convo {
  return {
    id,
    serverId: null,
    title: "Cuộc trò chuyện mới",
    time: "Bây giờ",
    tint: NEW_TINT,
    fg: NEW_FG,
    messages: [],
    loaded: true,
  };
}

function titleFrom(text: string): string {
  return text.length > 26 ? text.slice(0, 26) + "…" : text;
}

/** Quản lý state & logic chat: gọi backend RAG thật + nạp/đọc lịch sử hội thoại. */
export function useChat(userName: string = USER_NAME) {
  const [convos, setConvos] = useState<Convo[]>(() => [freshConvo("new-0")]);
  const [activeId, setActiveId] = useState("new-0");
  const [text, setText] = useState("");
  const [typing, setTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newCount, setNewCount] = useState(1);
  const scrollRef = useRef<HTMLDivElement>(null);

  const active = convos.find((c) => c.id === activeId) ?? convos[0];
  const msgs = active ? active.messages : [];
  const isEmpty = msgs.length === 0;

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [msgs.length, typing, activeId]);

  // Nạp danh sách hội thoại (sidebar) khi mở trang; im lặng nếu chưa đăng nhập.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const dtos = await chatApi.listConversations();
        if (!alive) return;
        setConvos((prev) => {
          const localDrafts = prev.filter((c) => c.serverId === null);
          return [...localDrafts, ...dtos.map(convoFromSummary)];
        });
      } catch {
        // Bỏ qua: chưa đăng nhập / lỗi mạng — vẫn cho chat, send sẽ báo lỗi nếu cần.
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const send = useCallback(
    async (value?: string) => {
      const v = (value ?? text).trim();
      if (!v || typing) return;
      const id = activeId;
      const serverId = convos.find((c) => c.id === id)?.serverId ?? null;

      setError(null);
      setText("");
      const userMsg: Msg = { from: "user", text: v, time: now() };
      setConvos((prev) =>
        prev.map((c): Convo =>
          c.id === id
            ? {
                ...c,
                title: c.messages.length === 0 ? titleFrom(v) : c.title,
                time: "Bây giờ",
                messages: [...c.messages, userMsg],
              }
            : c,
        ),
      );
      setTyping(true);

      try {
        const res = await chatApi.ask(v, serverId);
        const botMsg: Msg = {
          from: "bot",
          text: res.answer,
          time: now(),
          sources: res.sources?.length ? res.sources.map(sourceFromDTO) : undefined,
        };
        setConvos((prev) => {
          const updated = prev.map((c): Convo =>
            c.id === id
              ? {
                  ...c,
                  serverId: c.serverId ?? res.conversation_id,
                  loaded: true,
                  time: "Bây giờ",
                  messages: [...c.messages, botMsg],
                }
              : c,
          );
          // Đưa hội thoại vừa trả lời lên đầu sidebar.
          const idx = updated.findIndex((c) => c.id === id);
          if (idx > 0) {
            const [hit] = updated.splice(idx, 1);
            updated.unshift(hit);
          }
          return updated;
        });
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          setError("Phiên đăng nhập đã hết. Vui lòng đăng nhập lại để tiếp tục.");
        } else {
          setError(
            e instanceof ApiError ? e.message : "Không gửi được câu hỏi, vui lòng thử lại.",
          );
        }
      } finally {
        setTyping(false);
      }
    },
    [text, typing, activeId, convos],
  );

  const openConvo = useCallback(
    async (id: string) => {
      setActiveId(id);
      setText("");
      setError(null);
      const target = convos.find((c) => c.id === id);
      if (!target || target.serverId === null || target.loaded) return;
      const serverId = target.serverId;
      try {
        const detail = await chatApi.getMessages(serverId);
        const loadedMsgs = detail.messages.map(msgFromDTO);
        setConvos((prev) =>
          prev.map((c): Convo =>
            c.id === id ? { ...c, messages: loadedMsgs, loaded: true } : c,
          ),
        );
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Không tải được hội thoại.");
      }
    },
    [convos],
  );

  const newChat = useCallback(() => {
    const id = "new-" + newCount;
    setNewCount((n) => n + 1);
    setConvos((prev) => [freshConvo(id), ...prev]);
    setActiveId(id);
    setText("");
    setError(null);
    setTyping(false);
  }, [newCount]);

  // Đổi tên hội thoại: cập nhật lạc quan, gọi backend nếu đã có serverId; lỗi → khôi phục.
  const renameConvo = useCallback(
    async (id: string, title: string) => {
      const next = title.trim();
      const target = convos.find((c) => c.id === id);
      if (!target || !next || next === target.title) return;
      const prevTitle = target.title;
      setConvos((prev) =>
        prev.map((c): Convo => (c.id === id ? { ...c, title: next } : c)),
      );
      if (target.serverId === null) return; // draft chưa gửi — chỉ đổi local
      try {
        await chatApi.renameConversation(target.serverId, next);
      } catch (e) {
        setConvos((prev) =>
          prev.map((c): Convo => (c.id === id ? { ...c, title: prevTitle } : c)),
        );
        setError(
          e instanceof ApiError ? e.message : "Không đổi được tên hội thoại.",
        );
      }
    },
    [convos],
  );

  // Xóa hội thoại: gọi backend nếu đã có serverId; xóa cuộc đang mở → mở cuộc mới trống.
  const deleteConvo = useCallback(
    async (id: string) => {
      const target = convos.find((c) => c.id === id);
      if (!target) return;
      if (target.serverId !== null) {
        try {
          await chatApi.deleteConversation(target.serverId);
        } catch (e) {
          setError(e instanceof ApiError ? e.message : "Không xóa được hội thoại.");
          return;
        }
      }
      setError(null);
      if (id === activeId) {
        // Cuộc đang mở bị xóa → tạo cuộc trò chuyện mới trống và chuyển sang.
        const newId = "new-" + newCount;
        setNewCount((n) => n + 1);
        setConvos((prev) => [freshConvo(newId), ...prev.filter((c) => c.id !== id)]);
        setActiveId(newId);
        setText("");
        setTyping(false);
      } else {
        setConvos((prev) => prev.filter((c) => c.id !== id));
      }
    },
    [convos, activeId, newCount],
  );

  const greetingText = `Xin chào buổi ${partOfDay()}, ${userName} 👋`;
  const greetingSub =
    "Mình là LuminaAi — trợ lý tư vấn tuyển sinh lớp 1. Mình giúp gì cho bé nhà mình hôm nay ạ?";

  return {
    convos,
    activeId,
    text,
    setText,
    typing,
    error,
    msgs,
    isEmpty,
    scrollRef,
    send,
    openConvo,
    newChat,
    renameConvo,
    deleteConvo,
    greetingText,
    greetingSub,
  };
}
