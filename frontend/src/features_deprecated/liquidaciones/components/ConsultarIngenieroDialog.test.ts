/**
 * Unit tests for ConsultarIngenieroDialog CIP sanitization helpers.
 */
import { describe, it, expect } from "vitest";
import {
  sanitizeCipInput,
  isValidCip,
} from "../utils/cip-utils";

describe("sanitizeCipInput", () => {
  it("removes non-digit characters", () => {
    expect(sanitizeCipInput("123abc")).toBe("123");
    expect(sanitizeCipInput("12-34-56")).toBe("123456");
    expect(sanitizeCipInput("abc")).toBe("");
    expect(sanitizeCipInput("12ab34cd56ef")).toBe("123456");
  });

  it("limits to 6 characters", () => {
    expect(sanitizeCipInput("1234567")).toBe("123456");
    expect(sanitizeCipInput("1234567890")).toBe("123456");
  });

  it("handles empty string", () => {
    expect(sanitizeCipInput("")).toBe("");
  });

  it("preserves valid digit-only input", () => {
    expect(sanitizeCipInput("123456")).toBe("123456");
    expect(sanitizeCipInput("000000")).toBe("000000");
  });

  it("handles special characters", () => {
    expect(sanitizeCipInput("123.456")).toBe("123456");
    expect(sanitizeCipInput("123,456")).toBe("123456");
    expect(sanitizeCipInput("123 456")).toBe("123456");
    expect(sanitizeCipInput("12-34-56")).toBe("123456");
  });

  it("handles mixed valid and invalid", () => {
    expect(sanitizeCipInput("12abc34!@#56")).toBe("123456");
  });
});

describe("isValidCip", () => {
  it("returns true for exactly 6 digits", () => {
    expect(isValidCip("123456")).toBe(true);
    expect(isValidCip("000000")).toBe(true);
    expect(isValidCip("999999")).toBe(true);
  });

  it("returns false for less than 6 digits", () => {
    expect(isValidCip("")).toBe(false);
    expect(isValidCip("1")).toBe(false);
    expect(isValidCip("12")).toBe(false);
    expect(isValidCip("123")).toBe(false);
    expect(isValidCip("1234")).toBe(false);
    expect(isValidCip("12345")).toBe(false);
  });

  it("returns false for more than 6 digits", () => {
    expect(isValidCip("1234567")).toBe(false);
    expect(isValidCip("1234567890")).toBe(false);
  });

  it("returns false for non-digit strings", () => {
    expect(isValidCip("abcdef")).toBe(false);
    expect(isValidCip("12-34-56")).toBe(false);
    expect(isValidCip("12ab34")).toBe(false);
  });
});
