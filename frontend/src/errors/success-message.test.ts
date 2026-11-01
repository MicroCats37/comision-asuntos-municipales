import { describe, expect, it } from "vitest";
import {
  clearSuccessMessage,
  extractSuccessMessage,
  peekSuccessMessage,
  recordSuccessMessage,
} from "./success-message";

describe("extractSuccessMessage", () => {
  it("returns the top-level envelope message", () => {
    expect(
      extractSuccessMessage({
        success: true,
        data: { id: 1 },
        message: "Recibo de delegado creado correctamente.",
      }),
    ).toBe("Recibo de delegado creado correctamente.");
  });

  it("falls back to the message nested in data", () => {
    expect(
      extractSuccessMessage({
        success: true,
        data: { id: 1, message: "Recibo de delegado eliminado correctamente." },
      }),
    ).toBe("Recibo de delegado eliminado correctamente.");
  });

  it("prefers the top-level message when both are present", () => {
    expect(
      extractSuccessMessage({
        message: "Nivel superior.",
        data: { message: "Anidado." },
      }),
    ).toBe("Nivel superior.");
  });

  it("returns undefined when there is no message", () => {
    expect(
      extractSuccessMessage({ success: true, data: { id: 1 } }),
    ).toBeUndefined();
    expect(extractSuccessMessage({ message: "" })).toBeUndefined();
    expect(extractSuccessMessage({ message: 42 })).toBeUndefined();
    expect(extractSuccessMessage(null)).toBeUndefined();
    expect(extractSuccessMessage(undefined)).toBeUndefined();
    expect(extractSuccessMessage("texto")).toBeUndefined();
  });

  it("ignores a nested message when data is not an object", () => {
    expect(extractSuccessMessage({ data: ["a"] })).toBeUndefined();
  });
});

describe("success message registry", () => {
  it("publishes, reads and clears the last success message", () => {
    clearSuccessMessage();
    expect(peekSuccessMessage()).toBeUndefined();

    recordSuccessMessage("Recibo creado correctamente.");
    expect(peekSuccessMessage()).toBe("Recibo creado correctamente.");

    clearSuccessMessage();
    expect(peekSuccessMessage()).toBeUndefined();
  });

  it("ignores blank messages", () => {
    recordSuccessMessage("   ");
    expect(peekSuccessMessage()).toBeUndefined();
  });
});
