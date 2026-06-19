import Avatar from "@/app/components/ui/Avatar";
import SectionHeading from "@/app/components/ui/SectionHeading";
import { PARTNERS } from "@/app/lib/data/landing";

export default function PartnersMarquee() {
  return (
    <section id="donvi" style={{ maxWidth: 1180, margin: "0 auto", padding: "64px 24px 20px" }}>
      <SectionHeading
        eyebrow="Đơn vị đồng hành"
        title="Tin cậy bởi các trường & tổ chức giáo dục"
        subtitle="Dữ liệu tuyển sinh được cập nhật cùng các đơn vị đồng hành trên toàn quốc."
        titleSize={34}
        marginBottom={36}
      />
      <div className="lp-marquee-mask" style={{ position: "relative", WebkitMaskImage: "linear-gradient(90deg, transparent, #000 9%, #000 91%, transparent)", maskImage: "linear-gradient(90deg, transparent, #000 9%, #000 91%, transparent)" }}>
        <div className="lp-marquee-track">
          {[...PARTNERS, ...PARTNERS].map((p, i) => (
            <div key={`${p.name}-${i}`} className="gw-card gw-card--pad" style={{ flex: "0 0 auto", display: "flex", alignItems: "center", gap: 13, padding: "16px 22px" }}>
              <Avatar initials={p.initial} bg="var(--brand-subtle)" color="var(--brand-strong)" size={44} shape="rounded" radius={13} fontSize={16} />
              <span style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 15, color: "var(--text-strong)", lineHeight: 1.25, whiteSpace: "nowrap" }}>{p.name}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
