/** Kiểu dữ liệu cho xác thực — khớp với response của backend (snake_case). */

export type Role = "admin" | "user";

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  avatar_url: string | null;
  is_active: boolean;
}

export interface RegisterInput {
  name: string;
  email: string;
  password: string;
}

export interface LoginInput {
  email: string;
  password: string;
}
