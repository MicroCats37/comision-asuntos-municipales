/**
 * recibo-honorario.schema — contrato del listado mensual de RH (Inspector y Delegado).
 *
 * Verifica que el zod refleje EXACTAMENTE el contrato HTTP del backend:
 *  - el RH Inspector expone el nº de RH de cabecera (`numero`) y, por fila, el
 *    nº de revisión, el nº de liquidación específica, las fechas de revisión y
 *    presentación, el dictamen de revisión y el comprobante activo tipado;
 *  - los tres números viajan separados: `numero` (RH), `numero_revision`
 *    (revisión) y `liquidacion_especifica_numero` (liquidación específica);
 *  - el RH Delegado conserva su contrato enriquecido (sin degradación).
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase (la ejecución
 * consolidada es la fase final de verificación).
 */
import { describe, expect, it } from "vitest";
import {
  rhDelegadoMensualListItemSchema,
  rhInspectorMensualDetalleSchema,
  rhInspectorMensualListItemSchema,
} from "./recibo-honorario.schema";

const comprobante = {
  tipo_comprobante: "FACTURA",
  serie: "F001",
  numero: "0001-45",
  fecha_emision: "2026-01-10",
};

const detalleInspector = {
  detalle_id: "detalle-1",
  expediente: "EXP-001",
  nombre_propietario: "Propietario Uno",
  distrito: "MIRAFLORES",
  importe_bruto: 1000,
  inspecciones_programadas: 4,
  inspecciones_liquidadas: 2,
  inspecciones_pagadas_hasta_mes_anterior: 1,
  costo_por_inspeccion: 500,
  monto_contribuido: 1000,
  saldo_restante: 1,
  liquidacion_especifica_numero: 42,
  numero_revision: 3,
  comprobante_activo: comprobante,
  sub_total: 1000,
  descuento: 200,
  honorarios: 800,
  fecha_revision: "2026-01-15",
  fecha_presentacion: "2026-01-20",
  dictamen_revision: "CONFORME",
};

const rhInspector = {
  id: "rh-1",
  numero: 7,
  periodo: 2026,
  mes: 1,
  fecha_registro: "2026-01-31T10:00:00",
  inspector: {
    id: "inspector-1",
    cip: "CIP-88888",
    dni: "76543210",
    nombre_completo: "María Quispe Rojas",
  },
  totales: {
    inspecciones_programadas: 4,
    inspecciones_liquidadas: 2,
    inspecciones_pagadas_hasta_mes_anterior: 1,
    saldo_restante: 1,
    sub_total: 1000,
    descuento: 200,
    honorarios: 800,
    tasa_descuento_aplicada: 0.2,
  },
  detalles: [detalleInspector],
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

const detalleDelegado = {
  liquidacion_delegado_id: "ld-1",
  detalle_id: "detalle-2",
  expediente: "EXP-002",
  fecha_revision: "2026-01-05",
  numero_revision: 3,
  total_liquidacion: 1180,
  sub_total_liquidacion: 1000,
  numero_rh: "1",
  imp_bruto: 1000,
  renta_cip: 250,
  aporte_codemu: 50,
  fondo_comun: 100,
  neto_honorario: 600,
  periodo: 2026,
  mes: 1,
  dictamen_revision: "CONFORME",
  fecha_presentacion: "2026-01-10",
  delegado_operacion_id: "op-1",
  liquidacion_especifica_numero: 42,
  comprobante_activo: comprobante,
};

const rhDelegado = {
  id: "rh-2",
  numero: 11,
  periodo: 2026,
  mes: 1,
  fecha_registro: "2026-01-31T10:00:00",
  delegado: {
    id: "delegado-1",
    cip: "CIP-00001",
    dni: "11111111",
    nombre_completo: "Delegado Uno",
  },
  totales: {
    sub_total: 1000,
    renta_cip: 250,
    aporte_codemu: 50,
    fondo_comun: 100,
    neto_honorario: 600,
  },
  detalles: [detalleDelegado],
  variables_calculo: {
    tasa_renta_cip: 0.25,
    tasa_aporte_codemu: 0.05,
    tasa_fondo_comun: 0.1,
  },
};

describe("rhInspectorMensualListItemSchema", () => {
  it("expone el número de RH de cabecera", () => {
    const parsed = rhInspectorMensualListItemSchema.parse(rhInspector);

    expect(parsed.numero).toBe(7);
  });

  it("acepta un RH sin número de cabecera", () => {
    const parsed = rhInspectorMensualListItemSchema.parse({
      ...rhInspector,
      numero: null,
    });

    expect(parsed.numero).toBeNull();
  });
});

describe("rhInspectorMensualDetalleSchema", () => {
  it("expone las fechas de revisión y presentación con su dictamen", () => {
    const parsed = rhInspectorMensualDetalleSchema.parse(detalleInspector);

    expect(parsed.fecha_revision).toBe("2026-01-15");
    expect(parsed.fecha_presentacion).toBe("2026-01-20");
    expect(parsed.dictamen_revision).toBe("CONFORME");
  });

  it("expone el número de liquidación específico y el de revisión por separado", () => {
    const parsed = rhInspectorMensualDetalleSchema.parse(detalleInspector);

    expect(parsed.liquidacion_especifica_numero).toBe(42);
    expect(parsed.numero_revision).toBe(3);
    expect(parsed.liquidacion_especifica_numero).not.toBe(parsed.numero_revision);
  });

  it("expone el comprobante activo con sus campos tipados", () => {
    const parsed = rhInspectorMensualDetalleSchema.parse(detalleInspector);

    expect(parsed.comprobante_activo?.tipo_comprobante).toBe("FACTURA");
    expect(parsed.comprobante_activo?.serie).toBe("F001");
    expect(parsed.comprobante_activo?.numero).toBe("0001-45");
    expect(parsed.comprobante_activo?.fecha_emision).toBe("2026-01-10");
  });

  it("admite un detalle sin comprobante activo", () => {
    const parsed = rhInspectorMensualDetalleSchema.parse({
      ...detalleInspector,
      comprobante_activo: null,
    });

    expect(parsed.comprobante_activo).toBeNull();
  });
});

describe("rhDelegadoMensualListItemSchema", () => {
  it("no se degrada: conserva todos los campos por fila", () => {
    const parsed = rhDelegadoMensualListItemSchema.parse(rhDelegado);
    const detalle = parsed.detalles[0];

    expect(parsed.numero).toBe(11);
    expect(detalle.numero_rh).toBe("1");
    expect(detalle.numero_revision).toBe(3);
    expect(detalle.liquidacion_especifica_numero).toBe(42);
    expect(detalle.fecha_revision).toBe("2026-01-05");
    expect(detalle.fecha_presentacion).toBe("2026-01-10");
    expect(detalle.dictamen_revision).toBe("CONFORME");
    expect(detalle.comprobante_activo?.numero).toBe("0001-45");
  });
});
