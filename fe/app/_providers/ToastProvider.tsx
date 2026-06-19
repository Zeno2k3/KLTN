"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

type ToastType = "success" | "error" | "info";

interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  /** Hiện một toast ở góc trái dưới màn hình (tự ẩn sau ~3.5s). */
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const ACCENT: Record<ToastType, string> = {
  success: "var(--success-500)",
  error: "var(--danger-500)",
  info: "var(--brand)",
};
const SYMBOL: Record<ToastType, string> = { success: "✓", error: "✕", info: "i" };

let _toastId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string, type: ToastType = "success") => {
    const id = ++_toastId;
    setToasts((list) => [...list, { id, message, type }]);
    setTimeout(() => {
      setToasts((list) => list.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  // Hiện toast còn "treo" sau khi điều hướng cứng (vd vừa đăng nhập xong rồi
  // window.location.assign sang /chat hoặc /admin).
  useEffect(() => {
    let pending: string | null = null;
    try {
      pending = sessionStorage.getItem("lumina_toast");
    } catch {
      pending = null;
    }
    if (!pending) return;
    const message = pending;
    // Xóa key BÊN TRONG timer (không phải ngay đây) để chịu được StrictMode chạy
    // effect 2 lần ở dev — lần chạy thứ hai vẫn thấy giá trị, không bị mất toast.
    const timer = setTimeout(() => {
      try {
        sessionStorage.removeItem("lumina_toast");
      } catch {
        /* bỏ qua */
      }
      showToast(message, "success");
    }, 0);
    return () => clearTimeout(timer);
  }, [showToast]);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div
        style={{
          position: "fixed",
          left: 20,
          bottom: 20,
          zIndex: 1000,
          display: "flex",
          flexDirection: "column",
          gap: 10,
          pointerEvents: "none",
        }}
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 11,
              minWidth: 240,
              maxWidth: 360,
              padding: "12px 16px",
              background: "var(--surface-card)",
              border: "1px solid var(--border-subtle)",
              borderLeft: `4px solid ${ACCENT[t.type]}`,
              borderRadius: "var(--radius-lg)",
              boxShadow: "var(--shadow-lg)",
              fontFamily: "var(--font-body)",
              fontSize: 14,
              fontWeight: 600,
              color: "var(--text-strong)",
              animation: "gw-msg-rise .2s ease",
            }}
          >
            <span
              style={{
                flex: "0 0 auto",
                width: 22,
                height: 22,
                borderRadius: "50%",
                background: ACCENT[t.type],
                color: "#fff",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 13,
                fontWeight: 800,
              }}
            >
              {SYMBOL[t.type]}
            </span>
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast phải được dùng bên trong <ToastProvider>.");
  return ctx;
}
