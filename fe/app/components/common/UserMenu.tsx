"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Avatar from "@/app/components/ui/Avatar";
import Button from "@/app/components/ui/Button";
import Icon from "@/app/components/ui/Icon";
import { useAuth } from "@/app/_providers/AuthProvider";
import { useToast } from "@/app/_providers/ToastProvider";

/** Lấy 2 ký tự viết tắt từ tên (chữ đầu của từ đầu + từ cuối). */
function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/** Cụm người dùng + nút đăng xuất (có hộp xác nhận), dùng ở header chat & admin. */
export default function UserMenu() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Đóng hộp xác nhận khi bấm ra ngoài.
  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  async function handleLogout() {
    setOpen(false);
    // Luôn đăng xuất phía client + điều hướng, kể cả khi gọi BE lỗi (mạng/hết phiên).
    try {
      await logout();
    } catch {
      // bỏ qua — phiên phía client đã được xóa trong AuthProvider.logout()
    }
    showToast("Đăng xuất thành công", "success");
    router.push("/");
  }

  return (
    <>
      <Avatar initials={user ? initials(user.name) : "?"} bg="var(--brand)" size={38} fontSize={14} />
      <span style={{ display: "flex", flexDirection: "column", lineHeight: 1.25, minWidth: 0 }}>
        <span style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 14, color: "var(--text-strong)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{user?.name ?? "—"}</span>
        <span style={{ fontSize: 12, color: "var(--text-subtle)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{user?.email ?? ""}</span>
      </span>

      <div ref={menuRef} style={{ position: "relative", flex: "0 0 auto", marginLeft: 6 }}>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-label="Đăng xuất"
          aria-haspopup="dialog"
          aria-expanded={open}
          title="Đăng xuất"
          className="ad-logout"
          style={{ width: 40, height: 40, borderRadius: 10, border: "1px solid var(--border-default)", background: "var(--surface-card)", color: "var(--text-muted)", display: "inline-flex", alignItems: "center", justifyContent: "center", cursor: "pointer", transition: "background .15s, color .15s, border-color .15s" }}
        >
          <Icon name="logout" size={19} />
        </button>

        {open && (
          <div
            role="dialog"
            aria-label="Xác nhận đăng xuất"
            style={{ position: "absolute", top: "calc(100% + 8px)", right: 0, width: 250, background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-lg)", padding: 16, zIndex: 60, animation: "gw-msg-rise .15s ease" }}
          >
            <p style={{ margin: "0 0 6px", fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 15, color: "var(--text-strong)" }}>Đăng xuất khỏi tài khoản?</p>
            <p style={{ margin: "0 0 14px", fontSize: 13, color: "var(--text-muted)", lineHeight: 1.5 }}>Bạn sẽ cần đăng nhập lại để tiếp tục.</p>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>Hủy</Button>
              <Button variant="danger" size="sm" onClick={handleLogout}>Đăng xuất</Button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
