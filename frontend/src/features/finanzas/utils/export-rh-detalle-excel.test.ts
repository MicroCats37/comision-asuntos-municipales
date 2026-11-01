import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  DetalleDelegadoRow,
  DetalleInspectorRow,
} from "@/features/finanzas/components/tables/RHDetalleTable.types";

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

const { exportRhDetalleDelegadosExcel, exportRhDetalleInspectoresExcel } =
  await import("./export-rh-detalle-excel");

const delegadoRows: DetalleDelegadoRow[] = [
  {
    id: "detalle-1",
    imp_bruto: 1000,
    sub_total: 1000,
    renta_cip: 250,
    aporte_codemu: 50,
    fondo_comun: 100,
    neto_honorario: 600,
    delegado_liquidacion: {
      id: "asignacion-1",
      periodo: 2026,
      mes: 1,
      numero_rh: "RH-001",
      dictamen_revision: "FAVORABLE",
      fecha_revision: "2026-01-20",
      fecha_presentacion: "2026-01-15",
      delegado: {
        id: "delegado-1",
        cip: "118318",
        nombre_completo: "Delegado Uno",
      },
      liquidacion: {
        id: "liquidacion-1",
        expediente: "113387-26",
        numero: 55163,
        tipo_liquidacion: { codigo: "EDIFICACION", nombre: "Edificación" },
      },
    },
  },
  {
    id: "detalle-2",
    imp_bruto: 500,
    sub_total: 500,
    renta_cip: 125,
    aporte_codemu: 25,
    fondo_comun: 50,
    neto_honorario: 300,
    delegado_liquidacion: {
      id: "asignacion-2",
      periodo: 2026,
      mes: 1,
      numero_rh: "RH-002",
      dictamen_revision: "FAVORABLE",
      fecha_revision: "2026-01-22",
      fecha_presentacion: "2026-01-18",
      delegado: {
        id: "delegado-2",
        cip: "118319",
        nombre_completo: "Delegado Dos",
      },
      liquidacion: {
        id: "liquidacion-2",
        expediente: "113388-26",
        numero: 55164,
        tipo_liquidacion: { codigo: "EDIFICACION", nombre: "Edificación" },
      },
    },
  },
];

const inspectorRows: DetalleInspectorRow[] = [
  {
    id: "detalle-insp-1",
    inspecciones_liquidadas: 3,
    costo_por_inspeccion: 500,
    monto_contribuido: 1500,
    sub_total: 1500,
    descuento: 225,
    honorarios: 1275,
    inspector_liquidacion: {
      id: "asignacion-insp-1",
      periodo: 2026,
      mes: 1,
      dictamen_revision: "CONFORME",
      fecha_revision: "2026-01-20",
      fecha_presentacion: "2026-01-15",
      inspector: {
        id: "inspector-1",
        cip: "CIP-88888",
        nombre_completo: "Inspector Uno",
      },
      liquidacion: {
        id: "liquidacion-io-1",
        expediente: "113387-26",
        numero: 55163,
        tipo_liquidacion: {
          codigo: "INSPECCION_OBRA",
          nombre: "Inspección de Obra",
        },
      },
    },
  },
];

describe("export-rh-detalle-excel", () => {
  beforeEach(() => {
    writeFile.mockClear();
    jsonToSheet.mockClear();
    bookAppendSheet.mockClear();
  });

  it("exporta todas las filas de Delegados con una fila de TOTALES", () => {
    exportRhDetalleDelegadosExcel(delegadoRows, { periodo: 2026, mes: 1 });

    expect(jsonToSheet).toHaveBeenCalledTimes(1);
    const sheet = jsonToSheet.mock.calls[0]?.[0] as Array<
      Record<string, string | number>
    >;

    // Una fila por detalle + una de totales.
    expect(sheet).toHaveLength(delegadoRows.length + 1);

    const primera = sheet[0];
    expect(primera["N° RH"]).toBe("RH-001");
    expect(primera.Expediente).toBe("113387-26");
    expect(primera.Delegado).toBe("Delegado Uno");
    expect(primera.CIP).toBe("118318");
    expect(primera.Periodo).toBe("2026/01");
    expect(primera["Imp. Bruto"]).toBe(1000);
    expect(primera["Neto Honorario"]).toBe(600);

    const totales = sheet[sheet.length - 1];
    expect(totales.Delegado).toBe("TOTALES");
    expect(totales.Periodo).toBe("2026-01");
    expect(totales["Imp. Bruto"]).toBe(1500);
    expect(totales["Renta CIP"]).toBe(375);
    expect(totales["Aporte CODEMU"]).toBe(75);
    expect(totales["Fondo Común"]).toBe(150);
    expect(totales["Neto Honorario"]).toBe(900);

    expect(writeFile).toHaveBeenCalledWith(
      expect.anything(),
      "rh-detalle-delegados-2026-01.xlsx",
    );
  });

  it("exporta las filas de Inspectores con sus totales", () => {
    exportRhDetalleInspectoresExcel(inspectorRows, { periodo: 2026, mes: 1 });

    const sheet = jsonToSheet.mock.calls[0]?.[0] as Array<
      Record<string, string | number>
    >;

    expect(sheet).toHaveLength(inspectorRows.length + 1);

    const primera = sheet[0];
    expect(primera.Inspector).toBe("Inspector Uno");
    expect(primera.CIP).toBe("CIP-88888");
    expect(primera.Periodo).toBe("2026/01");
    expect(primera.Dictamen).toBe("CONFORME");
    expect(primera["Insp. Liquidadas"]).toBe(3);

    const totales = sheet[sheet.length - 1];
    expect(totales.Inspector).toBe("TOTALES");
    expect(totales.Honorarios).toBe(1275);

    expect(writeFile).toHaveBeenCalledWith(
      expect.anything(),
      "rh-detalle-inspectores-2026-01.xlsx",
    );
  });
});
