import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

// Smoke test: chứng minh stack vitest + jsdom + React 19 + testing-library hoạt động.
// Dùng component nội tuyến để không phụ thuộc import của app (vd next/link).
function Greeting({ name }: { name: string }) {
  return <p>Xin chào {name}</p>;
}

describe("vitest + jsdom + React", () => {
  it("render được component React trong jsdom", () => {
    render(<Greeting name="phụ huynh" />);
    expect(screen.getByText(/Xin chào phụ huynh/)).toBeTruthy();
  });
});
