/**
 * RhInspectorMensualModal — acción "Gestionar comprobante" en el paso 2 (WU4).
 *
 * Contrato de la capability `rh-mensual-browse-edit`:
 * - la fila SELECCIONADA del paso 2 ofrece la acción "Gestionar comprobante";
 * - la acción apunta a la `LiquidacionGeneral` EXACTA de esa fila (la candidata
 *   ya trae `liquidacion_general_id`), sin ambigüedad de destino;
 * - la operación NO crea una revisión (el número de revisión no cambia);
 * - tras guardar se refresca el query de candidatas y la columna "Comprobante"
 *   refleja el comprobante vigente;
 * - la EDICIÓN del comprobante vigente es un PATCH in-place (no un POST): el
 *   wizard delega la escritura en el modal ÚNICO y sólo le entrega la
 *   liquidación exacta, con su comprobante vigente.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la verificación
 * corre en la fase final de SDD (tarea 5.4).
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { beforeEach, describe, expect, it, vi } from "vitest";

/** Comprobante que devuelve el detalle de la liquidación objetivo. */
interface ComprobanteDetalle {
  id: string;
  tipo_comprobante: string;
  serie: string;
  numero: string;
  fecha_emision: string;
  monto: number;
  activo: boolean;
  motivo_reemplazo: string | null;
}

const mocks = vi.hoisted(() => ({
  cotizar: vi.fn(),
  crear: vi.fn(),
  actualizar: vi.fn(),
  refetch: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiPut: vi.fn(),
  notifyError: vi.fn(),
  notifySuccess: vi.fn(),
  /**
   * Comprobantes que devuelve el detalle de la liquidación objetivo.
   * Por defecto la liquidación NO tiene vigente (el flujo arranca en el alta).
   */
  comprobantesDetalle: [] as Array<{
    id: string;
    tipo_comprobante: string;
    serie: string;
    numero: string;
    fecha_emision: string;
    monto: number;
    activo: boolean;
    motivo_reemplazo: string | null;
  }>,
}));

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
    post: mocks.apiPost,
    patch: mocks.apiPatch,
    put: mocks.apiPut,
    delete: vi.fn(),
  },
}));

vi.mock("@/features/finanzas/hooks/useRHInspectorMensual", () => ({
  useCotizarRHInspector: () => ({ cotizar: mocks.cotizar, isPending: false }),
  useCotizarEdicionRHInspector: () => ({
    cotizar: mocks.cotizar,
    isPending: false,
  }),
  useCrearRHInspector: () => ({ crear: mocks.crear, isPending: false }),
  useActualizarRHInspector: () => ({
    actualizar: mocks.actualizar,
    isPending: false,
  }),
}));

/**
 * Una candidata con `liquidacion_general_id` explícito (identidad exacta de la
 * liquidación objetivo del comprobante).
 */
vi.mock("@/features/finanzas/hooks/useCandidatasInspector", () => ({
  useCandidatasInspector: () => {
    const vigente = mocks.comprobantesDetalle.find((c) => c.activo);
    const items = [
      {
        liquidacion_inspector_id: "li-1",
        liquidacion_categoria_visitas_id: "lcv-1",
        liquidacion_general_id: "lg-1",
        expediente: "EXP-001",
        numero_revision: 1,
        fecha_registro: "2026-10-01",
        inspector_nombre: "Inspector Uno",
        inspector_cip: "200002",
        inspector_dni: "200002",
        especialidad_nombre: "Arquitectura",
        nombre_propietario: "Propietario Uno",
        cantidad_visitas: 4,
        inspecciones_pagadas: 1,
        saldo_disponible: 3,
        costo_por_inspeccion: 500,
        total_liquidacion: 2000,
        sub_total_liquidacion: 2000,
        liquidacion_especifica_numero: 77,
        comprobante_activo: vigente
          ? {
              tipo_comprobante: vigente.tipo_comprobante,
              serie: vigente.serie,
              numero: vigente.numero,
              fecha_emision: vigente.fecha_emision,
            }
          : null,
      },
    ];

    return {
      data: {
        inspector_id: "insp-1",
        inspector_nombre: "Inspector Uno",
        inspector_cip: "200002",
        inspector_dni: "200002",
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

/** Detalle de la liquidación objetivo (historial de comprobantes). */
vi.mock("@/features/liquidaciones/hooks/useLiquidacionGeneralDetalle", () => ({
  useLiquidacionGeneralDetalle: ({ id }: { id: string | null }) => ({
    data: id
      ? {
          liquidacion_general: {
            id,
            estado: "PENDIENTE",
            total: 2000,
            sub_total: 2000,
            numero_revision: 1,
            fecha_registro: "2026-10-01",
            comprobantes: mocks.comprobantesDetalle,
          },
          liquidacion_especifica: { id: "le-1", numero: 77 },
          liquidacion_tipo: null,
        }
      : null,
    isLoading: false,
  }),
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

/**
 * El flujo de comprobante se stubbea: el wizard lo integra (recibe la
 * liquidación objetivo y dispara `onSuccess` con la liquidación actualizada).
 *
 * El stub NO declara prop `modo`: el modal público es ÚNICO y deriva su vista
 * del comprobante vigente. `comprobante-vigente` deja ver si la liquidación
 * que entrega el wizard trae ese vigente (⇒ ruta de EDICIÓN) o no (⇒ alta).
 */
vi.mock("@/features/liquidaciones/components/forms", () => ({
  ComprobanteFormModal: ({
    open,
    liquidacionGeneral,
    onSuccess,
  }: {
    open: boolean;
    liquidacionGeneral: {
      id: string;
      comprobantes?: Array<{ activo?: boolean }>;
    };
    onSuccess?: (updated: unknown) => void;
  }) =>
    open ? (
      <div data-testid="comprobante-modal">
        <span>{`objetivo:${liquidacionGeneral.id}`}</span>
        <span data-testid="comprobante-vigente">
          {liquidacionGeneral.comprobantes?.some((c) => c.activo)
            ? "si"
            : "no"}
        </span>
        <button
          type="button"
          onClick={() =>
            onSuccess?.({
              id: liquidacionGeneral.id,
              comprobantes: [
                {
                  id: "c-2",
                  tipo_comprobante: "FACTURA",
                  serie: "F003",
                  numero: "77",
                  fecha_emision: "2026-02-01",
                  monto: 2000,
                  activo: true,
                  motivo_reemplazo: null,
                },
              ],
            })
          }
        >
          Guardar comprobante
        </button>
      </div>
    ) : null,
}));

// Se conserva el `handleApiError` real (parsea el envelope del backend) y sólo
// se espía el toast.
vi.mock("@/errors", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/errors")>();
  return {
    ...actual,
    notify: { error: mocks.notifyError, success: mocks.notifySuccess },
  };
});

import { RhInspectorMensualModal } from "./RhInspectorMensualModal";
import { useRHSelectionStore } from "@/features/finanzas/stores/rh-selection.store";

/** Lleva el wizard (modo creación) al paso 2 con la candidata SELECCIONADA. */
async function irAlPasoSeleccionConFilaSeleccionada() {
  render(<RhInspectorMensualModal open onOpenChange={vi.fn()} />);

  fireEvent.change(screen.getByLabelText("CIP del Inspector"), {
    target: { value: "200002" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Seleccionar operatividad" }),
  );
  fireEvent.click(screen.getByRole("button", { name: /Buscar Candidatas/ }));

  await waitFor(() =>
    expect(document.getElementById("row-lcv-1")).toBeInTheDocument(),
  );

  fireEvent.click(document.getElementById("row-lcv-1")!);

  await waitFor(() =>
    expect(document.getElementById("sel-expediente-lcv-1")).toBeInTheDocument(),
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.refetch.mockResolvedValue(undefined);
  mocks.comprobantesDetalle = [];
  useRHSelectionStore.setState({ selections: {} });
});

/** Fuente del wizard del RH Inspector (guardas de arquitectura). */
function leerFuenteWizard(): string {
  return readFileSync(
    fileURLToPath(new URL("./RhInspectorMensualModal.tsx", import.meta.url)),
    "utf8",
  );
}

/** Fuente del hook de edición del comprobante (guarda del PATCH). */
function leerFuenteHookEditar(): string {
  return readFileSync(
    fileURLToPath(
      new URL(
        "../../../liquidaciones/hooks/useEditarComprobante.ts",
        import.meta.url,
      ),
    ),
    "utf8",
  );
}

/** Comprobante VIGENTE de la liquidación objetivo (ruta de EDICIÓN). */
const COMPROBANTE_VIGENTE: ComprobanteDetalle = {
  id: "c-1",
  tipo_comprobante: "FACTURA",
  serie: "F001",
  numero: "77",
  fecha_emision: "2026-10-05",
  monto: 2000,
  activo: true,
  motivo_reemplazo: null,
};

describe("RhInspectorMensualModal — acción de comprobante del paso 2", () => {
  it("expone la acción sólo en la fila SELECCIONADA", async () => {
    await irAlPasoSeleccionConFilaSeleccionada();

    expect(
      screen.getByRole("button", { name: "Gestionar comprobante" }),
    ).toBeInTheDocument();
  });

  it("abre el flujo de comprobante sobre la liquidación exacta de la fila", async () => {
    await irAlPasoSeleccionConFilaSeleccionada();

    fireEvent.click(
      screen.getByRole("button", { name: "Gestionar comprobante" }),
    );

    await waitFor(() =>
      expect(screen.getByTestId("comprobante-modal")).toBeInTheDocument(),
    );
    // El objetivo es la LiquidacionGeneral de la fila.
    expect(screen.getByTestId("comprobante-modal")).toHaveTextContent(
      "objetivo:lg-1",
    );
  });

  it("refresca las candidatas y muestra el comprobante vigente tras guardar", async () => {
    await irAlPasoSeleccionConFilaSeleccionada();

    fireEvent.click(
      screen.getByRole("button", { name: "Gestionar comprobante" }),
    );
    await waitFor(() =>
      expect(screen.getByTestId("comprobante-modal")).toBeInTheDocument(),
    );

    const llamadasAntes = mocks.refetch.mock.calls.length;

    fireEvent.click(screen.getByRole("button", { name: "Guardar comprobante" }));

    // Refetch EXPLÍCITO del query de candidatas.
    await waitFor(() =>
      expect(mocks.refetch.mock.calls.length).toBeGreaterThan(llamadasAntes),
    );
    // La columna "Comprobante" de la fila seleccionada refleja el comprobante
    // vigente que devuelve el backend.
    await waitFor(() => expect(screen.getByText("F003-77")).toBeInTheDocument());
    expect(screen.queryByText("Sin comprobante")).toBeNull();
  });

  it("no crea revisiones", async () => {
    // Guard de fuente: el wizard del RH nunca invoca la mutación de nueva
    // revisión (la acción de comprobante es otro flujo, reutilizado).
    const source = leerFuenteWizard();
    expect(source).not.toMatch(/useCrearNuevaRevision/);
    expect(source).not.toMatch(/nueva-revision/);
    expect(source).not.toMatch(/nueva_revision/);

    await irAlPasoSeleccionConFilaSeleccionada();

    fireEvent.click(
      screen.getByRole("button", { name: "Gestionar comprobante" }),
    );
    await waitFor(() =>
      expect(screen.getByTestId("comprobante-modal")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: "Guardar comprobante" }));

    const urls = [
      ...mocks.apiPost.mock.calls,
      ...mocks.apiPatch.mock.calls,
      ...mocks.apiPut.mock.calls,
    ].map((llamada) => String(llamada[0]));
    expect(urls.some((url) => url.includes("revision"))).toBe(false);
  });
});

/**
 * EDICIÓN del comprobante vigente desde el RH mensual.
 *
 * El wizard NO implementa el flujo de edición: monta el modal ÚNICO y le
 * entrega la liquidación exacta CON su comprobante vigente. De ahí que el
 * modal derive la ruta de EDICIÓN (un PATCH in-place del activo) y no la de
 * ALTA (un POST).
 */
describe("RhInspectorMensualModal — edición del comprobante vigente", () => {
  it("entrega al modal la liquidación CON su comprobante vigente (ruta de edición)", async () => {
    mocks.comprobantesDetalle = [COMPROBANTE_VIGENTE];

    await irAlPasoSeleccionConFilaSeleccionada();

    // La fila ya muestra el comprobante vigente.
    expect(screen.getAllByText("F001-77").length).toBeGreaterThan(0);

    fireEvent.click(
      screen.getByRole("button", { name: "Gestionar comprobante" }),
    );
    await waitFor(() =>
      expect(screen.getByTestId("comprobante-modal")).toBeInTheDocument(),
    );

    // El modal recibe la liquidación exacta Y su vigente: el modal único deriva
    // de ahí la vista de EDICIÓN (no la de alta).
    expect(screen.getByTestId("comprobante-modal")).toHaveTextContent(
      "objetivo:lg-1",
    );
    expect(screen.getByTestId("comprobante-vigente")).toHaveTextContent("si");
  });

  it("sin comprobante vigente el modal único arranca en la ruta de ALTA", async () => {
    await irAlPasoSeleccionConFilaSeleccionada();

    fireEvent.click(
      screen.getByRole("button", { name: "Gestionar comprobante" }),
    );
    await waitFor(() =>
      expect(screen.getByTestId("comprobante-modal")).toBeInTheDocument(),
    );

    expect(screen.getByTestId("comprobante-vigente")).toHaveTextContent("no");
  });

  it("la edición del vigente emite un PATCH y NINGÚN POST", () => {
    const wizard = leerFuenteWizard();

    // 1) El wizard delega la escritura: no conoce los hooks de comprobante ni
    //    escribe contra la API por su cuenta.
    expect(wizard).not.toMatch(/useCrearComprobante/);
    expect(wizard).not.toMatch(/useEditarComprobante/);
    expect(wizard).not.toMatch(/api\.(post|patch|put|delete)\(/);

    // 2) Monta UN SOLO `ComprobanteFormModal` y SIN selector de modo: el
    //    modal decide sola si es alta o edición a partir del vigente.
    expect(wizard.match(/<ComprobanteFormModal/g) ?? []).toHaveLength(1);
    expect(wizard).not.toMatch(/\bmodo=/);

    // 3) La ruta de EDICIÓN del modal único es un PATCH in-place del activo
    //    (nunca un POST de alta).
    const hook = leerFuenteHookEditar();
    expect(hook).toContain("api.patch(");
    expect(hook).toContain("/comprobante/${comprobanteId}");
    expect(hook).not.toContain("api.post(");
  });
});
