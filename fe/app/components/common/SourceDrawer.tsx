"use client";

import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import Button from "@/app/components/ui/Button";
import Icon from "@/app/components/ui/Icon";
import { chatApi } from "@/app/lib/api";
import { buildCitationDocument } from "@/app/lib/citations";
import type { CitationPara } from "@/app/lib/citations";
import type { DocumentDetailDTO } from "@/app/types/chat";

interface SourceDrawerProps {
  open: boolean;
  /** Tài liệu cần hiển thị; null = không mở được (nguồn thiếu document_id). */
  documentId: number | null;
  /** UUID các đoạn được trích trong tin nhắn → tô sáng. */
  citedUuids: Set<string>;
  /** UUID chunk → các đoạn nguyên văn được trích (highlight sub-chunk). */
  citedSpans?: Map<string, string[]>;
  /** Tên tạm hiện ở header trong lúc tải / khi lỗi. */
  fallbackTitle?: string;
  onClose: () => void;
}

const eyebrow: CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: "var(--ls-wider)",
  textTransform: "uppercase",
  color: "var(--brand-strong)",
};

/** Bảng tài liệu trượt từ phải: header + meta + danh sách đoạn (đoạn được trích tô sáng). */
export default function SourceDrawer({
  open,
  documentId,
  citedUuids,
  citedSpans,
  fallbackTitle,
  onClose,
}: SourceDrawerProps) {
  // Kết quả tải gắn với "khóa yêu cầu" (documentId + lần thử) để suy ra trạng thái loading
  // mà KHÔNG cần setState đồng bộ trong effect (đổi tài liệu → loading ngay, không nháy nội dung cũ).
  const [result, setResult] = useState<{
    key: string;
    dto: DocumentDetailDTO | null;
    error: boolean;
  } | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const requestKey = open && documentId != null ? `${documentId}:${reloadKey}` : null;

  // Esc để đóng (giống ConfirmDialog).
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // Nạp nội dung tài liệu khi mở / đổi tài liệu / thử lại. setState chỉ trong callback bất đồng bộ.
  useEffect(() => {
    if (!open || documentId == null) return;
    const key = `${documentId}:${reloadKey}`;
    let active = true;
    chatApi
      .getDocument(documentId)
      .then((d) => {
        if (active) setResult({ key, dto: d, error: false });
      })
      .catch(() => {
        if (active) setResult({ key, dto: null, error: true });
      });
    return () => {
      active = false;
    };
  }, [open, documentId, reloadKey]);

  // Trạng thái suy ra từ việc kết quả có khớp yêu cầu hiện tại không.
  const matches = result != null && requestKey != null && result.key === requestKey;
  const phase: "loading" | "ready" | "error" = !matches
    ? "loading"
    : result!.error
      ? "error"
      : "ready";
  const dtoData = matches && !result!.error ? result!.dto : null;

  // Tô sáng tính riêng (rẻ, thuần) để đổi citedUuids không gây nạp lại mạng.
  const doc = useMemo(
    () => (dtoData ? buildCitationDocument(dtoData, citedUuids, citedSpans) : null),
    [dtoData, citedUuids, citedSpans],
  );

  if (!open) return null;

  const title = doc?.title ?? fallbackTitle ?? "Nguồn tham khảo";

  return (
    <div
      role="presentation"
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(12, 26, 26, 0.40)",
        backdropFilter: "blur(4px)",
        WebkitBackdropFilter: "blur(4px)",
        display: "flex",
        justifyContent: "flex-end",
        zIndex: 100,
      }}
    >
      <div
        className="ch-drawer"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "min(460px, 100%)",
          height: "100%",
          background: "var(--surface-card)",
          boxShadow: "var(--shadow-xl)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 12,
            padding: 20,
            borderBottom: "1px solid var(--border-subtle)",
          }}
        >
          <span
            style={{
              flex: "0 0 auto",
              width: 40,
              height: 40,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              background: "var(--brand-subtle)",
              borderRadius: "var(--radius-md)",
              color: "var(--brand-strong)",
            }}
          >
            <Icon name="file" size={20} />
          </span>
          <span style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0, flex: 1 }}>
            <span style={eyebrow}>Nguồn tham khảo</span>
            <span
              style={{
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: 17,
                color: "var(--text-strong)",
                lineHeight: 1.25,
                wordBreak: "break-word",
              }}
            >
              {title}
            </span>
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
              {(doc?.kind ?? "Tài liệu") + " · LuminaAi"}
            </span>
          </span>
          <button
            type="button"
            className="ch-drawer-close"
            aria-label="Đóng"
            onClick={onClose}
            style={{
              flex: "0 0 auto",
              width: 36,
              height: 36,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              border: "none",
              cursor: "pointer",
              background: "var(--surface-sunken)",
              color: "var(--text-muted)",
              borderRadius: "var(--radius-circle)",
              transition: "background .15s, color .15s",
            }}
          >
            <Icon name="x" size={18} />
          </button>
        </div>

        {/* Meta bar — chỉ hiện khi đã có tài liệu */}
        {doc && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 10,
              padding: "12px 20px",
            }}
          >
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                fontSize: 12.5,
                fontWeight: 600,
                color: "var(--brand-strong)",
                background: "var(--brand-subtle)",
                border: "1px solid var(--border-brand)",
                borderRadius: "var(--radius-pill)",
                padding: "5px 12px",
              }}
            >
              <Icon name="book" size={13} />
              {doc.pages}
            </span>
            <span style={{ flex: 1, minWidth: 150, fontSize: 12.5, color: "var(--text-muted)" }}>
              Đoạn được LuminaAi trích dẫn được tô sáng bên dưới
            </span>
          </div>
        )}

        {/* Body */}
        <div className="ch-scroll" style={{ flex: 1, overflowY: "auto", padding: 20 }}>
          {phase === "loading" && (
            <p style={{ color: "var(--text-muted)", fontSize: 14 }}>Đang tải tài liệu…</p>
          )}

          {phase === "error" && (
            <div style={{ color: "var(--text-muted)", fontSize: 14 }}>
              <p style={{ margin: "0 0 12px" }}>Không tải được tài liệu. Ba mẹ thử lại nhé.</p>
              <Button variant="secondary" size="sm" onClick={() => setReloadKey((k) => k + 1)}>
                Thử lại
              </Button>
            </div>
          )}

          {phase === "ready" && doc && (
            <div
              style={{
                background: "var(--surface-card)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-xl)",
                boxShadow: "var(--shadow-sm)",
                padding: 20,
              }}
            >
              {doc.paras.length === 0 ? (
                <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 14 }}>
                  Tài liệu này hiện chưa có nội dung trích dẫn.
                </p>
              ) : (
                doc.paras.map((para, i) => <Para key={i} para={para} first={i === 0} />)
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/** Một đoạn trong tài liệu: heading, đoạn tô sáng (★), hoặc đoạn thường. */
function Para({ para, first }: { para: CitationPara; first: boolean }) {
  if (para.kind === "heading") {
    return (
      <h3
        style={{
          margin: first ? "0 0 10px" : "18px 0 10px",
          fontFamily: "var(--font-display)",
          fontWeight: 700,
          fontSize: 15,
          color: "var(--text-strong)",
        }}
      >
        {para.text}
      </h3>
    );
  }

  if (para.highlight) {
    return (
      <div
        style={{
          background: "var(--sun-50)",
          borderRadius: "var(--radius-lg)",
          padding: 16,
          margin: first ? "0 0 4px" : "12px 0 4px",
        }}
      >
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
            marginBottom: 8,
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "var(--ls-wider)",
            textTransform: "uppercase",
            color: "var(--sun-600)",
          }}
        >
          <Icon name="star" size={12} />
          Đoạn được trích dẫn
        </span>
        <p
          style={{
            margin: 0,
            fontSize: 14.5,
            lineHeight: 1.7,
            color: "var(--text-body)",
            whiteSpace: "pre-wrap",
          }}
        >
          {para.segments
            ? para.segments.map((seg, j) =>
                seg.mark ? (
                  <mark
                    key={j}
                    style={{
                      background: "var(--sun-200)",
                      color: "inherit",
                      borderRadius: 3,
                      padding: "0 1px",
                    }}
                  >
                    {seg.text}
                  </mark>
                ) : (
                  <span key={j}>{seg.text}</span>
                ),
              )
            : para.text}
        </p>
      </div>
    );
  }

  return (
    <p
      style={{
        margin: first ? 0 : "12px 0 0",
        fontSize: 14.5,
        lineHeight: 1.7,
        color: "var(--text-muted)",
        whiteSpace: "pre-wrap",
      }}
    >
      {para.text}
    </p>
  );
}
