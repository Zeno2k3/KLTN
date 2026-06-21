"use client";

import { useState } from "react";
import SourceDrawer from "@/app/components/common/SourceDrawer";
import CitationChip from "@/app/components/ui/CitationChip";
import Icon from "@/app/components/ui/Icon";
import type { SourceGroup } from "@/app/lib/citations";

const EMPTY: Set<string> = new Set();

/** Dòng "Nguồn:" + các chip tài liệu dưới tin bot. Tự quản một drawer (chỉ 1 mở mỗi lúc). */
export default function SourceChips({ groups }: { groups: SourceGroup[] }) {
  const [active, setActive] = useState<SourceGroup | null>(null);
  if (!groups.length) return null;

  return (
    <span
      style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6, marginTop: 8 }}
    >
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 4,
          fontSize: 12,
          fontWeight: 600,
          color: "var(--text-subtle)",
        }}
      >
        <Icon name="book" size={13} />
        Nguồn:
      </span>

      {groups.map((g, i) => (
        <CitationChip
          key={i}
          label={g.label}
          title={g.snippet ?? undefined}
          disabled={g.documentId == null}
          onClick={g.documentId != null ? () => setActive(g) : undefined}
        />
      ))}

      <SourceDrawer
        open={active != null}
        documentId={active?.documentId ?? null}
        citedUuids={active?.citedUuids ?? EMPTY}
        fallbackTitle={active?.label}
        onClose={() => setActive(null)}
      />
    </span>
  );
}
