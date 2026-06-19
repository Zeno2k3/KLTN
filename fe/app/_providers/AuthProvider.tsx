"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { authApi } from "@/app/lib/api";
import type { LoginInput, RegisterInput, User } from "@/app/types/auth";

interface AuthContextValue {
  /** User hiện tại, null nếu chưa đăng nhập. */
  user: User | null;
  /** Đang kiểm tra phiên (gọi /me) lần đầu khi tải trang. */
  loading: boolean;
  login: (data: LoginInput) => Promise<User>;
  register: (data: RegisterInput) => Promise<User>;
  loginWithGoogle: (credential: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      setUser(await authApi.me());
    } catch {
      setUser(null);
    }
  }, []);

  // Khôi phục phiên khi tải trang (cookie có sẵn → /me).
  useEffect(() => {
    (async () => {
      await refreshUser();
      setLoading(false);
    })();
  }, [refreshUser]);

  const login = useCallback(async (data: LoginInput) => {
    const u = await authApi.login(data);
    setUser(u);
    return u;
  }, []);

  const register = useCallback(async (data: RegisterInput) => {
    const u = await authApi.register(data);
    setUser(u);
    return u;
  }, []);

  const loginWithGoogle = useCallback(async (accessToken: string) => {
    const u = await authApi.loginWithGoogle(accessToken);
    setUser(u);
    return u;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, loginWithGoogle, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth phải được dùng bên trong <AuthProvider>.");
  return ctx;
}
