import { describe, expect, it } from "vitest";

import { now, partOfDay, todayDMY } from "./time";

describe("lib/time", () => {
  it("now() trả 'HH:MM' (2 chữ số : 2 chữ số)", () => {
    expect(now()).toMatch(/^\d{2}:\d{2}$/);
  });

  it("partOfDay() là một trong: sáng | chiều | tối", () => {
    expect(["sáng", "chiều", "tối"]).toContain(partOfDay());
  });

  it("todayDMY() trả 'DD/MM/YYYY'", () => {
    expect(todayDMY()).toMatch(/^\d{2}\/\d{2}\/\d{4}$/);
  });
});
