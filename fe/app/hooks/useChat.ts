"use client";

import { useEffect, useRef, useState } from "react";
import type { Convo } from "@/app/types/chat";
import { DEFAULT_REPLY, SCRIPTED, SEED, USER_NAME } from "@/app/lib/data/chat";
import { now, partOfDay } from "@/app/lib/time";

/** Quản lý toàn bộ state & logic của giao diện chat. */
export function useChat() {
  const [convos, setConvos] = useState<Convo[]>(SEED);
  const [activeId, setActiveId] = useState("c1");
  const [text, setText] = useState("");
  const [typing, setTyping] = useState(false);
  const [newCount, setNewCount] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  const active = convos.find((c) => c.id === activeId) ?? convos[0];
  const msgs = active ? active.messages : [];
  const isEmpty = msgs.length === 0;

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [msgs.length, typing, activeId]);

  function botRespond(targetId: string, userText: string) {
    setTyping(true);
    setTimeout(() => {
      const reply = SCRIPTED[userText] || DEFAULT_REPLY;
      setTyping(false);
      setConvos((prev) => prev.map((c) => (c.id === targetId ? { ...c, messages: [...c.messages, { from: "bot", text: reply, time: now() }] } : c)));
    }, 1100);
  }

  function send(value?: string) {
    const v = (value ?? text).trim();
    if (!v) return;
    const id = activeId;
    setConvos((prev) => prev.map((c) => {
      if (c.id !== id) return c;
      const first = c.messages.length === 0;
      return { ...c, title: first ? (v.length > 26 ? v.slice(0, 26) + "…" : v) : c.title, time: now(), messages: [...c.messages, { from: "user", text: v, time: now() }] };
    }));
    setText("");
    botRespond(id, v);
  }

  function openConvo(id: string) {
    setActiveId(id);
    setText("");
    setTyping(false);
  }

  function newChat() {
    const id = "n" + (newCount + 1);
    const convo: Convo = { id, title: "Cuộc trò chuyện mới", time: "Bây giờ", tint: "var(--ink-100)", fg: "var(--text-muted)", messages: [] };
    setNewCount((n) => n + 1);
    setConvos((prev) => [convo, ...prev]);
    setActiveId(id);
    setText("");
    setTyping(false);
  }

  const greetingText = `Xin chào buổi ${partOfDay()}, ${USER_NAME} 👋`;
  const greetingSub = "Mình là LuminaAi — trợ lý tư vấn tuyển sinh lớp 1. Mình giúp gì cho bé nhà mình hôm nay ạ?";

  return {
    convos,
    activeId,
    text,
    setText,
    typing,
    msgs,
    isEmpty,
    scrollRef,
    send,
    openConvo,
    newChat,
    greetingText,
    greetingSub,
  };
}
