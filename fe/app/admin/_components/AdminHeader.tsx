import AppHeader from "@/app/components/common/AppHeader";
import LogoBadge from "@/app/components/common/LogoBadge";
import UserMenu from "@/app/components/common/UserMenu";

/** Header trang quản trị (cụm người dùng/đăng xuất lấy từ phiên đăng nhập). */
export default function AdminHeader() {
  return (
    <AppHeader
      badge={<LogoBadge logoSize={28} radius={13} pad={6} shadow flex />}
      title={<>LuminaAi <span style={{ color: "var(--text-subtle)", fontWeight: 600 }}>· Quản trị</span></>}
      subtitle="Bảng điều khiển hệ thống tư vấn tuyển sinh"
      right={<UserMenu />}
    />
  );
}
