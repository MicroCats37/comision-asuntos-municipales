/**
 * rh-periodo — helpers de período (YYYY-MM) de los wizards RH mensuales.
 *
 * Cubre el valor inicial (MES CALENDARIO ANTERIOR al actual), el rollover de
 * año (enero → diciembre del año previo) y las validaciones de parseo y de
 * período futuro.
 */
import { describe, expect, it } from "vitest";

import {
  getPreviousPeriodParts,
  isFutureRhPeriod,
  parseRhPeriod,
} from "./rh-periodo";

describe("getPreviousPeriodParts", () => {
  it("devuelve el mes calendario anterior en un mes intermedio", () => {
    const partes = getPreviousPeriodParts(new Date(2026, 10, 4)); // 4 nov 2026

    expect(partes.rhPeriod).toBe("2026-10");
    expect(partes.year).toBe("2026");
    expect(partes.month).toBe("10");
  });

  it("hace rollover de año en enero → diciembre del año previo", () => {
    const partes = getPreviousPeriodParts(new Date(2026, 0, 15)); // 15 ene 2026

    expect(partes.rhPeriod).toBe("2025-12");
    expect(partes.year).toBe("2025");
    expect(partes.month).toBe("12");
  });

  it("devuelve noviembre cuando el mes actual es diciembre", () => {
    const partes = getPreviousPeriodParts(new Date(2026, 11, 31)); // 31 dic 2026

    expect(partes.rhPeriod).toBe("2026-11");
  });
});

describe("parseRhPeriod", () => {
  it("parsea un período válido", () => {
    expect(parseRhPeriod("2026-10")).toEqual({ periodo: 2026, mes: 10 });
  });

  it("devuelve null para formatos inválidos", () => {
    expect(parseRhPeriod("2026")).toBeNull();
    expect(parseRhPeriod("2026-13")).toBeNull();
    expect(parseRhPeriod("")).toBeNull();
    expect(parseRhPeriod(null)).toBeNull();
  });
});

describe("isFutureRhPeriod", () => {
  const now = new Date(2026, 10, 4); // 4 nov 2026

  it("detecta los períodos posteriores al mes actual", () => {
    expect(isFutureRhPeriod(2026, 12, now)).toBe(true);
    expect(isFutureRhPeriod(2027, 1, now)).toBe(true);
  });

  it("permite el mes actual y los anteriores", () => {
    expect(isFutureRhPeriod(2026, 11, now)).toBe(false);
    expect(isFutureRhPeriod(2026, 10, now)).toBe(false);
    expect(isFutureRhPeriod(2025, 12, now)).toBe(false);
  });
});
