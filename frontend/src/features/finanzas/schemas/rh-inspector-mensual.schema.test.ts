/**
 * rh-inspector-mensual.schema — contrato de cotización del RH de inspector.
 *
 * Verifica que el item de la cotización exponga los valores financieros
 * calculados (subtotal, descuento, honorarios) y la tasa cotizada, manteniendo
 * la convención del backend: la tasa es una fracción decimal.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase (la ejecución
 * consolidada es la fase final de verificación).
 */
import { describe, expect, it } from "vitest";
import {
  RHInspectorCotizarItemSchema,
  RHInspectorCotizarSchema,
} from "./rh-inspector-mensual.schema";

const item = {
  exp_liqui: "EXP-001",
  liquidacion_inspector_id: "li-1",
  liquidacion_categoria_visitas_id: "lcv-1",
  nombre_propietario: "Propietario Uno",
  importe_bruto: 2000,
  inspecciones_programadas: 4,
  inspecciones_liquidadas: 2,
  inspecciones_pagadas_hasta_mes_anterior: 1,
  costo_por_inspeccion: 500,
  monto_contribuido: 1000,
  saldo_disponible: 3,
  saldo_restante: 1,
  sub_total: 1000,
  descuento: 200,
  honorarios: 800,
  tasa_descuento_aplicada: 0.2,
};

const cotizacion = {
  inspector: {
    id: "inspector-1",
    nombre_completo: "Inspector Uno",
    cip: "100001",
    dni: "100001",
  },
  periodo: 2026,
  mes: 10,
  items: [item],
  totales: {
    sub_total: 1000,
    descuento: 200,
    honorarios: 800,
    tasa_descuento_aplicada: 0.2,
  },
  escala_descuento_id: "escala-1",
  variables_calculo: {
    escala_id: "escala-1",
    escala_nombre: "Escala 2026",
    rango_aplicado: {
      monto_minimo: 8000,
      monto_maximo: 15000,
      porcentaje_descuento: 0.2,
    },
  },
};

describe("RHInspectorCotizarItemSchema", () => {
  it("expone el subtotal, el descuento y los honorarios del item", () => {
    const parsed = RHInspectorCotizarItemSchema.parse(item);

    expect(parsed.sub_total).toBe(1000);
    expect(parsed.descuento).toBe(200);
    expect(parsed.honorarios).toBe(800);
  });

  it("expone la tasa cotizada como fracción decimal", () => {
    const parsed = RHInspectorCotizarItemSchema.parse(item);

    expect(parsed.tasa_descuento_aplicada).toBe(0.2);
    expect(parsed.tasa_descuento_aplicada).not.toBe(20);
  });

  it("acepta los Decimals serializados como string por el backend", () => {
    const parsed = RHInspectorCotizarItemSchema.parse({
      ...item,
      sub_total: "1000.00",
      descuento: "200.00",
      honorarios: "800.00",
      tasa_descuento_aplicada: "0.20",
    });

    expect(parsed.sub_total).toBe(1000);
    expect(parsed.descuento).toBe(200);
    expect(parsed.honorarios).toBe(800);
    expect(parsed.tasa_descuento_aplicada).toBe(0.2);
  });

  it("rechaza un item sin los valores financieros calculados", () => {
    const incomplete = { ...item } as Record<string, unknown>;
    delete incomplete.sub_total;
    delete incomplete.descuento;
    delete incomplete.honorarios;
    delete incomplete.tasa_descuento_aplicada;

    expect(RHInspectorCotizarItemSchema.safeParse(incomplete).success).toBe(
      false,
    );
  });
});

describe("RHInspectorCotizarSchema", () => {
  it("parsea la cotización completa con los valores financieros por item", () => {
    const parsed = RHInspectorCotizarSchema.parse(cotizacion);

    expect(parsed.items[0].sub_total).toBe(1000);
    expect(parsed.items[0].descuento).toBe(200);
    expect(parsed.items[0].honorarios).toBe(800);
    expect(parsed.items[0].tasa_descuento_aplicada).toBe(0.2);
  });

  it("mantiene la tasa de los totales como fracción decimal", () => {
    const parsed = RHInspectorCotizarSchema.parse(cotizacion);

    expect(parsed.totales.tasa_descuento_aplicada).toBe(0.2);
    expect(parsed.variables_calculo.rango_aplicado.porcentaje_descuento).toBe(
      0.2,
    );
  });
});
