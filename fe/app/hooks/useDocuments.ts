"use client";

import { useState } from "react";
import type { Doc, Status } from "@/app/types/admin";
import { SEED_DOCS } from "@/app/lib/data/admin";
import { todayDMY } from "@/app/lib/time";

/** Quản lý danh sách tài liệu PDF: thêm (mô phỏng xử lý) & xoá. */
export function useDocuments() {
  const [docs, setDocs] = useState<Doc[]>(SEED_DOCS);
  const [nextId, setNextId] = useState(5);

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;
    const dd = todayDMY();
    let id = nextId;
    const added: Doc[] = files.map((f) => {
      const mb = f.size / (1024 * 1024);
      const size = mb >= 1 ? mb.toFixed(1).replace(".", ",") + " MB" : Math.round(f.size / 1024) + " KB";
      return { id: id++, name: f.name, meta: size + " · thêm " + dd, status: "processing" as Status };
    });
    setDocs((prev) => [...added, ...prev]);
    setNextId(id);
    e.target.value = "";
    setTimeout(() => setDocs((prev) => prev.map((d) => (d.status === "processing" ? { ...d, status: "ready" } : d))), 2200);
  }

  function deleteDoc(id: number) {
    setDocs((prev) => prev.filter((d) => d.id !== id));
  }

  return { docs, onPick, deleteDoc };
}
