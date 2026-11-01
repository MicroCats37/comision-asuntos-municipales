/**
 * rh-porcentaje — conversión fracción decimal → porcentaje.
 *
 * El backend expone las tasas cotizadas como fracción decimal (ej. `0.20`).
 * Este helper es el ÚNICO punto de conversión: garantiza que la fracción se
 * convierta UNA sola vez (y no aparezca `0.20%` en lugar de `20%`).
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase (la ejecución
 * consolidada es la fase final de verificación).
 */
import { describe, expect, it } from "vitest";
import {
  etiquetaConPorcentaje,
  formatPorcentaje,
  toPercent,
} from "./rh-porcentaje";

describe("toPercent", () => {
  it("convierte la fracción decimal a su valor porcentual", () => {
    expect(toPercent(0.2)).toBe(20);
    expect(toPercent(0.25)).toBe(25);
    expect(toPercent(0.05)).toBe(5);
  });

  it("devuelve null cuando la tasa no está disponible", () => {
    expect(toPercent(null)).toBeNull();
    expect(toPercent(undefined)).toBeNull();
  });
});

describe("formatPorcentaje", () => {
  it("formatea 0.20 como 20%", () => {
    expect(formatPorcentaje(0.2)).toBe("20%");
  });

  it("nunca muestra la fracción como porcentaje (0.20%)", () => {
    expect(formatPorcentaje(0.2)).not.toBe("0.20%");
  });

  it("convierte la fracción una sola vez (no 2000%)", () => {
    expect(formatPorcentaje(0.2)).not.toBe("2000%");
  });

  it("respeta los decimales solicitados", () => {
    expect(formatPorcentaje(0.2, 2)).toBe("20.00%");
    expect(formatPorcentaje(0.155, 1)).toBe("15.5%");
    expect(formatPorcentaje(0.25)).toBe("25%");
  });

  it("devuelve null cuando la tasa no está disponible", () => {
    expect(formatPorcentaje(null)).toBeNull();
    expect(formatPorcentaje(undefined)).toBeNull();
  });
});

describe("etiquetaConPorcentaje", () => {
  it("añade el porcentaje cotizado al rótulo del encabezado", () => {
    expect(etiquetaConPorcentaje("Descuento", 0.2)).toBe("Descuento (20%)");
    expect(etiquetaConPorcentaje("Renta CIP", 0.25)).toBe("Renta CIP (25%)");
  });

  it("deja el rótulo intacto cuando no hay tasa", () => {
    expect(etiquetaConPorcentaje("Descuento", null)).toBe("Descuento");
    expect(etiquetaConPorcentaje("Descuento", undefined)).toBe("Descuento");
  });

  it("no duplica la conversión en el rótulo", () => {
    expect(etiquetaConPorcentaje("Descuento", 0.2)).not.toContain("2000%");
  });
});
