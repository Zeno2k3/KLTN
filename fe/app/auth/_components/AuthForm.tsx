"use client";

import { useState, type CSSProperties, type FormEvent } from "react";
import { useGoogleLogin } from "@react-oauth/google";
import Button from "@/app/components/ui/Button";
import Icon from "@/app/components/ui/Icon";
import TextField from "@/app/components/ui/TextField";
import { useAuth } from "@/app/_providers/AuthProvider";

/**
 * Điều hướng sau khi đăng nhập/đăng ký. Dùng điều hướng cứng (window.location)
 * thay vì router.push để CHẮC CHẮN chuyển trang kể cả khi gọi từ callback popup
 * Google (chạy ngoài luồng sự kiện React) — đồng thời để proxy + AuthProvider
 * chạy lại với cookie mới. Toast được giữ qua sessionStorage để hiện ở trang đích.
 */
function redirectAfterAuth(role: string, message: string) {
  try {
    sessionStorage.setItem("lumina_toast", message);
  } catch {
    /* sessionStorage bị chặn — bỏ qua, vẫn điều hướng */
  }
  window.location.assign(role === "admin" ? "/admin" : "/chat");
}

const tabBase: CSSProperties = {
  flex: 1,
  height: 38,
  border: "none",
  borderRadius: "var(--radius-pill)",
  cursor: "pointer",
  fontFamily: "var(--font-body)",
  fontWeight: 700,
  fontSize: 14.5,
};
const activeTab: CSSProperties = { ...tabBase, background: "var(--surface-card)", color: "var(--brand-strong)", boxShadow: "var(--shadow-xs)" };
const idleTab: CSSProperties = { ...tabBase, background: "transparent", color: "var(--text-muted)" };

/** Form đăng ký / đăng nhập với 2 tab (email + Google). */
export default function AuthForm() {
  const { login, register, loginWithGoogle } = useAuth();

  const [mode, setMode] = useState<"register" | "login">("register");
  const isRegister = mode === "register";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [agree, setAgree] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Luồng access token: mở popup Google, nhận access_token rồi gửi BE xác thực.
  const googleLogin = useGoogleLogin({
    scope: "openid email profile",
    onSuccess: (resp) => handleGoogle(resp.access_token),
    onError: () => setError("Đăng nhập Google thất bại."),
  });

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (isRegister && !name.trim()) return setError("Vui lòng nhập họ và tên.");
    if (!email.trim()) return setError("Vui lòng nhập email.");
    if (isRegister && password.length < 8) return setError("Mật khẩu tối thiểu 8 ký tự.");
    if (!password) return setError("Vui lòng nhập mật khẩu.");
    if (isRegister && !agree) return setError("Vui lòng đồng ý với Điều khoản.");

    setLoading(true);
    try {
      const u = isRegister
        ? await register({ name: name.trim(), email: email.trim(), password })
        : await login({ email: email.trim(), password });
      redirectAfterAuth(u.role, isRegister ? "Đăng ký thành công" : "Đăng nhập thành công");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Có lỗi xảy ra, vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogle(accessToken?: string) {
    if (!accessToken) return setError("Không lấy được thông tin từ Google.");
    setError(null);
    setLoading(true);
    try {
      const u = await loginWithGoogle(accessToken);
      redirectAfterAuth(u.role, "Đăng nhập thành công");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng nhập Google thất bại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ width: "100%", maxWidth: 412 }}>
      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, padding: 4, background: "var(--ink-100)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-pill)", marginBottom: 26 }}>
        <button type="button" onClick={() => { setMode("register"); setError(null); }} style={isRegister ? activeTab : idleTab}>Đăng ký</button>
        <button type="button" onClick={() => { setMode("login"); setError(null); }} style={isRegister ? idleTab : activeTab}>Đăng nhập</button>
      </div>

      <h1 style={{ fontSize: 28, margin: "0 0 6px", color: "var(--text-strong)" }}>{isRegister ? "Tạo tài khoản" : "Chào mừng trở lại"}</h1>
      <p style={{ fontSize: 15, color: "var(--text-muted)", margin: "0 0 24px" }}>{isRegister ? "Bắt đầu hành trình tìm trường cho con cùng LuminaAi." : "Đăng nhập để tiếp tục cuộc trò chuyện của bạn."}</p>

      {/* Google chỉ ở tab Đăng nhập — đăng nhập Google tự tạo tài khoản nếu chưa có,
          nên không cần "đăng ký bằng Google" riêng. Nút tùy biến theo thiết kế Lumina. */}
      {!isRegister && (
        <>
          <button
            type="button"
            className="az-google"
            onClick={() => googleLogin()}
            disabled={loading}
            style={{ width: "100%", height: 50, display: "flex", alignItems: "center", justifyContent: "center", gap: 11, background: "var(--surface-card)", border: "1.5px solid var(--border-default)", borderRadius: "var(--radius-lg)", fontFamily: "var(--font-body)", fontWeight: 700, fontSize: 15, color: "var(--text-strong)", cursor: loading ? "default" : "pointer", transition: "background .15s, border-color .15s" }}
          >
            <svg width="20" height="20" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.7-6.1 8-11.3 8a12 12 0 1 1 7.9-21l5.7-5.7A20 20 0 1 0 24 44a20 20 0 0 0 19.6-23.5Z" /><path fill="#FF3D00" d="m6.3 14.7 6.6 4.8A12 12 0 0 1 24 12c3 0 5.8 1.2 7.9 3l5.7-5.7A20 20 0 0 0 6.3 14.7Z" /><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2A12 12 0 0 1 12.7 28l-6.5 5C9.6 39.6 16.3 44 24 44Z" /><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3a12 12 0 0 1-4.1 5.6l6.2 5.2C39 39.9 44 33.6 44 24c0-1.2-.1-2.4-.4-3.5Z" /></svg>
            Tiếp tục với Google
          </button>

          {/* divider */}
          <div style={{ display: "flex", alignItems: "center", gap: 14, margin: "20px 0" }}>
            <span style={{ flex: 1, height: 1, background: "var(--border-subtle)" }} />
            <span style={{ fontSize: 13, color: "var(--text-subtle)" }}>hoặc dùng email</span>
            <span style={{ flex: 1, height: 1, background: "var(--border-subtle)" }} />
          </div>
        </>
      )}

      {/* form */}
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 15 }}>
        {isRegister && (
          <TextField
            label="Họ và tên"
            type="text"
            placeholder="Nguyễn Thu Hà"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="name"
            disabled={loading}
          />
        )}
        <TextField
          label="Email"
          type="email"
          placeholder="bame@email.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          disabled={loading}
        />
        <TextField
          label={
            <>
              Mật khẩu
              {!isRegister && <a href="#" style={{ marginLeft: "auto", fontWeight: 600, fontSize: 13, color: "var(--brand-strong)", textDecoration: "none" }}>Quên mật khẩu?</a>}
            </>
          }
          labelStyle={{ display: "flex", alignItems: "center" }}
          type="password"
          placeholder="Tối thiểu 8 ký tự"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete={isRegister ? "new-password" : "current-password"}
          disabled={loading}
        />

        {isRegister && (
          <label style={{ display: "flex", alignItems: "flex-start", gap: 10, fontSize: 13.5, color: "var(--text-muted)", lineHeight: 1.5, marginTop: 1 }}>
            <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} style={{ width: 18, height: 18, marginTop: 1, accentColor: "var(--brand)", flex: "0 0 auto" }} />
            <span>Tôi đồng ý với <a href="#" style={{ color: "var(--brand-strong)", fontWeight: 600, textDecoration: "none" }}>Điều khoản</a> và <a href="#" style={{ color: "var(--brand-strong)", fontWeight: 600, textDecoration: "none" }}>Chính sách bảo mật</a> của LuminaAi.</span>
          </label>
        )}

        {error && (
          <p role="alert" style={{ margin: 0, fontSize: 13.5, color: "var(--danger-600)", background: "var(--danger-50)", border: "1px solid var(--danger-200)", borderRadius: "var(--radius-md)", padding: "9px 12px" }}>
            {error}
          </p>
        )}

        <Button type="submit" variant="primary" size="lg" style={{ width: "100%", marginTop: 6 }} iconRight={<Icon name="arrow-right" />}>
          {loading ? "Đang xử lý…" : isRegister ? "Tạo tài khoản" : "Đăng nhập"}
        </Button>
      </form>

      <p style={{ textAlign: "center", fontSize: 14.5, color: "var(--text-muted)", margin: "22px 0 0" }}>
        {isRegister ? "Đã có tài khoản?" : "Chưa có tài khoản?"}{" "}
        <a href="#" onClick={(e) => { e.preventDefault(); setMode(isRegister ? "login" : "register"); setError(null); }} style={{ color: "var(--brand-strong)", fontWeight: 700, textDecoration: "none" }}>
          {isRegister ? "Đăng nhập" : "Đăng ký ngay"}
        </a>
      </p>
    </div>
  );
}
