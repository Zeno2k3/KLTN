import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import CitationChip from "./CitationChip";

afterEach(cleanup);

describe("CitationChip", () => {
  it("hiện nhãn + icon; bấm → gọi onClick một lần", () => {
    const onClick = vi.fn();
    render(<CitationChip label="Bảng học phí" onClick={onClick} />);
    const btn = screen.getByRole("button", { name: /Bảng học phí/ });
    expect(btn.querySelector("svg")).toBeTruthy(); // icon file-text
    fireEvent.click(btn);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("disabled → không phải button; có title = đoạn trích", () => {
    render(<CitationChip label="x.pdf" title="đoạn trích" disabled />);
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.getByText("x.pdf")).toBeTruthy();
    expect(screen.getByTitle("đoạn trích")).toBeTruthy();
  });
});
