"use client";

import Button from "@/app/components/ui/Button";
import Icon from "@/app/components/ui/Icon";
import UserMenu from "@/app/components/common/UserMenu";
import { useAuth } from "@/app/_providers/AuthProvider";

/**
 * Cụm nút bên phải của thanh điều hướng trang chủ — PHẢN ÁNH trạng thái đăng nhập.
 *
 * `LandingNav` là Server Component tĩnh nên trước đây luôn hiện "Đăng ký", khiến
 * người dùng đã đăng nhập (cookie còn nguyên) tưởng bị đăng xuất khi quay lại trang chủ.
 * Component này (client) gọi `useAuth` để hiện đúng: đã đăng nhập → avatar + "Vào chat";
 * chưa → "Đăng ký" + "Hỏi LuminaAi".
 */
export default function LandingNavActions() {
  const { user, loading } = useAuth();

  // Đang kiểm tra phiên (/me): chừa chỗ cùng kích thước để tránh nháy "Đăng ký" rồi đổi.
  if (loading) {
    return <div aria-hidden style={{ width: 150, height: 40 }} />;
  }

  if (user) {
    return (
      <>
        <Button href="/chat" variant="primary" size="sm" iconLeft={<Icon name="message-circle" />}>
          Vào chat
        </Button>
        <UserMenu />
      </>
    );
  }

  return (
    <>
      <Button href="/auth" variant="ghost" size="sm">
        Đăng ký
      </Button>
      <Button href="/chat" variant="primary" size="sm" iconLeft={<Icon name="message-circle" />}>
        Hỏi LuminaAi
      </Button>
    </>
  );
}
