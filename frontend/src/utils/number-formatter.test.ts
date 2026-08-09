/**
 * Unit tests for number-formatter utilities.
 */
import { describe, it, expect } from "vitest";
import {
  trimTrailingZeros,
  formatDecimalPercent,
  formatCurrencyTrimmed,
} from "./number-formatter";

describe("trimTrailingZeros", () => {
  it("trims trailing zeros from integer-like decimals", () => {
    expect(trimTrailingZeros(5.0)).toBe("5");
    expect(trimTrailingZeros(5.000)).toBe("5");
    expect(trimTrailingZeros(5.0000)).toBe("5");
    expect(trimTrailingZeros(2.0000)).toBe("2");
    expect(trimTrailingZeros(100.000)).toBe("100");
  });

  it("trims trailing zeros while preserving significant digits", () => {
    expect(trimTrailingZeros(5.001)).toBe("5.001");
    expect(trimTrailingZeros(5.5000)).toBe("5.5");
    expect(trimTrailingZeros(5.5500)).toBe("5.55");
    expect(trimTrailingZeros(5.5550)).toBe("5.555");
    expect(trimTrailingZeros(0.0500)).toBe("0.05");
    expect(trimTrailingZeros(0.0501)).toBe("0.0501");
  });

  it("respects maxDecimals cap", () => {
    expect(trimTrailingZeros(1.123456789, 4)).toBe("1.1235");
    expect(trimTrailingZeros(1.123456789, 2)).toBe("1.12");
  });

  it("handles string input", () => {
    expect(trimTrailingZeros("5.000")).toBe("5");
    expect(trimTrailingZeros("5.500")).toBe("5.5");
  });

  it("returns non-numeric strings as-is", () => {
    expect(trimTrailingZeros("abc" as unknown as number)).toBe("abc");
  });

  it("handles edge cases", () => {
    expect(trimTrailingZeros(0)).toBe("0");
    expect(trimTrailingZeros(0.0)).toBe("0");
    expect(trimTrailingZeros(-5.000)).toBe("-5");
    expect(trimTrailingZeros(-5.500)).toBe("-5.5");
  });
});

describe("formatDecimalPercent", () => {
  it("converts decimal fraction to percentage with trimmed zeros", () => {
    expect(formatDecimalPercent(0.05)).toBe("5%");
    expect(formatDecimalPercent(0.0500)).toBe("5%");
    expect(formatDecimalPercent(0.05000)).toBe("5%");
    expect(formatDecimalPercent(0.020000)).toBe("2%");
  });

  it("preserves meaningful decimal places", () => {
    expect(formatDecimalPercent(0.051)).toBe("5.1%");
    expect(formatDecimalPercent(0.055)).toBe("5.5%");
    expect(formatDecimalPercent(0.0555)).toBe("5.55%");
    expect(formatDecimalPercent(0.05555)).toBe("5.555%");
    expect(formatDecimalPercent(0.001)).toBe("0.1%");
  });

  it("handles null and undefined", () => {
    expect(formatDecimalPercent(null)).toBe("—");
    expect(formatDecimalPercent(undefined)).toBe("—");
  });

  it("handles whole percentages", () => {
    expect(formatDecimalPercent(0.18)).toBe("18%");
    expect(formatDecimalPercent(0.5)).toBe("50%");
    expect(formatDecimalPercent(1.0)).toBe("100%");
  });

  it("respects maxDecimals cap", () => {
    expect(formatDecimalPercent(0.123456789, 2)).toBe("12.35%");
  });

  it("handles percentage_minimo_uit style values", () => {
    // e.g., 0.005 * 100 = 0.5%
    expect(formatDecimalPercent(0.005)).toBe("0.5%");
    // e.g., 0.01 * 100 = 1%
    expect(formatDecimalPercent(0.01)).toBe("1%");
    // e.g., 0.1 * 100 = 10%
    expect(formatDecimalPercent(0.1)).toBe("10%");
  });
});

describe("formatCurrencyTrimmed", () => {
  it("formats currency with trailing zeros trimmed", () => {
    expect(formatCurrencyTrimmed(5.0)).toBe("S/ 5");
    expect(formatCurrencyTrimmed(5.0000)).toBe("S/ 5");
    expect(formatCurrencyTrimmed(5.5000)).toBe("S/ 5.5");
    expect(formatCurrencyTrimmed(5.001)).toBe("S/ 5.001");
  });

  it("handles null and undefined", () => {
    expect(formatCurrencyTrimmed(null)).toBe("—");
    expect(formatCurrencyTrimmed(undefined)).toBe("—");
  });

  it("handles standard currency amounts", () => {
    expect(formatCurrencyTrimmed(1234.56)).toBe("S/ 1234.56");
    expect(formatCurrencyTrimmed(0.05)).toBe("S/ 0.05");
    expect(formatCurrencyTrimmed(100.0)).toBe("S/ 100");
  });

  it("respects maxDecimals cap", () => {
    expect(formatCurrencyTrimmed(1.123456789, 2)).toBe("S/ 1.12");
  });
});
