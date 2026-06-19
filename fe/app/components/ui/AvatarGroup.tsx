import Avatar from "@/app/components/ui/Avatar";

interface AvatarGroupProps {
  items: { initials: string; bg: string }[];
  size?: number;
  /** Độ chồng lấn giữa các avatar (px). */
  overlap?: number;
  border: string;
  fontSize?: number;
}

/** Cụm avatar chồng lên nhau. */
export default function AvatarGroup({ items, size = 38, overlap = 11, border, fontSize = 14 }: AvatarGroupProps) {
  return (
    <div style={{ display: "flex" }}>
      {items.map((a, i) => (
        <Avatar
          key={a.initials}
          initials={a.initials}
          bg={a.bg}
          size={size}
          border={border}
          fontSize={fontSize}
          style={{ marginLeft: i === 0 ? 0 : -overlap }}
        />
      ))}
    </div>
  );
}
