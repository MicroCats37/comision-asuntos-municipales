import { describe, expect, it } from "vitest";
import {
  continuidadVisitasFormSchema,
  visitasFormSchema,
} from "./liquidacion-visitas-form.schema";

describe("visitasFormSchema category", () => {
  it.each(["1", "2", "3", "4"])("accepts canonical category %s", (value) => {
    expect(visitasFormSchema.shape.categoria.safeParse(value).success).toBe(
      true,
    );
  });

  it.each(["C1", "C2", "C3", "C4"])("rejects legacy category %s", (value) => {
    expect(visitasFormSchema.shape.categoria.safeParse(value).success).toBe(
      false,
    );
  });
});

describe("continuidadVisitasFormSchema — el bruto declarado", () => {
  it("acepta el bruto declarado de la liquidación previa", () => {
    const result = continuidadVisitasFormSchema.safeParse({
      liquidacion_previa_id: "previa-1",
      total_pagado_previa: 212.6,
    });

    expect(result.success).toBe(true);
  });

  it("acepta un bruto declarado vacío (equivale a 0: no declarado)", () => {
    const result = continuidadVisitasFormSchema.safeParse({
      liquidacion_previa_id: "previa-1",
      total_pagado_previa: "",
    });

    expect(result.success).toBe(true);
  });

  it("rechaza un bruto declarado negativo", () => {
    const result = continuidadVisitasFormSchema.safeParse({
      total_pagado_previa: -1,
    });

    expect(result.success).toBe(false);
  });

  it("rechaza un bruto declarado por encima del máximo del backend", () => {
    const result = continuidadVisitasFormSchema.safeParse({
      total_pagado_previa: 99999999999.99,
    });

    expect(result.success).toBe(false);
  });

  it("el límite de crédito del cliente ya no bloquea el formulario", () => {
    // El invariante IV-5 del servidor es la única barrera (responde 400).
    const result = continuidadVisitasFormSchema.safeParse({
      subtotal_credito: 501,
      valor_maximo_credito: 500,
    });

    expect(result.success).toBe(true);
  });
});
