import { describe, expect, it } from "vitest";
import {
  esNumeroRevisionValido,
  MAX_REVISIONES,
  NUMERO_REVISION_FIJA,
  NUMERO_REVISION_OPTIONS,
  NUMERO_REVISION_PERMITIDOS,
  resolveNumeroRevisionInicial,
  toNumeroRevision,
} from "./numeroRevision";

describe("numeroRevision — espejo del contrato backend", () => {
  it("expone el mismo conjunto permitido y máximo que el backend", () => {
    expect([...NUMERO_REVISION_PERMITIDOS]).toEqual([1, 3, 5]);
    expect(MAX_REVISIONES).toBe(5);
    expect(NUMERO_REVISION_FIJA).toBe(1);
  });

  it("ofrece exactamente una opción por número permitido", () => {
    expect(NUMERO_REVISION_OPTIONS.map((opcion) => opcion.value)).toEqual([
      1, 3, 5,
    ]);
  });

  it("acepta solo los valores del conjunto permitido", () => {
    expect(esNumeroRevisionValido(1)).toBe(true);
    expect(esNumeroRevisionValido(3)).toBe(true);
    expect(esNumeroRevisionValido(5)).toBe(true);

    for (const invalido of [0, 2, 4, 6, -1, 1.5, "3", null, undefined]) {
      expect(esNumeroRevisionValido(invalido)).toBe(false);
    }
  });

  it("normaliza el valor que devuelve la API (number | string)", () => {
    expect(toNumeroRevision("3")).toBe(3);
    expect(toNumeroRevision(5)).toBe(5);
    expect(toNumeroRevision("7")).toBeUndefined();
    expect(toNumeroRevision(undefined)).toBeUndefined();
    expect(toNumeroRevision("")).toBeUndefined();
  });
});

describe("resolveNumeroRevisionInicial — valor con el que se abre el formulario", () => {
  it("inicializa en 1 para create", () => {
    expect(resolveNumeroRevisionInicial("create")).toBe(1);
  });

  it("inicializa en 1 para relacionada (no incrementa la revisión)", () => {
    expect(resolveNumeroRevisionInicial("relacionada", 3)).toBe(1);
    expect(resolveNumeroRevisionInicial("relacionada", 5)).toBe(1);
  });

  it("inicializa en previa + 2 para nueva-revision (cadena 1 → 3 → 5)", () => {
    expect(resolveNumeroRevisionInicial("nueva-revision", 1)).toBe(3);
    expect(resolveNumeroRevisionInicial("nueva-revision", 3)).toBe(5);
  });

  it("acota nueva-revision al máximo permitido desde una previa en revisión 5", () => {
    // previa 5 + 2 = 7, que no pertenece al conjunto {1, 3, 5} → se queda en 5
    expect(resolveNumeroRevisionInicial("nueva-revision", 5)).toBe(5);
  });

  it("conserva el valor almacenado en edit", () => {
    expect(resolveNumeroRevisionInicial("edit", 5)).toBe(5);
    expect(resolveNumeroRevisionInicial("edit", "3")).toBe(3);
    expect(resolveNumeroRevisionInicial("edit", 1)).toBe(1);
  });

  it("cae en la revisión fija cuando el valor de origen no es válido", () => {
    expect(resolveNumeroRevisionInicial("edit", 7)).toBe(1);
    expect(resolveNumeroRevisionInicial("edit", undefined)).toBe(1);
    expect(resolveNumeroRevisionInicial("nueva-revision", undefined)).toBe(1);
  });
});
