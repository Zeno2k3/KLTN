"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import Button from "@/app/components/ui/Button";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  /** Kiểu nút xác nhận (mặc định "primary"; dùng "danger" cho hành động phá hủy). */
  variant?: "primary" | "danger";
  onConfirm: () => void;
  onCancel: () => void;
}

/** Hộp thoại xác nhận ở giữa màn hình (overlay làm mờ nền). Esc / bấm nền = hủy. */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel,
  variant = "primary",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  // Giữ DOM sống trong lúc fade-out. Fade-IN dùng CSS @keyframes (giá trị nghỉ là opacity 1
  // → không bao giờ kẹt vô hình kể cả khi timer/rAF bị tab ẩn throttle); fade-OUT dùng transition.
  const [mounted, setMounted] = useState(open);

  // Mở → mount ngay (điều chỉnh state trong render: pattern React, tránh setState đồng bộ trong effect).
  if (open && !mounted) setMounted(true);

  useEffect(() => {
    if (open) return; // mở: enter animation chạy qua CSS, không cần timer
    const id = setTimeout(() => setMounted(false), 220); // đóng: unmount sau khi fade-out xong
    return () => clearTimeout(id);
  }, [open]);

  // Esc để hủy.
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!mounted) return null;

  const closing = !open; // open=false nhưng còn mounted → đang fade-out

  // Hành động phá hủy hiển thị dạng outline đỏ (đỡ hút bấm nhầm); nút an toàn (Hủy) là primary.
  const confirmVariant = variant === "danger" ? "danger-outline" : variant;

  return (
    <div
      role="presentation"
      onClick={onCancel}
      style={{ position: "fixed", inset: 0, background: "rgba(0, 0, 0, 0.4)", backdropFilter: "blur(6px)", WebkitBackdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: 20, opacity: closing ? 0 : 1, animation: closing ? "none" : "gw-fade-in .22s ease", transition: "opacity .22s ease" }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
        style={{ width: "min(420px, 100%)", background: "var(--surface-card)", borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-lg)", padding: 24, marginTop: 32, opacity: closing ? 0 : 1, transform: closing ? "translateY(8px)" : "none", animation: closing ? "none" : "gw-msg-rise .22s ease", transition: "opacity .22s ease, transform .22s ease" }}
      >
        <h2 style={{ margin: "0 0 8px", fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 19, color: "var(--text-strong)" }}>{title}</h2>
        <div style={{ margin: 0, fontSize: 14, color: "var(--text-muted)", lineHeight: 1.55 }}>{message}</div>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 28 }}>
          <Button variant='secondary' onClick={onCancel} size="sm">{cancelLabel}</Button>
          <Button variant='danger' onClick={onConfirm} size="sm">{confirmLabel}</Button>
        </div>
      </div>
    </div>
  );
}
