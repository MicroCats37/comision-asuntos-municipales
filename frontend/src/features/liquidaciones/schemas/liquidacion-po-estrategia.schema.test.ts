/**
 * Union discriminada de estrategias de cotización PO (Edificaciones).
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la ejecución de
 * la suite queda reservada para el Módulo 8 de la verificación final.
 *
 * Contrato espejo:
 *   backend/modules/liquidaciones/presentation/schemas/liquidacion_especifico/
 *   liquidacion_edificaciones_schemas.py → LiquidacionEdificacionesEstrategiaIn
 */
import { describe, expect, it } from "vitest";
import {
  construirEstrategiaPayload,
  ESTRATEGIA_HABILITADAS,
  ESTRATEGIA_NORMAL,
  ESTRATEGIA_TOTAL,
  ESTRATEGIAS_COTIZACION_PO,
  edificacionesEstrategiaSchema,
  esEstrategiaValida,
  MENSAJE_TOTAL_EXPLICITO_POSITIVO,
  MENSAJE_TOTAL_EXPLICITO_REQUERIDO,
  MENSAJE_VALOR_DECLARADO_POSITIVO,
  MENSAJE_VALOR_DECLARADO_REQUERIDO,
  normalizarPayloadEstrategia,
  parsePayloadEstrategia,
  validarDatosDeEstrategia,
} from "./liquidacion-po-estrategia.schema";

const TARIFAS = [
  {
    tarifa_porcentaje_obra_id: "tarifa-1",
    especialidad_id: "esp-1",
  },
];

describe("estrategias PO — exactamente tres modos canónicos", () => {
  it("expone tres estrategias y ningún alias", () => {
    expect(ESTRATEGIAS_COTIZACION_PO).toHaveLength(3);
    expect(ESTRATEGIAS_COTIZACION_PO).toEqual([
      "NORMAL_SELECCIONADAS",
      "TARIFA_HABILITADAS_PARTICIPANTES",
      "TOTAL_EXPLICITO",
    ]);
  });

  it("rechaza un cuarto modo o un alias", () => {
    expect(esEstrategiaValida("MODO_CUSTOM")).toBe(false);
    expect(esEstrategiaValida("TOTAL")).toBe(false);
    expect(esEstrategiaValida("NORMAL")).toBe(false);
    expect(esEstrategiaValida(undefined)).toBe(false);
  });
});

describe("union discriminada — payloads válidos por estrategia", () => {
  it("acepta NORMAL_SELECCIONADAS con valor declarado", () => {
    const resultado = edificacionesEstrategiaSchema.safeParse({
      estrategia_cotizacion: ESTRATEGIA_NORMAL,
      datos: { valor_declarado: 1000000 },
      tipo_tramite: "OBRA_NUEVA",
      tarifas: TARIFAS,
    });
    expect(resultado.success).toBe(true);
  });

  it("acepta TARIFA_HABILITADAS_PARTICIPANTES con valor declarado", () => {
    const resultado = edificacionesEstrategiaSchema.safeParse({
      estrategia_cotizacion: ESTRATEGIA_HABILITADAS,
      datos: { valor_declarado: 1000000 },
      tarifas: TARIFAS,
    });
    expect(resultado.success).toBe(true);
  });

  it("acepta TOTAL_EXPLICITO con valor informativo y total final", () => {
    const resultado = edificacionesEstrategiaSchema.safeParse({
      estrategia_cotizacion: ESTRATEGIA_TOTAL,
      datos: { valor_declarado: 1000000, total_explicito: 177 },
      tarifas: TARIFAS,
    });
    expect(resultado.success).toBe(true);
  });
});

describe("union discriminada — campos exigidos y prohibidos", () => {
  it("rechaza TOTAL_EXPLICITO sin valor declarado", () => {
    const resultado = edificacionesEstrategiaSchema.safeParse({
      estrategia_cotizacion: ESTRATEGIA_TOTAL,
      datos: { total_explicito: 177 },
      tarifas: TARIFAS,
    });
    expect(resultado.success).toBe(false);
  });

  it("rechaza NORMAL_SELECCIONADAS con total explícito (dato ajeno)", () => {
    const resultado = edificacionesEstrategiaSchema.safeParse({
      estrategia_cotizacion: ESTRATEGIA_NORMAL,
      datos: { valor_declarado: 1000000, total_explicito: 177 },
      tarifas: TARIFAS,
    });
    expect(resultado.success).toBe(false);
  });

  it("rechaza TARIFA_HABILITADAS_PARTICIPANTES con total explícito", () => {
    const resultado = edificacionesEstrategiaSchema.safeParse({
      estrategia_cotizacion: ESTRATEGIA_HABILITADAS,
      datos: { valor_declarado: 1000000, total_explicito: 177 },
      tarifas: TARIFAS,
    });
    expect(resultado.success).toBe(false);
  });

  it("rechaza una estrategia incompleta (falta el dato que exige)", () => {
    const resultado = edificacionesEstrategiaSchema.safeParse({
      estrategia_cotizacion: ESTRATEGIA_TOTAL,
      datos: {},
      tarifas: TARIFAS,
    });
    expect(resultado.success).toBe(false);
  });

  it("rechaza un discriminador desconocido", () => {
    const resultado = edificacionesEstrategiaSchema.safeParse({
      estrategia_cotizacion: "MODO_CUSTOM",
      datos: { valor_declarado: 1000000 },
      tarifas: TARIFAS,
    });
    expect(resultado.success).toBe(false);
  });

  it("rechaza campos desconocidos en `datos` (extra forbid)", () => {
    const resultado = edificacionesEstrategiaSchema.safeParse({
      estrategia_cotizacion: ESTRATEGIA_NORMAL,
      datos: { valor_declarado: 1000000, porcentaje_custom: 5 },
      tarifas: TARIFAS,
    });
    expect(resultado.success).toBe(false);
  });
});

describe("normalización — discriminador opcional de NORMAL_SELECCIONADAS", () => {
  it("materializa NORMAL_SELECCIONADAS cuando el discriminador no viene", () => {
    const normalizado = normalizarPayloadEstrategia({
      datos: { valor_declarado: 1000000 },
      tarifas: TARIFAS,
    });
    expect(normalizado.estrategia_cotizacion).toBe(ESTRATEGIA_NORMAL);
  });

  it("parsea el payload vigente sin discriminador (byte-compatible)", () => {
    const resultado = parsePayloadEstrategia({
      datos: { valor_declarado: 1000000 },
      tarifas: TARIFAS,
    });
    expect(resultado.estrategia_cotizacion).toBe(ESTRATEGIA_NORMAL);
    if (resultado.estrategia_cotizacion !== ESTRATEGIA_NORMAL) {
      throw new Error(
        "La estrategia normalizada debe ser NORMAL_SELECCIONADAS",
      );
    }
    expect(resultado.datos.valor_declarado).toBe(1000000);
  });

  it("no materializa NORMAL_SELECCIONADAS sobre un payload de TOTAL", () => {
    // Sin discriminador el payload se degrada a NORMAL_SELECCIONADAS, que
    // exige `valor_declarado`: el parse falla en lugar de adivinar la
    // estrategia.
    expect(() =>
      parsePayloadEstrategia({
        datos: { total_explicito: 177 },
        tarifas: TARIFAS,
      }),
    ).toThrow();
  });
});

describe("builder — payload discriminado por estrategia", () => {
  it("NORMAL_SELECCIONADAS envía solo el valor declarado", () => {
    const payload = construirEstrategiaPayload({
      estrategia: ESTRATEGIA_NORMAL,
      valor_declarado: 1000000,
      total_explicito: 177,
      tipo_tramite: "OBRA_NUEVA",
      tarifas: TARIFAS,
    });
    expect(payload.estrategia_cotizacion).toBe(ESTRATEGIA_NORMAL);
    expect(payload.datos).toEqual({ valor_declarado: 1000000 });
    expect(payload.datos).not.toHaveProperty("total_explicito");
    expect(payload.tipo_tramite).toBe("OBRA_NUEVA");
  });

  it("TARIFA_HABILITADAS_PARTICIPANTES envía solo el valor declarado", () => {
    const payload = construirEstrategiaPayload({
      estrategia: ESTRATEGIA_HABILITADAS,
      valor_declarado: 1000000,
      total_explicito: 177,
      tarifas: TARIFAS,
    });
    expect(payload.estrategia_cotizacion).toBe(ESTRATEGIA_HABILITADAS);
    expect(payload.datos).toEqual({ valor_declarado: 1000000 });
    expect(payload.datos).not.toHaveProperty("total_explicito");
  });

  it("TOTAL_EXPLICITO envía el valor informativo y el total final", () => {
    const payload = construirEstrategiaPayload({
      estrategia: ESTRATEGIA_TOTAL,
      valor_declarado: 1000000,
      total_explicito: 177,
      tarifas: TARIFAS,
    });
    expect(payload.estrategia_cotizacion).toBe(ESTRATEGIA_TOTAL);
    expect(payload.datos).toEqual({
      valor_declarado: 1000000,
      total_explicito: 177,
    });
  });

  it("el payload construido por el builder es aceptado por la union", () => {
    const resultado = edificacionesEstrategiaSchema.safeParse(
      construirEstrategiaPayload({
        estrategia: ESTRATEGIA_TOTAL,
        valor_declarado: 1000000,
        total_explicito: 177,
        tipo_tramite: "OBRA_NUEVA",
        tarifas: TARIFAS,
      }),
    );
    expect(resultado.success).toBe(true);
  });
});

describe("validación por estrategia", () => {
  it("NORMAL_SELECCIONADAS exige valor declarado", () => {
    const issues = validarDatosDeEstrategia(ESTRATEGIA_NORMAL, {});
    expect(issues).toEqual([
      { path: "valor_declarado", message: MENSAJE_VALOR_DECLARADO_REQUERIDO },
    ]);
  });

  it("NORMAL_SELECCIONADAS rechaza el valor declarado no positivo", () => {
    const issues = validarDatosDeEstrategia(ESTRATEGIA_NORMAL, {
      valor_declarado: 0,
    });
    expect(issues).toEqual([
      { path: "valor_declarado", message: MENSAJE_VALOR_DECLARADO_POSITIVO },
    ]);
  });

  it("TOTAL_EXPLICITO exige valor declarado y total final", () => {
    const issues = validarDatosDeEstrategia(ESTRATEGIA_TOTAL, {});
    expect(issues).toEqual([
      { path: "valor_declarado", message: MENSAJE_VALOR_DECLARADO_REQUERIDO },
      { path: "total_explicito", message: MENSAJE_TOTAL_EXPLICITO_REQUERIDO },
    ]);
  });

  it("TOTAL_EXPLICITO rechaza el total no positivo", () => {
    const issues = validarDatosDeEstrategia(ESTRATEGIA_TOTAL, {
      valor_declarado: 1000000,
      total_explicito: -1,
    });
    expect(issues).toEqual([
      { path: "total_explicito", message: MENSAJE_TOTAL_EXPLICITO_POSITIVO },
    ]);
  });

  it("TOTAL_EXPLICITO rechaza el valor declarado no positivo", () => {
    const issues = validarDatosDeEstrategia(ESTRATEGIA_TOTAL, {
      valor_declarado: 0,
      total_explicito: 177,
    });
    expect(issues).toEqual([
      { path: "valor_declarado", message: MENSAJE_VALOR_DECLARADO_POSITIVO },
    ]);
  });

  it("NORMAL_SELECCIONADAS ignora el total explícito residual", () => {
    const issues = validarDatosDeEstrategia(ESTRATEGIA_NORMAL, {
      valor_declarado: 1000,
      total_explicito: 0,
    });
    expect(issues).toEqual([]);
  });
});
