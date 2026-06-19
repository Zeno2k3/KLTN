"use client";

import { useState } from "react";
import type { StatCardData } from "@/app/types/admin";
import { useDocuments } from "@/app/hooks/useDocuments";
import AdminHeader from "./_components/AdminHeader";
import AdminSidebar from "./_components/AdminSidebar";
import DocsView from "./_components/DocsView";
import StatsView from "./_components/StatsView";

export default function AdminPage() {
  const [tab, setTab] = useState<"stats" | "docs">("stats");
  const { docs, onPick, deleteDoc } = useDocuments();
  const isStats = tab === "stats";

  const stats: StatCardData[] = [
    { label: "Phụ huynh hoạt động", value: "2.847", delta: "+12%", icon: "users", tint: "var(--teal-50)", fg: "var(--brand)" },
    { label: "Lượt trò chuyện", value: "9.130", delta: "+8%", icon: "chat", tint: "var(--sky-50)", fg: "var(--sky-600)" },
    { label: "Câu hỏi đã giải đáp", value: "24.6K", delta: "+18%", icon: "q", tint: "var(--sun-50)", fg: "var(--sun-600)" },
    { label: "Tài liệu kiến thức", value: String(docs.length), delta: "cập nhật", icon: "doc", tint: "var(--brand-subtle)", fg: "var(--brand-strong)" },
  ];

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", fontFamily: "var(--font-body)", color: "var(--text-body)", background: "var(--ink-100)" }}>
      <AdminHeader />

      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        <AdminSidebar tab={tab} onTab={setTab} docCount={docs.length} />

        <main className="ad-scroll" style={{ flex: 1, minWidth: 0, overflowY: "auto", overflowX: "hidden", padding: "30px clamp(20px,4vw,44px) 44px" }}>
          {isStats ? <StatsView stats={stats} /> : <DocsView docs={docs} onPick={onPick} onDelete={deleteDoc} />}
        </main>
      </div>
    </div>
  );
}
