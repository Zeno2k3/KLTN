import type { StatCardData } from "@/app/types/admin";
import Icon from "@/app/components/ui/Icon";
import IconBox from "@/app/components/ui/IconBox";

/** Thẻ số liệu thống kê (icon + delta + giá trị + nhãn). */
export default function AdminStatCard({ stat }: { stat: StatCardData }) {
  return (
    <div className="gw-card gw-card--pad">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <IconBox size={42} radius={12} bg={stat.tint} color={stat.fg}>
          <Icon name={stat.icon} size={21} />
        </IconBox>
        <span style={{ fontFamily: "var(--font-body)", fontWeight: 700, fontSize: 12.5, color: "var(--success-600)", background: "var(--success-50)", borderRadius: "var(--radius-pill)", padding: "3px 9px" }}>{stat.delta}</span>
      </div>
      <div style={{ fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 32, color: "var(--text-strong)", lineHeight: 1, marginTop: 16 }}>{stat.value}</div>
      <div style={{ marginTop: 6, fontSize: 14, color: "var(--text-muted)" }}>{stat.label}</div>
    </div>
  );
}
