import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Bảo vệ route cần đăng nhập (Next.js 16: "middleware" đã đổi tên thành "proxy").
 *
 * Token nằm trong httpOnly cookie do backend set; proxy đọc được cookie để chặn
 * truy cập ẩn danh. Chỉ kiểm tra SỰ TỒN TẠI của phiên (refresh_token) để
 * redirect; phân quyền admin được thực thi thật ở backend + gate client-side.
 */
export function proxy(request: NextRequest) {
  const hasSession = request.cookies.has("refresh_token");
  if (!hasSession) {
    const url = new URL("/auth", request.url);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/chat", "/chat/:path*", "/admin", "/admin/:path*"],
};
