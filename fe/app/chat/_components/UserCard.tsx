import Avatar from "@/app/components/ui/Avatar";
import Icon from "@/app/components/ui/Icon";

/** Thẻ thông tin người dùng ở cuối sidebar chat. */
export default function UserCard() {
  return (
    <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: 11 }}>
      <Avatar initials="HN" bg="var(--sky-400)" size={38} fontSize={14} />
      <span style={{ flex: 1, minWidth: 0 }}>
        <span style={{ display: "block", fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 14, color: "var(--text-strong)" }}>Chị Hồng Nhung</span>
        <span style={{ display: "block", fontSize: 12, color: "var(--text-subtle)" }}>Phụ huynh bé Bốp</span>
      </span>
      <span style={{ flex: "0 0 auto", color: "var(--text-subtle)" }}>
        <Icon name="gear" size={18} />
      </span>
    </div>
  );
}
