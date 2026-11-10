/**
 * RhInspectorMensualModal — acceso al browse de liquidaciones existentes.
 *
 * Contrato de la capability `rh-mensual-browse-edit`:
 * - el paso 2 del wizard expone una acción que abre el browse de liquidaciones
 *   EXISTENTES;
 * - la acción está disponible SIEMPRE en el paso 2, incluso cuando NO hay
 *   ninguna candidata (es la salida del usuario en ese caso);
 * - el browse es una vista separada: no crea revisiones.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la verificación
 * corre en la fase final de SDD (tarea 5.4).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiPut: vi.fn(),
  apiDelete: vi.fn(),
  refetch: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: {
    get: mocks.apiGet,
    post: mocks.apiPost,
    patch: mocks.apiPatch,
    put: mocks.apiPut,
    delete: mocks.apiDelete,
  },
}));

vi.mock("@/features/finanzas/hooks/useRHInspectorMensual", () => ({
  useCotizarRHInspector: () => ({ cotizar: vi.fn(), isPending: false }),
  useCotizarEdicionRHInspector: () => ({
    cotizar: vi.fn(),
    isPending: false,
  }),
  useCrearRHInspector: () => ({ crear: vi.fn(), isPending: false }),
  useActualizarRHInspector: () => ({ actualizar: vi.fn(), isPending: false }),
}));

/** El wizard arranca SIN candidatas: el browse es la única salida. */
vi.mock("@/features/finanzas/hooks/useCandidatasInspector", () => ({
  useCandidatasInspector: () => ({
    data: {
      inspector_id: "inspector-1",
      inspector_nombre: "Inspector Uno",
      inspector_cip: "200002",
      inspector_dni: "200002",
      periodo: "2026-10",
      items: [],
      candidatos: [],
      total: 0,
      page: 1,
      pageSize: 20,
      page_size: 20,
      totalPages: 1,
      total_pages: 1,
    },
    isLoading: false,
    isError: false,
    refetch: mocks.refetch,
  }),
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
            id: "operacion-1",
            nombre_completo: "Inspector Uno",
            cip: "200002",
            especialidad: { id: "esp-1", nombre: "Arquitectura" },
            tipo_liquidacion: "INSPECCION_OBRA",
            categoria: "INSPECCION",
            numero_registro: "REG-1",
            vigencia: "2026",
            periodo_inicio: "2026",
            periodo_fin: null,
            es_vigente: true,
            inspector_operacion_id: "operacion-1",
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

import { RhInspectorMensualModal } from "./RhInspectorMensualModal";
import { useRHSelectionStore } from "@/features/finanzas/stores/rh-selection.store";

/** Lleva el wizard (modo creación) del paso 1 al paso 2. */
async function irAlPasoSeleccion() {
  // El browse usa TanStack Query: el harness necesita su QueryClient.
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <RhInspectorMensualModal open onOpenChange={vi.fn()} />
    </QueryClientProvider>,
  );

  fireEvent.change(screen.getByLabelText("CIP del Inspector"), {
    target: { value: "200002" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Seleccionar operatividad" }),
  );
  fireEvent.click(screen.getByRole("button", { name: /Buscar Candidatas/ }));

  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: /Ver liquidaciones existentes/ }),
    ).toBeInTheDocument(),
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.refetch.mockResolvedValue(undefined);
  mocks.apiGet.mockResolvedValue({
    data: {
      success: true,
      data: { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 },
      error: null,
    },
  });
  useRHSelectionStore.setState({ selections: {} });
});

describe("RhInspectorMensualModal — browse de liquidaciones existentes", () => {
  it("expone el acceso al browse aunque NO haya candidatas", async () => {
    await irAlPasoSeleccion();

    expect(
      screen.getByRole("button", { name: /Ver liquidaciones existentes/ }),
    ).toBeInTheDocument();
  });

  it("abre el browse de liquidaciones existentes desde el paso 2", async () => {
    await irAlPasoSeleccion();

    fireEvent.click(
      screen.getByRole("button", { name: /Ver liquidaciones existentes/ }),
    );

    await waitFor(() =>
      expect(screen.getByText("Liquidaciones existentes")).toBeInTheDocument(),
    );
  });

  it("el browse no emite ninguna escritura (no crea revisiones)", async () => {
    await irAlPasoSeleccion();

    fireEvent.click(
      screen.getByRole("button", { name: /Ver liquidaciones existentes/ }),
    );

    await waitFor(() => expect(mocks.apiGet).toHaveBeenCalled());

    expect(mocks.apiPost).not.toHaveBeenCalled();
    expect(mocks.apiPatch).not.toHaveBeenCalled();
    expect(mocks.apiPut).not.toHaveBeenCalled();
    expect(mocks.apiDelete).not.toHaveBeenCalled();
  });
});
