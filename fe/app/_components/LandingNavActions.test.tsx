import type { ReactNode } from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

// Điều khiển trạng thái đăng nhập trả về từ useAuth.
const mockAuth = vi.fn();
vi.mock("@/app/_providers/AuthProvider", () => ({
  useAuth: () => mockAuth(),
}));

// Stub các phụ thuộc nặng (next/link, các provider) để test tập trung vào NHÁNH hiển thị.
vi.mock("@/app/components/ui/Button", () => ({
  default: ({ href, children }: { href?: string; children?: ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));
vi.mock("@/app/components/ui/Icon", () => ({ default: () => null }));
vi.mock("@/app/components/common/UserMenu", () => ({
  default: () => <div data-testid="user-menu">user-menu</div>,
}));

import LandingNavActions from "./LandingNavActions";

afterEach(() => {
  cleanup();
  mockAuth.mockReset();
});

describe("LandingNavActions — header trang chủ phản ánh trạng thái đăng nhập", () => {
  it("đã đăng nhập → hiện 'Vào chat' + UserMenu, KHÔNG hiện 'Đăng ký'", () => {
    mockAuth.mockReturnValue({ user: { name: "Cookie Test" }, loading: false });
    render(<LandingNavActions />);
    expect(screen.getByText("Vào chat")).toBeTruthy();
    expect(screen.getByTestId("user-menu")).toBeTruthy();
    expect(screen.queryByText("Đăng ký")).toBeNull();
  });

  it("chưa đăng nhập → hiện 'Đăng ký' + 'Hỏi LuminaAi'", () => {
    mockAuth.mockReturnValue({ user: null, loading: false });
    render(<LandingNavActions />);
    expect(screen.getByText("Đăng ký")).toBeTruthy();
    expect(screen.getByText("Hỏi LuminaAi")).toBeTruthy();
    expect(screen.queryByTestId("user-menu")).toBeNull();
  });

  it("đang kiểm tra phiên (loading) → chưa hiện gì (tránh nháy 'Đăng ký')", () => {
    mockAuth.mockReturnValue({ user: null, loading: true });
    render(<LandingNavActions />);
    expect(screen.queryByText("Đăng ký")).toBeNull();
    expect(screen.queryByText("Vào chat")).toBeNull();
  });
});
