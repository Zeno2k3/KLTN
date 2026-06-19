import Link from "next/link";
import Avatar from "@/app/components/ui/Avatar";
import Icon from "@/app/components/ui/Icon";
import AppHeader from "@/app/components/common/AppHeader";
import LogoBadge from "@/app/components/common/LogoBadge";

/** Header trang quản trị (dùng khung AppHeader + cụm người dùng/đăng xuất). */
export default function AdminHeader() {
  return (
    <AppHeader
      badge={<LogoBadge logoSize={28} radius={13} pad={6} shadow flex />}
      title={<>LuminaAi <span style={{ color: "var(--text-subtle)", fontWeight: 600 }}>· Quản trị</span></>}
      subtitle="Bảng điều khiển hệ thống tư vấn tuyển sinh"
      right={
        <>
          <Avatar initials="QT" bg="var(--brand)" size={38} fontSize={14} />
          <span style={{ display: "flex", flexDirection: "column", lineHeight: 1.25 }}>
            <span style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 14, color: "var(--text-strong)" }}>Quản trị viên</span>
            <span style={{ fontSize: 12, color: "var(--text-subtle)" }}>admin@luminaai.vn</span>
          </span>
          <Link href="/auth" aria-label="Đăng xuất" title="Đăng xuất" className="ad-logout" style={{ flex: "0 0 auto", marginLeft: 6, width: 40, height: 40, borderRadius: 10, border: "1px solid var(--border-default)", background: "var(--surface-card)", color: "var(--text-muted)", display: "inline-flex", alignItems: "center", justifyContent: "center", textDecoration: "none", transition: "background .15s, color .15s, border-color .15s" }}>
            <Icon name="logout" size={19} />
          </Link>
        </>
      }
    />
  );
}
