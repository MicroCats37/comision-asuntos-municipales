/**
 * Proyección a fila de tabla — Fase 5 (números de revisión repetidos).
 *
 * El número de revisión es una ETIQUETA editable: dos liquidaciones hermanas
 * pueden compartir el mismo número (por ejemplo dos revisiones 3). La
 * proyección a fila NO puede deduplicar ni elegir un hermano "canónico":
 * cada liquidación conserva su propia etiqueta.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase.
 */
import { describe, expect, it } from "vitest";
import {
  type LiquidacionGeneralLike,
  mapLiquidacionRow,
} from "./mapLiquidacionRow";

function base(id: string, numeroRevision: number): LiquidacionGeneralLike {
  return {
    id,
    numero_revision: numeroRevision,
    fecha_registro: "2026-01-15",
    proyecto: {
      nombre_propietario: "PROPIETARIO",
      direccion: "AV. PRINCIPAL 123",
    },
  };
}

describe("mapLiquidacionRow — hermanos con el mismo número de revisión", () => {
  it("mantiene DOS filas distintas con la misma etiqueta de revisión", () => {
    const rowA = mapLiquidacionRow("edificacion", base("hermano-a", 3), 10);
    const rowB = mapLiquidacionRow("edificacion", base("hermano-b", 3), 11);

    expect(rowA.id).toBe("hermano-a");
    expect(rowB.id).toBe("hermano-b");
    expect(rowA.id).not.toBe(rowB.id);
  });

  it("cada fila muestra SU PROPIA etiqueta de revisión (sin deduplicar)", () => {
    const rowA = mapLiquidacionRow("edificacion", base("hermano-a", 3), 10);
    const rowB = mapLiquidacionRow("edificacion", base("hermano-b", 3), 11);
    const rowC = mapLiquidacionRow("edificacion", base("otra", 5), 12);

    expect(rowA.numeroRevision).toBe(3);
    expect(rowB.numeroRevision).toBe(3);
    expect(rowC.numeroRevision).toBe(5);
  });

  it("no inventa una revisión cuando el dato viene vacío", () => {
    const row = mapLiquidacionRow(
      "edificacion",
      { ...base("sin-revision", 1), numero_revision: null },
      10,
    );

    expect(row.numeroRevision).toBeNull();
  });
});
