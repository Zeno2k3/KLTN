import Link from "next/link";
import type { CSSProperties, MouseEventHandler, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "accent" | "danger" | "danger-outline";
type Size = "sm" | "md" | "lg";

interface ButtonProps {
  variant?: Variant;
  size?: Size;
  block?: boolean;
  /** Có `href` → render Link (route nội bộ) hoặc <a> (#/http/mailto). Không có → <button>. */
  href?: string;
  iconLeft?: ReactNode;
  iconRight?: ReactNode;
  className?: string;
  style?: CSSProperties;
  onClick?: MouseEventHandler<HTMLElement>;
  type?: "button" | "submit" | "reset";
  title?: string;
  ariaLabel?: string;
  children?: ReactNode;
}

function buildClass(variant?: Variant, size?: Size, block?: boolean, extra?: string) {
  return ["gw-btn", variant && `gw-btn--${variant}`, size && `gw-btn--${size}`, block && "gw-btn--block", extra]
    .filter(Boolean)
    .join(" ");
}

/**
 * Bọc hệ thống nút `gw-btn`. Đa hình giữa <button> / next/link <Link> / <a>.
 */
export default function Button({
  variant,
  size,
  block,
  href,
  iconLeft,
  iconRight,
  className,
  style,
  onClick,
  type = "button",
  title,
  ariaLabel,
  children,
}: ButtonProps) {
  const cls = buildClass(variant, size, block, className);
  const inner = (
    <>
      {iconLeft && <span className="gw-btn__icon">{iconLeft}</span>}
      {children}
      {iconRight && <span className="gw-btn__icon">{iconRight}</span>}
    </>
  );

  if (href !== undefined) {
    const external = href.startsWith("#") || href.startsWith("http") || href.startsWith("mailto:");
    if (external) {
      return (
        <a href={href} className={cls} style={style} onClick={onClick} title={title} aria-label={ariaLabel}>
          {inner}
        </a>
      );
    }
    return (
      <Link href={href} className={cls} style={style} onClick={onClick} title={title} aria-label={ariaLabel}>
        {inner}
      </Link>
    );
  }

  return (
    <button type={type} className={cls} style={style} onClick={onClick} title={title} aria-label={ariaLabel}>
      {inner}
    </button>
  );
}
