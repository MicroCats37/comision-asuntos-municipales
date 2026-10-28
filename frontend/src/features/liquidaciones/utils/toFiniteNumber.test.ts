import { describe, expect, it } from "vitest";
import { toFiniteNumber } from "./toFiniteNumber";

describe("toFiniteNumber", () => {
  it("normalizes numeric API strings used as form initial data", () => {
    expect(toFiniteNumber("100000.00")).toBe(100000);
    expect(toFiniteNumber("125.50")).toBe(125.5);
  });

  it("keeps numbers and rejects empty or invalid values", () => {
    expect(toFiniteNumber(42.25)).toBe(42.25);
    expect(toFiniteNumber("")).toBeUndefined();
    expect(toFiniteNumber("invalid")).toBeUndefined();
  });
});
