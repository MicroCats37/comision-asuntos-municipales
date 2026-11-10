/**
 * RhDelegadoMensualModal — acceso al browse de liquidaciones existentes.
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

vi.mock("@/features/finanzas/hooks/useRHEditDelegadoDetalleRows", () => ({
  useRHEditDelegadoDetalleRows: () => ({
    rowsByDetalleId: new Map<string, unknown>(),
    isLoading: false,
  }),
}));

vi.mock("@/features/finanzas/hooks/useRHDelegadoMensual", () => ({
  useCotizarRHDelegado: () => ({ cotizar: vi.fn(), isPending: false }),
  useCrearRHDelegado: () => ({ crear: vi.fn(), isPending: false }),
  useActualizarRHDelegado: () => ({ actualizar: vi.fn(), isPending: false }),
}));

/** El wizard arranca SIN candidatas: el browse es la única salida. */
vi.mock("@/features/finanzas/hooks/useCandidatasDelegado", () => ({
  useCandidatasDelegado: () => ({
    data: {
      delegado: {
        id: "delegado-1",
        cip: "100001",
        dni: "100001",
        nombre_completo: "Delegado Uno",
      },
      items: [],
      candidatas: [],
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

import { RhDelegadoMensualModal } from "./RhDelegadoMensualModal";
import { useRHSelectionStore } from "@/features/finanzas/stores/rh-selection.store";

/** Lleva el wizard (modo creación) del paso 1 al paso 2. */
async function irAlPasoSeleccion() {
  // El browse usa TanStack Query: el harness necesita su QueryClient.
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <RhDelegadoMensualModal open onOpenChange={vi.fn()} />
    </QueryClientProvider>,
  );

  fireEvent.change(screen.getByLabelText("CIP del Delegado"), {
    target: { value: "100001" },
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

describe("RhDelegadoMensualModal — browse de liquidaciones existentes", () => {
  it("expone el acceso al browse aunque NO haya candidatas", async () => {
    await irAlPasoSeleccion();

    // No hay ninguna candidata en el paso 2…
    expect(screen.queryByText("EXP-002")).toBeNull();
    // …pero el browse está disponible.
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
