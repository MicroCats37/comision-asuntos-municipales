/**
 * RhDelegadoMensualModal — selector de período, columna de comprobante y
 * dictamen canónico.
 *
 * Cubre:
 * - el selector `input[type=month]` del paso 2 arranca en el MES CALENDARIO
 *   ANTERIOR al actual;
 * - una candidata nueva nace con el PERÍODO GLOBAL (no con el mes actual);
 * - cambiar el período global NO reescribe las filas ya PERSISTIDAS
 *   (`detalle_id`) — la metadata de un recibo no se toca;
 * - la grid de candidatas muestra la columna "Comprobante" con el
 *   comprobante vigente;
 * - el `Select` de dictamen ofrece el vocabulario canónico (incluido
 *   "No conforme").
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { ReciboHonorarioDelegadoMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";

/** Radix Select llama a `scrollIntoView`, que jsdom no implementa. */
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

const mocks = vi.hoisted(() => ({
  cotizar: vi.fn(),
  refetch: vi.fn(),
  paramsCandidatas: null as Record<string, unknown> | null,
}));

vi.mock("@/features/finanzas/hooks/useRHEditDelegadoDetalleRows", () => ({
  useRHEditDelegadoDetalleRows: () => ({
    rowsByDetalleId: new Map<string, unknown>([
      [
        "detalle-1",
        {
          id: "detalle-1",
          imp_bruto: 1000,
          delegado_liquidacion: {
            id: "asignacion-1",
            liquidacion: {
              id: "lg-1",
              expediente: "EXP-001",
              numero_revision: 2,
              numero: 77,
              municipalidad: {
                id: "municipalidad-1",
                nombre: "Municipalidad Uno",
              },
              tipo_liquidacion: {
                id: "tipo-1",
                codigo: "EDIFICACION",
                nombre: "Edificación",
              },
            },
            especialidad: { id: "esp-1", nombre: "Arquitectura" },
          },
        },
      ],
    ]),
    isLoading: false,
  }),
}));

vi.mock("@/features/finanzas/hooks/useRHDelegadoMensual", () => ({
  useCotizarRHDelegado: () => ({ cotizar: mocks.cotizar, isPending: false }),
  useCrearRHDelegado: () => ({ crear: vi.fn(), isPending: false }),
  useActualizarRHDelegado: () => ({ actualizar: vi.fn(), isPending: false }),
}));

vi.mock("@/features/finanzas/hooks/useCandidatasDelegado", () => ({
  useCandidatasDelegado: (params: Record<string, unknown>) => {
    mocks.paramsCandidatas = params;
    const items = [
      {
        id: "lg-2",
        expediente: "EXP-002",
        numero_revision: 1,
        sub_total: 5000,
        total: 5900,
        municipalidad_nombre: "Municipalidad Uno",
        tipo_liquidacion: {
          id: "tipo-1",
          codigo: "EDIFICACION",
          nombre: "Edificación",
        },
        especialidad_candidata: { id: "esp-1", nombre: "Arquitectura" },
        tipo_delegado: "TITULAR",
        delegado_operacion_id: "operacion-1",
        liquidacion_especifica_numero: 88,
        comprobante_activo: {
          tipo_comprobante: "FACTURA",
          serie: "F001",
          numero: "000123",
          fecha_emision: "2026-10-15",
        },
      },
    ];

    return {
      data: {
        delegado: {
          id: "delegado-1",
          cip: "100001",
          dni: "100001",
          nombre_completo: "Delegado Uno",
        },
        items,
        candidatas: items,
        total: 1,
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

vi.mock("@/features/liquidaciones/hooks/useLiquidacionGeneralDetalle", () => ({
  useLiquidacionGeneralDetalle: () => ({ data: undefined, isLoading: false }),
}));

vi.mock(
  "@/features/finanzas/components/fields/DelegadoOperacionSmartField",
  () => ({
    DelegadoOperacionSmartField: ({
      onSelect,
    }: {
      onSelect: (selection: unknown) => void;
    }) => (
      <button
        type="button"
        onClick={() =>
          onSelect({
            id: "operacion-1",
            municipalidad_id: "municipalidad-1",
            municipalidad_nombre: "Municipalidad Uno",
            tipo_liquidacion_id: "tipo-1",
            tipo_liquidacion_codigo: "EDIFICACION",
            tipo_liquidacion_nombre: "Edificación",
            especialidad_id: "esp-1",
            especialidad_nombre: "Arquitectura",
            tipo: "TITULAR",
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

import { RhDelegadoMensualModal } from "./RhDelegadoMensualModal";
import { useRHSelectionStore } from "@/features/finanzas/stores/rh-selection.store";

const rh = {
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
      dictamen_revision: "CONFORME",
      fecha_presentacion: "2026-10-05",
      fecha_revision: "2026-10-10",
      liquidacion_especifica_numero: 77,
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
    especialidad_id: "esp-1",
    especialidad_nombre: "Arquitectura",
    tipo: "TITULAR",
  },
} as unknown as ReciboHonorarioDelegadoMensual;

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
  render(<RhDelegadoMensualModal open onOpenChange={vi.fn()} />);

  fireEvent.change(screen.getByLabelText("CIP del Delegado"), {
    target: { value: "100001" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Seleccionar operatividad" }),
  );
  fireEvent.click(screen.getByRole("button", { name: /Buscar Candidatas/ }));

  await waitFor(() => expect(selectorPeriodo()).toBeInTheDocument());
}

/** Renderiza el wizard en modo edición (arranca en el paso 2). */
function renderEnEdicion() {
  render(
    <RhDelegadoMensualModal open onOpenChange={vi.fn()} editContext={{ rh }} />,
  );
}

/** Marca la candidata disponible del grid inferior. */
function marcarCandidata() {
  const checkbox = document.getElementById("card-lg-2");
  if (!checkbox) throw new Error("No se encontró la candidata disponible");
  fireEvent.click(checkbox);
}

describe("RhDelegadoMensualModal — selector de período", () => {
  beforeEach(() => {
    mocks.cotizar.mockReset();
    mocks.refetch.mockReset();
    mocks.refetch.mockResolvedValue(undefined);
    useRHSelectionStore.setState({ selections: {} });
  });

  it("arranca en el mes calendario ANTERIOR al actual", async () => {
    await irAlPasoSeleccion();

    const selector = selectorPeriodo();
    expect(selector).toHaveAttribute("type", "month");
    expect(selector).toHaveValue(periodoAnteriorEsperado());
  });

  it("la fila nueva nace con el período global y no con el mes actual", async () => {
    await irAlPasoSeleccion();

    marcarCandidata();

    await waitFor(() =>
      expect(document.getElementById("sel-periodo-lg-2")).toBeInTheDocument(),
    );

    const [anio, mes] = periodoAnteriorEsperado().split("-");
    expect(document.getElementById("sel-periodo-lg-2")).toHaveValue(
      Number(anio),
    );
    expect(document.getElementById("sel-mes-lg-2")).toHaveValue(Number(mes));
  });

  it("cambiar el período global NO reescribe las filas persistidas", async () => {
    renderEnEdicion();

    // La fila persistida del RH (detalle_id) ya viene con 2026 / 10.
    expect(document.getElementById("sel-periodo-lg-1")).toHaveValue(2026);
    expect(document.getElementById("sel-mes-lg-1")).toHaveValue(10);

    marcarCandidata();

    await waitFor(() =>
      expect(document.getElementById("sel-periodo-lg-2")).toBeInTheDocument(),
    );

    // Se cambia el período global de la cabecera.
    fireEvent.change(selectorPeriodo(), { target: { value: "2026-09" } });

    await waitFor(() =>
      expect(document.getElementById("sel-mes-lg-2")).toHaveValue(9),
    );

    // La fila nueva sigue el período global…
    expect(document.getElementById("sel-periodo-lg-2")).toHaveValue(2026);
    // …y la fila persistida conserva el suyo.
    expect(document.getElementById("sel-mes-lg-1")).toHaveValue(10);
  });
});

describe("RhDelegadoMensualModal — columna de comprobante", () => {
  beforeEach(() => {
    useRHSelectionStore.setState({ selections: {} });
  });

  it("muestra el comprobante vigente en la grid de candidatas", async () => {
    await irAlPasoSeleccion();

    expect(screen.getByText("Comprobante")).toBeInTheDocument();
    expect(screen.getByText("F001-000123")).toBeInTheDocument();
    expect(screen.getByText(/FACTURA · 2026-10-15/)).toBeInTheDocument();
  });
});

describe("RhDelegadoMensualModal — dictamen canónico", () => {
  beforeEach(() => {
    useRHSelectionStore.setState({ selections: {} });
  });

  it('ofrece "No conforme" en el selector de dictamen', async () => {
    await irAlPasoSeleccion();

    marcarCandidata();

    await waitFor(() =>
      expect(document.getElementById("sel-dictamen-lg-2")).toBeInTheDocument(),
    );

    fireEvent.click(document.getElementById("sel-dictamen-lg-2"));

    await waitFor(() =>
      expect(
        screen.getByRole("option", { name: "No conforme" }),
      ).toBeInTheDocument(),
    );
  });
});
