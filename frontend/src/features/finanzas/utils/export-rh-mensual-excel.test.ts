import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  ReciboHonorarioDelegadoMensual,
  ReciboHonorarioInspectorMensual,
} from "@/features/finanzas/schemas/recibo-honorario.schema";

const writeFile = vi.fn();
const jsonToSheet = vi.fn((rows: unknown) => rows);
const bookAppendSheet = vi.fn();

vi.mock("xlsx", () => ({
  utils: {
    book_new: vi.fn(() => ({})),
    json_to_sheet: (rows: unknown) => jsonToSheet(rows),
    book_append_sheet: (workbook: unknown, worksheet: unknown, name: string) =>
      bookAppendSheet(workbook, worksheet, name),
  },
  writeFile: (workbook: unknown, fileName: string) =>
    writeFile(workbook, fileName),
}));

const {
  buildRhMensualDelegadosRows,
  exportRhMensualDelegadosExcel,
  exportRhMensualInspectoresExcel,
} = await import("./export-rh-mensual-excel");

const detalleDelegado = (expediente: string, monto: number) => ({
  liquidacion_delegado_id: `asig-${expediente}`,
  detalle_id: `det-${expediente}`,
  expediente,
  fecha_revision: "2026-01-20",
  numero_revision: 2,
  total_liquidacion: monto,
  sub_total_liquidacion: monto,
  numero_rh: "RH-001",
  imp_bruto: monto,
  renta_cip: monto * 0.25,
  aporte_codemu: monto * 0.05,
  fondo_comun: monto * 0.1,
  neto_honorario: monto * 0.6,
  periodo: 2026,
  mes: 1,
  dictamen_revision: "FAVORABLE",
  fecha_presentacion: "2026-01-15",
  liquidacion_especifica_numero: 55163,
  comprobante_activo: { tipo_comprobante: "F", serie: "001", numero: "55" },
});

const delegatedRows = [
  {
    id: "rh-1",
    numero: 101,
    periodo: 2026,
    mes: 1,
    fecha_registro: "2026-01-31T10:00:00",
    delegado: { id: "d1", nombre_completo: "Delegado Uno", cip: "118318" },
    totales: {
      sub_total: 1500,
      renta_cip: 375,
      aporte_codemu: 75,
      fondo_comun: 150,
      neto_honorario: 900,
    },
    detalles: [
      detalleDelegado("113387-26", 1000),
      detalleDelegado("113388-26", 500),
    ],
    variables_calculo: {
      tasa_renta_cip: 0.25,
      tasa_aporte_codemu: 0.05,
      tasa_fondo_comun: 0.1,
    },
    delegado_operacion_context: null,
  },
  {
    id: "rh-2",
    numero: 102,
    periodo: 2026,
    mes: 1,
    fecha_registro: "2026-01-31T11:00:00",
    delegado: { id: "d2", nombre_completo: "Delegado Dos", cip: "118319" },
    totales: {
      sub_total: 0,
      renta_cip: 0,
      aporte_codemu: 0,
      fondo_comun: 0,
      neto_honorario: 0,
    },
    detalles: [],
    variables_calculo: {
      tasa_renta_cip: 0.25,
      tasa_aporte_codemu: 0.05,
      tasa_fondo_comun: 0.1,
    },
    delegado_operacion_context: null,
  },
] as unknown as ReciboHonorarioDelegadoMensual[];

const inspectorRows = [
  {
    id: "rh-i1",
    numero: 201,
    periodo: 2026,
    mes: 1,
    fecha_registro: "2026-01-31T10:00:00",
    inspector: {
      id: "i1",
      nombre_completo: "Inspector Uno",
      cip: "CIP-88888",
    },
    totales: {
      inspecciones_programadas: 5,
      inspecciones_liquidadas: 3,
      inspecciones_pagadas_hasta_mes_anterior: 0,
      saldo_restante: 2,
      sub_total: 1500,
      descuento: 225,
      honorarios: 1275,
      tasa_descuento_aplicada: 0.15,
    },
    detalles: [
      {
        detalle_id: "det-i1",
        expediente: "113387-26",
        nombre_propietario: "Propietario Uno",
        distrito: "LIMA",
        importe_bruto: 1500,
        inspecciones_programadas: 5,
        inspecciones_liquidadas: 3,
        inspecciones_pagadas_hasta_mes_anterior: 0,
        costo_por_inspeccion: 500,
        monto_contribuido: 1500,
        saldo_restante: 2,
        liquidacion_especifica_numero: 55163,
        numero_revision: 3,
        comprobante_activo: null,
        honorarios: 1275,
        descuento: 225,
        sub_total: 1500,
        fecha_revision: "2026-01-20",
        fecha_presentacion: "2026-01-15",
        dictamen_revision: "CONFORME",
      },
    ],
    variables_calculo: {
      escala_id: "esc1",
      escala_nombre: "Escala 15%",
      rango_aplicado: {
        monto_minimo: 0,
        monto_maximo: null,
        porcentaje_descuento: 15,
      },
    },
  },
] as unknown as ReciboHonorarioInspectorMensual[];

describe("export-rh-mensual-excel", () => {
  beforeEach(() => {
    writeFile.mockClear();
    jsonToSheet.mockClear();
    bookAppendSheet.mockClear();
  });

  it("aplana una fila por liquidación de Delegado (no por recibo)", () => {
    const filas = buildRhMensualDelegadosRows(delegatedRows);

    // 2 liquidaciones del RH-1; el RH-2 no tiene liquidaciones.
    expect(filas).toHaveLength(2);

    const primera = filas[0];
    expect(primera.Item).toBe(1);
    expect(primera["N° RH"]).toBe(101);
    expect(primera.Delegado).toBe("Delegado Uno");
    expect(primera.CIP).toBe("118318");
    expect(primera.Expediente).toBe("113387-26");
    expect(primera["Nro Liq."]).toBe(55163);
    expect(primera.Dictamen).toBe("FAVORABLE");
    expect(primera["Importe bruto"]).toBe(1000);
    expect(primera["Neto honorario"]).toBe(600);
  });

  it("exporta el detalle de Delegado con fila de TOTALES", () => {
    exportRhMensualDelegadosExcel(delegatedRows, { periodo: 2026, mes: 1 });

    const sheet = jsonToSheet.mock.calls[0]?.[0] as Array<
      Record<string, string | number>
    >;

    // 2 liquidaciones + 1 fila de totales.
    expect(sheet).toHaveLength(3);

    const totales = sheet[sheet.length - 1];
    expect(totales.Delegado).toBe("TOTALES");
    expect(totales.Periodo).toBe("2026-01");
    expect(totales["Importe bruto"]).toBe(1500);
    expect(totales["Renta CIP"]).toBe(375);
    expect(totales["Neto honorario"]).toBe(900);

    expect(writeFile).toHaveBeenCalledWith(
      expect.anything(),
      "rh-mensual-delegados-2026-01.xlsx",
    );
  });

  it("exporta el detalle de Inspectores con fila de TOTALES", () => {
    exportRhMensualInspectoresExcel(inspectorRows, { periodo: 2026, mes: 1 });

    const sheet = jsonToSheet.mock.calls[0]?.[0] as Array<
      Record<string, string | number>
    >;

    // 1 liquidación + 1 fila de totales.
    expect(sheet).toHaveLength(2);

    const primera = sheet[0];
    expect(primera["N° RH"]).toBe(201);
    expect(primera.Inspector).toBe("Inspector Uno");
    expect(primera.CIP).toBe("CIP-88888");
    expect(primera.Expediente).toBe("113387-26");
    expect(primera.Propietario).toBe("Propietario Uno");
    expect(primera.Honorarios).toBe(1275);

    const totales = sheet[sheet.length - 1];
    expect(totales.Inspector).toBe("TOTALES");
    expect(totales.Honorarios).toBe(1275);
    expect(totales["IO incluidas" as string]).toBeUndefined();

    expect(writeFile).toHaveBeenCalledWith(
      expect.anything(),
      "rh-mensual-inspectores-2026-01.xlsx",
    );
  });
});
