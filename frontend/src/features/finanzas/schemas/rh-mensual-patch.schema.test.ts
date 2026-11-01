/**
 * Contrato PATCH de los RH mensuales (sincronización del conjunto final).
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase (la ejecución
 * consolidada es la fase final de verificación).
 */
import { describe, expect, it } from "vitest";
import {
  rhDelegadoMensualDetalleSchema,
  rhInspectorMensualDetalleSchema,
} from "./recibo-honorario.schema";
import {
  RHDelegadoActualizarInSchema,
  RHDelegadoActualizarItemInSchema,
  RHDelegadoCotizarItemSchema,
} from "./rh-delegado-mensual.schema";
import {
  RHInspectorActualizarInSchema,
  RHInspectorActualizarItemInSchema,
  RHInspectorCotizarItemSchema,
} from "./rh-inspector-mensual.schema";

describe("RHDelegadoActualizarItemInSchema — item del PATCH de delegado", () => {
  it("acepta un item con detalle_id (fila a conservar)", () => {
    const parsed = RHDelegadoActualizarItemInSchema.parse({
      liquidacion_general_id: "lg-1",
      especialidad_revision_id: "esp-1",
      detalle_id: "detalle-1",
      numero_rh: "RH-001",
      periodo: 2026,
      mes: 10,
    });

    expect(parsed.detalle_id).toBe("detalle-1");
  });

  it("acepta un item sin detalle_id (fila a agregar)", () => {
    const parsed = RHDelegadoActualizarItemInSchema.parse({
      liquidacion_general_id: "lg-2",
      especialidad_revision_id: "esp-1",
    });

    expect(parsed.detalle_id).toBeUndefined();
  });

  it("rechaza un item sin liquidacion_general_id", () => {
    const result = RHDelegadoActualizarItemInSchema.safeParse({
      especialidad_revision_id: "esp-1",
    });

    expect(result.success).toBe(false);
  });

  it("rechaza un mes fuera del rango 1-12", () => {
    const result = RHDelegadoActualizarItemInSchema.safeParse({
      liquidacion_general_id: "lg-1",
      especialidad_revision_id: "esp-1",
      mes: 13,
    });

    expect(result.success).toBe(false);
  });
});

describe("RHDelegadoActualizarInSchema — payload completo de sincronización", () => {
  it("acepta el conjunto final de items con y sin detalle_id", () => {
    const parsed = RHDelegadoActualizarInSchema.parse({
      cip: "100001",
      periodo: 2026,
      mes: 10,
      delegado_operacion_id: "operacion-1",
      items: [
        {
          liquidacion_general_id: "lg-1",
          especialidad_revision_id: "esp-1",
          detalle_id: "detalle-1",
        },
        {
          liquidacion_general_id: "lg-2",
          especialidad_revision_id: "esp-1",
        },
      ],
    });

    expect(parsed.items).toHaveLength(2);
    expect(parsed.items[0].detalle_id).toBe("detalle-1");
    expect(parsed.items[1].detalle_id).toBeUndefined();
  });

  it("rechaza un payload sin items", () => {
    const result = RHDelegadoActualizarInSchema.safeParse({
      cip: "100001",
      periodo: 2026,
      mes: 10,
      delegated_operacion_id: "operacion-1",
      items: [],
    });

    expect(result.success).toBe(false);
  });
});

describe("RHInspectorActualizarItemInSchema — item del PATCH de inspector", () => {
  it("acepta una fila persistida identificada por detalle_id y expediente", () => {
    const parsed = RHInspectorActualizarItemInSchema.parse({
      exp_liqui: "EXP-IO-001",
      cantidad_visitas: 2,
      detalle_id: "detalle-insp-1",
    });

    expect(parsed.detalle_id).toBe("detalle-insp-1");
    expect(parsed.exp_liqui).toBe("EXP-IO-001");
  });

  it("acepta una fila nueva identificada por la IO candidata", () => {
    const parsed = RHInspectorActualizarItemInSchema.parse({
      liquidacion_categoria_visitas_id: "lcv-1",
      cantidad_visitas: 1,
    });

    expect(parsed.liquidacion_categoria_visitas_id).toBe("lcv-1");
  });

  it("rechaza una cantidad de visitas menor a 1", () => {
    const result = RHInspectorActualizarItemInSchema.safeParse({
      exp_liqui: "EXP-IO-001",
      cantidad_visitas: 0,
    });

    expect(result.success).toBe(false);
  });
});

describe("RHInspectorActualizarInSchema — payload completo de sincronización", () => {
  it("acepta el conjunto final de items", () => {
    const parsed = RHInspectorActualizarInSchema.parse({
      cip: "200002",
      periodo: 2026,
      mes: 10,
      items: [
        {
          exp_liqui: "EXP-IO-001",
          cantidad_visitas: 2,
          detalle_id: "detalle-insp-1",
        },
      ],
    });

    expect(parsed.items[0].detalle_id).toBe("detalle-insp-1");
  });
});

describe("detalle_id tipado en los contratos de RH mensual", () => {
  it("expone detalle_id en el detalle del listado de RH de delegado", () => {
    const parsed = rhDelegadoMensualDetalleSchema.parse({
      liquidacion_delegado_id: "asignacion-1",
      detalle_id: "detalle-1",
      expediente: "EXP-001",
      imp_bruto: 1000,
    });

    expect(parsed.detalle_id).toBe("detalle-1");
  });

  it("expone detalle_id en el detalle del listado de RH de inspector", () => {
    const parsed = rhInspectorMensualDetalleSchema.parse({
      detalle_id: "detalle-insp-1",
      expediente: "EXP-IO-001",
      nombre_propietario: "Propietario Uno",
      importe_bruto: 1000,
      inspecciones_programadas: 5,
      inspecciones_liquidadas: 2,
      inspecciones_pagadas_hasta_mes_anterior: 1,
      costo_por_inspeccion: 200,
      monto_contribuido: 400,
      saldo_restante: 2,
    });

    expect(parsed.detalle_id).toBe("detalle-insp-1");
  });

  it("expone detalle_id en el item de cotización de delegado e inspector", () => {
    const delegado = RHDelegadoCotizarItemSchema.parse({
      exp_liqui: "EXP-001",
      detalle_id: "detalle-1",
      imp_bruto: 1000,
    });
    const inspector = RHInspectorCotizarItemSchema.parse({
      exp_liqui: "EXP-IO-001",
      liquidacion_inspector_id: "li-1",
      liquidacion_categoria_visitas_id: "lcv-1",
      detalle_id: "detalle-insp-1",
      nombre_propietario: "Propietario Uno",
      importe_bruto: 1000,
      inspecciones_programadas: 5,
      inspecciones_liquidadas: 2,
      inspecciones_pagadas_hasta_mes_anterior: 1,
      costo_por_inspeccion: 200,
      monto_contribuido: 400,
      saldo_disponible: 4,
      saldo_restante: 2,
      // Valores financieros por item (contrato de cotización del RH de inspector).
      sub_total: 1000,
      descuento: 200,
      honorarios: 800,
      tasa_descuento_aplicada: 0.2,
    });

    expect(delegado.detalle_id).toBe("detalle-1");
    expect(inspector.detalle_id).toBe("detalle-insp-1");
  });
});
