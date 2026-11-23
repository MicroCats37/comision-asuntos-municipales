import { describe, expect, it } from "vitest";
import {
  ordenarCandidatasRh,
  ordenarSeleccionRh,
} from "./rh-candidatas-order";

describe("rh-candidatas-order", () => {
  it("ordena las candidatas por número de liquidación ascendente", () => {
    const candidatas = [
      { liquidacion_especifica_numero: 12 },
      { liquidacion_especifica_numero: 3 },
      { liquidacion_especifica_numero: null },
      { liquidacion_especifica_numero: 8 },
    ];

    expect(ordenarCandidatasRh(candidatas)).toEqual([
      { liquidacion_especifica_numero: 3 },
      { liquidacion_especifica_numero: 8 },
      { liquidacion_especifica_numero: 12 },
      { liquidacion_especifica_numero: null },
    ]);
  });

  it("mantiene las filas seleccionadas en el mismo orden", () => {
    const selecciones = [
      { candidate: { liquidacion_especifica_numero: 9 } },
      { candidate: { liquidacion_especifica_numero: 2 } },
    ];

    expect(ordenarSeleccionRh(selecciones)).toEqual([
      { candidate: { liquidacion_especifica_numero: 2 } },
      { candidate: { liquidacion_especifica_numero: 9 } },
    ]);
  });
});
