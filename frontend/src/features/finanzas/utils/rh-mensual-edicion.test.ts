/**
 * Modo EDICIÓN de RH mensuales — preselección y metadata persistida.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase (la ejecución
 * consolidada es la fase final de verificación).
 */
import { describe, expect, it } from "vitest";
import type {
  DetalleDelegadoRow,
  ReciboHonorarioDelegadoMensual,
  ReciboHonorarioInspectorMensual,
} from "../schemas/recibo-honorario.schema";
import {
  buildDelegadoEditOperacionSelection,
  buildDelegadoEditSelection,
  buildInspectorEditSelection,
} from "./rh-mensual-edicion";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const buildDelegadoRh = (): ReciboHonorarioDelegadoMensual =>
  ({
    id: "rh-delegado-1",
    periodo: 2026,
    mes: 10,
    fecha_registro: "2026-10-31T10:00:00",
    delegado: {
      id: "delegado-1",
      cip: "100001",
      dni: "100001",
      nombre_completo: "Delegado Uno",
    },
    totales: {
      sub_total: 1000,
      renta_cip: 250,
      aporte_codemu: 50,
      fondo_comun: 100,
      neto_honorario: 600,
    },
    detalles: [
      {
        liquidacion_delegado_id: "asignacion-1",
        detalle_id: "detalle-1",
        expediente: "EXP-001",
        numero_revision: 2,
        total_liquidacion: 1200,
        sub_total_liquidacion: 1000,
        numero_rh: "RH-001",
        imp_bruto: 1000,
        renta_cip: 250,
        aporte_codemu: 50,
        fondo_comun: 100,
        neto_honorario: 600,
        periodo: 2026,
        mes: 10,
        dictamen_revision: "APROBADO",
        fecha_presentacion: "2026-10-05",
        fecha_revision: "2026-10-10",
        liquidacion_especifica_numero: 77,
      },
      {
        liquidacion_delegado_id: "asignacion-2",
        detalle_id: "detalle-2",
        expediente: "EXP-002",
        numero_revision: 1,
        total_liquidacion: 900,
        sub_total_liquidacion: 800,
        numero_rh: null,
        imp_bruto: 800,
        periodo: null,
        mes: null,
        dictamen_revision: null,
        fecha_presentacion: null,
        fecha_revision: null,
        liquidacion_especifica_numero: 88,
      },
    ],
    variables_calculo: {
      tasa_renta_cip: 0.25,
      tasa_aporte_codemu: 0.05,
      tasa_fondo_comun: 0.1,
    },
    delegado_operacion_id: "operacion-1",
    delegado_operacion_context: {
      id: "operacion-1",
      municipalidad_id: "municipalidad-1",
      municipalidad_nombre: "Municipalidad Uno",
      tipo_liquidacion_id: "tipo-1",
      tipo_liquidacion_codigo: "EDIFICACION",
      tipo_liquidacion_nombre: "Edificación",
      especialidad_id: "especialidad-1",
      especialidad_nombre: "Arquitectura",
      tipo: "TITULAR",
    },
  }) as unknown as ReciboHonorarioDelegadoMensual;

const buildDetalleRow = (
  id: string,
  liquidacionId: string,
  especialidadId: string,
): DetalleDelegadoRow =>
  ({
    id,
    imp_bruto: 1000,
    sub_total: 1000,
    renta_cip: 250,
    aporte_codemu: 50,
    fondo_comun: 100,
    neto_honorario: 600,
    delegado_liquidacion: {
      id: `asignacion-${id}`,
      numero_rh: "RH-001",
      periodo: 2026,
      mes: 10,
      dictamen_revision: "APROBADO",
      fecha_revision: "2026-10-10",
      fecha_presentacion: "2026-10-05",
      delegado: {
        id: "delegado-1",
        cip: "100001",
        nombre_completo: "Delegado Uno",
      },
      liquidacion: {
        id: liquidacionId,
        expediente: "EXP-001",
        numero_revision: 2,
        numero: 77,
        municipalidad: { id: "municipalidad-1", nombre: "Municipalidad Uno" },
        tipo_liquidacion: {
          id: "tipo-1",
          codigo: "EDIFICACION",
          nombre: "Edificación",
        },
      },
      especialidad: { id: especialidadId, nombre: "Arquitectura" },
    },
  }) as unknown as DetalleDelegadoRow;

const buildInspectorRh = (): ReciboHonorarioInspectorMensual =>
  ({
    id: "rh-inspector-1",
    periodo: 2026,
    mes: 10,
    fecha_registro: "2026-10-31T10:00:00",
    inspector: {
      id: "inspector-1",
      cip: "200002",
      dni: "200002",
      nombre_completo: "Inspector Dos",
    },
    totales: {
      inspecciones_programadas: 5,
      inspecciones_liquidadas: 2,
      inspecciones_pagadas_hasta_mes_anterior: 1,
      saldo_restante: 2,
      sub_total: 1000,
      descuento: 200,
      honorarios: 800,
      tasa_descuento_aplicada: 0.2,
    },
    detalles: [
      {
        detalle_id: "detalle-insp-1",
        expediente: "EXP-IO-001",
        nombre_propietario: "Propietario Uno",
        distrito: "Miraflores",
        importe_bruto: 1000,
        inspecciones_programadas: 5,
        inspecciones_liquidadas: 2,
        inspecciones_pagadas_hasta_mes_anterior: 1,
        costo_por_inspeccion: 200,
        monto_contribuido: 400,
        saldo_restante: 2,
      },
    ],
    variables_calculo: {
      escala_id: "escala-1",
      escala_nombre: "Escala 2026",
      rango_aplicado: {
        monto_minimo: 0,
        monto_maximo: 10000,
        porcentaje_descuento: 0.2,
      },
    },
  }) as unknown as ReciboHonorarioInspectorMensual;

// ── Delegado ──────────────────────────────────────────────────────────────────

describe("buildDelegadoEditSelection — preselección del RH de delegado", () => {
  it("preselecciona un item por cada detalle persistido resoluble", () => {
    const rows = new Map<string, DetalleDelegadoRow>([
      ["detalle-1", buildDetalleRow("detalle-1", "lg-1", "esp-1")],
      ["detalle-2", buildDetalleRow("detalle-2", "lg-2", "esp-1")],
    ]);

    const { entries, unresolved } = buildDelegadoEditSelection(
      buildDelegadoRh(),
      rows,
    );

    expect(entries).toHaveLength(2);
    expect(unresolved).toBe(0);
  });

  it("conserva el detalle_id persistido para que el PATCH conserve la fila", () => {
    const rows = new Map<string, DetalleDelegadoRow>([
      ["detalle-1", buildDetalleRow("detalle-1", "lg-1", "esp-1")],
      ["detalle-2", buildDetalleRow("detalle-2", "lg-2", "esp-1")],
    ]);

    const { entries } = buildDelegadoEditSelection(buildDelegadoRh(), rows);

    expect(entries[0].cotizarItem.detalle_id).toBe("detalle-1");
    expect(entries[1].cotizarItem.detalle_id).toBe("detalle-2");
  });

  it("siembra la metadata desde el detalle persistido (no desde el encabezado)", () => {
    const rows = new Map<string, DetalleDelegadoRow>([
      ["detalle-1", buildDetalleRow("detalle-1", "lg-1", "esp-1")],
      ["detalle-2", buildDetalleRow("detalle-2", "lg-2", "esp-1")],
    ]);

    const { entries } = buildDelegadoEditSelection(buildDelegadoRh(), rows);

    expect(entries[0].cotizarItem.numero_rh).toBe("RH-001");
    expect(entries[0].cotizarItem.periodo).toBe(2026);
    expect(entries[0].cotizarItem.mes).toBe(10);
    expect(entries[0].cotizarItem.dictamen_revision).toBe("APROBADO");
    expect(entries[0].cotizarItem.fecha_presentacion).toBe("2026-10-05");
    expect(entries[0].cotizarItem.fecha_revision).toBe("2026-10-10");
  });

  it("resuelve liquidacion_general_id y especialidad_revision_id del detalle flat", () => {
    const rows = new Map<string, DetalleDelegadoRow>([
      ["detalle-1", buildDetalleRow("detalle-1", "lg-1", "esp-1")],
      ["detalle-2", buildDetalleRow("detalle-2", "lg-2", "esp-1")],
    ]);

    const { entries } = buildDelegadoEditSelection(buildDelegadoRh(), rows);

    expect(entries[0].cotizarItem.liquidacion_general_id).toBe("lg-1");
    expect(entries[0].cotizarItem.especialidad_revision_id).toBe("esp-1");
  });

  it("indexa la fila por su liquidación para que no vuelva a ofrecerse como candidata", () => {
    const rows = new Map<string, DetalleDelegadoRow>([
      ["detalle-1", buildDetalleRow("detalle-1", "lg-1", "esp-1")],
      ["detalle-2", buildDetalleRow("detalle-2", "lg-2", "esp-1")],
    ]);

    const { entries } = buildDelegadoEditSelection(buildDelegadoRh(), rows);

    expect(entries[0].candidate.id).toBe("lg-1");
    expect(entries[1].candidate.id).toBe("lg-2");
  });

  it("cuenta como no resueltos los detalles sin fila flat y no los selecciona", () => {
    const rows = new Map<string, DetalleDelegadoRow>([
      ["detalle-1", buildDetalleRow("detalle-1", "lg-1", "esp-1")],
    ]);

    const { entries, unresolved } = buildDelegadoEditSelection(
      buildDelegadoRh(),
      rows,
    );

    expect(entries).toHaveLength(1);
    expect(unresolved).toBe(1);
  });

  it("deja la metadata vacía cuando el detalle persistido no la tiene", () => {
    const rows = new Map<string, DetalleDelegadoRow>([
      ["detalle-1", buildDetalleRow("detalle-1", "lg-1", "esp-1")],
      ["detalle-2", buildDetalleRow("detalle-2", "lg-2", "esp-1")],
    ]);

    const { entries } = buildDelegadoEditSelection(buildDelegadoRh(), rows);

    expect(entries[1].cotizarItem.numero_rh).toBe("");
    expect(entries[1].cotizarItem.periodo).toBeUndefined();
    expect(entries[1].cotizarItem.mes).toBeUndefined();
    expect(entries[1].cotizarItem.dictamen_revision).toBe("");
  });
});

describe("buildDelegadoEditOperacionSelection — operatividad del RH", () => {
  it("reconstruye la operatividad vigente desde el contexto del listado", () => {
    const operacion = buildDelegadoEditOperacionSelection(buildDelegadoRh());

    expect(operacion?.id).toBe("operacion-1");
    expect(operacion?.tipo_liquidacion_codigo).toBe("EDIFICACION");
    expect(operacion?.especialidad_id).toBe("especialidad-1");
  });

  it("devuelve null cuando el RH no tiene operatividad (flujo legacy)", () => {
    const rh = buildDelegadoRh();
    rh.delegado_operacion_context = null;

    expect(buildDelegadoEditOperacionSelection(rh)).toBeNull();
  });
});

// ── Inspector ─────────────────────────────────────────────────────────────────

describe("buildInspectorEditSelection — preselección del RH de inspector", () => {
  it("preselecciona los detalles persistidos con su detalle_id", () => {
    const entries = buildInspectorEditSelection(buildInspectorRh());

    expect(entries).toHaveLength(1);
    expect(entries[0].cotizarItem.detalle_id).toBe("detalle-insp-1");
  });

  it("siembra la cantidad de inspecciones liquidadas del detalle persistido", () => {
    const entries = buildInspectorEditSelection(buildInspectorRh());

    expect(entries[0].cotizarItem.cantidad_visitas).toBe(2);
    expect(entries[0].cotizarItem.periodo).toBe(2026);
    expect(entries[0].cotizarItem.mes).toBe(10);
  });

  it("indexa la fila persistida con una clave propia (detalle:<id>)", () => {
    const entries = buildInspectorEditSelection(buildInspectorRh());

    expect(entries[0].candidate.liquidacion_categoria_visitas_id).toBe(
      "detalle:detalle-insp-1",
    );
    expect(entries[0].candidate.expediente).toBe("EXP-IO-001");
  });

  it("expone el saldo disponible sin contar las visitas del propio RH", () => {
    const entries = buildInspectorEditSelection(buildInspectorRh());

    // programadas (5) - pagadas hasta el mes anterior (1) = 4
    expect(entries[0].candidate.saldo_disponible).toBe(4);
  });

  it("omite los detalles sin detalle_id porque no se pueden conservar", () => {
    const rh = buildInspectorRh();
    rh.detalles = [{ ...rh.detalles[0], detalle_id: null }];

    expect(buildInspectorEditSelection(rh)).toHaveLength(0);
  });
});
