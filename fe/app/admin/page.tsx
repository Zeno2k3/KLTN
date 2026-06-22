"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useDocuments } from "@/app/hooks/useDocuments";
import { useAuth } from "@/app/_providers/AuthProvider";
import AdminHeader from "./_components/AdminHeader";
import AdminSidebar from "./_components/AdminSidebar";
import DocsView from "./_components/DocsView";
import StatsView from "./_components/StatsView";

export default function AdminPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [tab, setTab] = useState<"stats" | "docs">("stats");
  const { docs, loading: docsLoading, error: docsError, onPick, deleteDoc, deleteAll, renameDoc, openDoc } = useDocuments();
  const isStats = tab === "stats";

  // Chỉ admin mới vào được; backend cũng chặn các API admin (require_admin).
  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/auth");
    else if (user.role !== "admin") router.replace("/chat");
  }, [loading, user, router]);

  if (loading || !user || user.role !== "admin") {
    return (
      <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-body)", color: "var(--text-muted)" }}>
        Đang tải…
      </div>
    );
  }

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", fontFamily: "var(--font-body)", color: "var(--text-body)", background: "var(--ink-100)" }}>
      <AdminHeader />

      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        <AdminSidebar tab={tab} onTab={setTab} docCount={docs.length} />

        <main className="ad-scroll" style={{ flex: 1, minWidth: 0, overflowY: "auto", overflowX: "hidden", padding: "30px clamp(20px,4vw,44px) 44px" }}>
          {isStats ? <StatsView /> : <DocsView docs={docs} onPick={onPick} onDelete={deleteDoc} onDeleteAll={deleteAll} onOpen={openDoc} onRename={renameDoc} loading={docsLoading} error={docsError} />}
        </main>
      </div>
    </div>
  );
}
