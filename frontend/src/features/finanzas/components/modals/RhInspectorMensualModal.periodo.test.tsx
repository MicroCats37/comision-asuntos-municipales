/**
 * RhInspectorMensualModal — período por defecto, columna de comprobante y
 * guarda de filas persistidas.
 *
 * Cubre:
 * - el selector `input[type=month]` del paso 2 arranca en el MES CALENDARIO
 *   ANTERIOR al actual;
 * - la grid de candidatas muestra la columna "Comprobante" con el
 *   comprobante vigente;
 * - una candidata nueva nace con el PERÍODO GLOBAL;
 * - cambiar el período global NO reescribe las filas ya PERSISTIDAS
 *   (`detalle_id`).
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReciboHonorarioInspectorMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";

const mocks = vi.hoisted(() => ({
  cotizar: vi.fn(),
  refetch: vi.fn(),
  paramsCandidatas: null as Record<string, unknown> | null,
  items: [] as unknown[],
}));

/** Candidatas del inspector (el listado se inyecta por test). */
const candidatas = {
  vacias: [] as unknown[],
  conComprobante: [
    {
      liquidacion_inspector_id: "li-1",
      liquidacion_categoria_visitas_id: "lcv-1",
      liquidacion_general_id: "lg-1",
      expediente: "EXP-001",
      numero_revision: 1,
      fecha_registro: "2026-10-01",
      inspector_nombre: "Inspector Uno",
      inspector_cip: "100001",
      inspector_dni: "100001",
      especialidad_nombre: "Arquitectura",
      nombre_propietario: "Propietario Uno",
      cantidad_visitas: 4,
      inspecciones_pagadas: 1,
      saldo_disponible: 3,
      costo_por_inspeccion: 500,
      total_liquidacion: 2000,
      sub_total_liquidacion: 2000,
      sub_total: 2000,
      descuento: 0,
      honorarios: 2000,
      tasa_descuento_aplicada: 0,
      periodo: 2026,
      mes: 10,
      liquidacion_especifica_numero: 77,
      comprobante_activo: {
        tipo_comprobante: "FACTURA",
        serie: "F001",
        numero: "000123",
        fecha_emision: "2026-10-15",
      },
    },
  ],
};

vi.mock("@/features/finanzas/hooks/useCandidatasInspector", () => ({
  useCandidatasInspector: (params: Record<string, unknown>) => {
    mocks.paramsCandidatas = params;
    const items = mocks.items;
    return {
      data: {
        inspector_id: "insp-1",
        inspector_nombre: "Inspector Uno",
        inspector_cip: "100001",
        inspector_dni: "100001",
        periodo: "2026-10",
        items,
        candidatos: items,
        total: items.length,
        page: 1,
        pageSize: 20,
        page_size: 20,
        totalPages: 1,
        total_pages: 1,
      },
      isLoading: false,
      isError: false,
      refetch: mocks.refetch,
    };
  },
}));

mocks.items = candidatas.vacias;

vi.mock("@/features/finanzas/hooks/useRHInspectorMensual", () => ({
  useCotizarRHInspector: () => ({ cotizar: mocks.cotizar, isPending: false }),
  useCotizarEdicionRHInspector: () => ({
    cotizar: mocks.cotizar,
    isPending: false,
  }),
  useCrearRHInspector: () => ({ crear: vi.fn(), isPending: false }),
  useActualizarRHInspector: () => ({ actualizar: vi.fn(), isPending: false }),
}));

vi.mock("@/features/liquidaciones/hooks/useLiquidacionGeneralDetalle", () => ({
  useLiquidacionGeneralDetalle: () => ({ data: undefined, isLoading: false }),
}));

vi.mock(
  "@/features/finanzas/components/fields/InspectorOperacionSmartField",
  () => ({
    InspectorOperacionSmartField: ({
      onSelect,
    }: {
      onSelect: (operacion: unknown) => void;
    }) => (
      <button
        type="button"
        onClick={() =>
          onSelect({
            inspector_operacion_id: "io-1",
            tipo_liquidacion: "INSPECCION_OBRA",
            especialidad: { id: "esp-1", nombre: "Arquitectura" },
            numero_registro: 1,
            periodo_inicio: "2026-01-01",
            periodo_fin: null,
          })
        }
      >
        Seleccionar operatividad
      </button>
    ),
  }),
);

vi.mock("@/features/liquidaciones/components/detail", () => ({
  composeDetalleSections: () => null,
  getTipoDetalleSection: () => null,
  LiquidacionDetalleModal: () => null,
}));

vi.mock("@/errors", () => ({
  notify: { error: vi.fn(), success: vi.fn() },
}));

import { RhInspectorMensualModal } from "./RhInspectorMensualModal";
import { useRHSelectionStore } from "@/features/finanzas/stores/rh-selection.store";

const rh = {
  id: "rh-inspector-1",
  periodo: 2026,
  mes: 10,
  fecha_registro: "2026-10-31T10:00:00",
  inspector: {
    id: "insp-1",
    cip: "100001",
    dni: "100001",
    nombre_completo: "Inspector Uno",
  },
  totales: {
    sub_total: 2000,
    descuento: 0,
    honorarios: 2000,
  },
  detalles: [
    {
      detalle_id: "detalle-1",
      expediente: "EXP-001",
      numero_revision: 1,
      inspecciones_programadas: 4,
      inspecciones_pagadas_hasta_mes_anterior: 1,
      inspecciones_liquidadas: 2,
      nombre_propietario: "Propietario Uno",
      costo_por_inspeccion: 500,
      importe_bruto: 2000,
      sub_total: 2000,
      liquidacion_especifica_numero: 77,
      comprobante_activo: {
        tipo_comprobante: "FACTURA",
        serie: "F001",
        numero: "000123",
        fecha_emision: "2026-10-15",
      },
    },
  ],
} as unknown as ReciboHonorarioInspectorMensual;

/** Período esperado por defecto: el mes calendario anterior al actual. */
function periodoAnteriorEsperado(): string {
  const now = new Date();
  const anterior = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  return `${anterior.getFullYear()}-${String(anterior.getMonth() + 1).padStart(2, "0")}`;
}

/** Selector de período de la cabecera del paso 2. */
function selectorPeriodo(): HTMLInputElement {
  const input = document.getElementById("periodo-step2");
  if (!(input instanceof HTMLInputElement)) {
    throw new Error("No se encontró el selector de período (#periodo-step2)");
  }
  return input;
}

/** Lleva el wizard (modo creación) del paso 1 al paso 2. */
async function irAlPasoSeleccion() {
  render(<RhInspectorMensualModal open onOpenChange={vi.fn()} />);

  fireEvent.change(screen.getByLabelText("CIP del Inspector"), {
    target: { value: "100001" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Seleccionar operatividad" }),
  );
  fireEvent.click(screen.getByRole("button", { name: /Buscar Candidatas/ }));

  await waitFor(() => expect(selectorPeriodo()).toBeInTheDocument());
}

describe("RhInspectorMensualModal — período por defecto", () => {
  beforeEach(() => {
    mocks.cotizar.mockReset();
    mocks.refetch.mockReset();
    mocks.refetch.mockResolvedValue(undefined);
    mocks.items = candidatas.vacias;
    useRHSelectionStore.setState({ selections: {} });
  });

  it("arranca en el mes calendario ANTERIOR al actual", async () => {
    await irAlPasoSeleccion();

    const selector = selectorPeriodo();
    expect(selector).toHaveAttribute("type", "month");
    expect(selector).toHaveValue(periodoAnteriorEsperado());
  });
});

describe("RhInspectorMensualModal — columna de comprobante", () => {
  beforeEach(() => {
    mocks.refetch.mockReset();
    mocks.refetch.mockResolvedValue(undefined);
    mocks.items = candidatas.conComprobante;
    useRHSelectionStore.setState({ selections: {} });
  });

  it("muestra el comprobante vigente en la grid de candidatas", async () => {
    await irAlPasoSeleccion();

    expect(screen.getByText("Comprobante")).toBeInTheDocument();
    expect(screen.getByText("F001-000123")).toBeInTheDocument();
    expect(screen.getByText(/FACTURA · 2026-10-15/)).toBeInTheDocument();
  });

  it("la candidata nueva nace con el período global", async () => {
    await irAlPasoSeleccion();

    const checkbox = document.getElementById("row-lcv-1");
    if (!checkbox) throw new Error("No se encontró la candidata disponible");
    fireEvent.click(checkbox);

    await waitFor(() =>
      expect(document.getElementById("sel-periodo-lcv-1")).toBeInTheDocument(),
    );

    const [anio, mes] = periodoAnteriorEsperado().split("-");
    expect(document.getElementById("sel-periodo-lcv-1")).toHaveValue(
      Number(anio),
    );
    expect(document.getElementById("sel-mes-lcv-1")).toHaveValue(Number(mes));
  });
});

describe("RhInspectorMensualModal — guarda de filas persistidas", () => {
  beforeEach(() => {
    mocks.refetch.mockReset();
    mocks.refetch.mockResolvedValue(undefined);
    mocks.items = candidatas.vacias;
    useRHSelectionStore.setState({ selections: {} });
  });

  it("cambiar el período global NO reescribe la fila persistida", async () => {
    render(
      <RhInspectorMensualModal
        open
        onOpenChange={vi.fn()}
        editContext={{ rh }}
      />,
    );

    await waitFor(() =>
      expect(
        document.getElementById("sel-periodo-detalle:detalle-1"),
      ).toBeInTheDocument(),
    );

    expect(
      document.getElementById("sel-periodo-detalle:detalle-1"),
    ).toHaveValue(2026);
    expect(document.getElementById("sel-mes-detalle:detalle-1")).toHaveValue(
      10,
    );

    fireEvent.change(selectorPeriodo(), { target: { value: "2026-09" } });

    await waitFor(() =>
      expect(selectorPeriodo()).toHaveValue("2026-09"),
    );

    // La fila persistida conserva su período/mes.
    expect(
      document.getElementById("sel-periodo-detalle:detalle-1"),
    ).toHaveValue(2026);
    expect(document.getElementById("sel-mes-detalle:detalle-1")).toHaveValue(
      10,
    );
  });
});
