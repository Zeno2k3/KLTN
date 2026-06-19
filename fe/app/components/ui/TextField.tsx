import type { ChangeEventHandler, CSSProperties, ReactNode } from "react";

const inputStyle: CSSProperties = {
  height: 48,
  padding: "0 15px",
  border: "1.5px solid var(--border-default)",
  borderRadius: "var(--radius-lg)",
  fontFamily: "var(--font-body)",
  fontSize: 15,
  color: "var(--text-strong)",
  background: "var(--surface-card)",
  transition: "border-color .15s, box-shadow .15s",
};

const labelText: CSSProperties = { fontSize: 13.5, fontWeight: 700, color: "var(--text-strong)" };

interface TextFieldProps {
  label: ReactNode;
  type?: string;
  placeholder?: string;
  name?: string;
  /** Style bổ sung cho phần label (vd hàng label có link "Quên mật khẩu?"). */
  labelStyle?: CSSProperties;
  value?: string;
  onChange?: ChangeEventHandler<HTMLInputElement>;
  required?: boolean;
  autoComplete?: string;
  disabled?: boolean;
}

/** Ô nhập có nhãn (label + input), dùng cho form auth. */
export default function TextField({
  label,
  type = "text",
  placeholder,
  name,
  labelStyle,
  value,
  onChange,
  required,
  autoComplete,
  disabled,
}: TextFieldProps) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 7 }}>
      <span style={labelStyle ? { ...labelText, ...labelStyle } : labelText}>{label}</span>
      <input
        className="az-input"
        type={type}
        placeholder={placeholder}
        name={name}
        style={inputStyle}
        value={value}
        onChange={onChange}
        required={required}
        autoComplete={autoComplete}
        disabled={disabled}
      />
    </label>
  );
}
