import { describe, expect, it } from "vitest";
import { getLiquidacionesPreviasEndpoint } from "./useLiquidacionesPrevias";

describe("getLiquidacionesPreviasEndpoint", () => {
  it.each([
    ["EDIFICACION", "/liquidaciones/edificaciones/"],
    ["HABILITACION_URBANA", "/liquidaciones/habilitacion-urbana/"],
    ["MECANICA_SUELOS", "/liquidaciones/mecanica-suelos/"],
    ["TALUDES", "/liquidaciones/taludes/"],
    ["IMPACTO_VIAL", "/liquidaciones/impacto-vial/"],
  ])("maps %s to its paginated list", (tipo, endpoint) => {
    expect(getLiquidacionesPreviasEndpoint(tipo)).toBe(endpoint);
  });

  it("rejects unsupported or missing types", () => {
    expect(getLiquidacionesPreviasEndpoint()).toBeUndefined();
    expect(getLiquidacionesPreviasEndpoint("INSPECCION_OBRA")).toBeUndefined();
  });
});
