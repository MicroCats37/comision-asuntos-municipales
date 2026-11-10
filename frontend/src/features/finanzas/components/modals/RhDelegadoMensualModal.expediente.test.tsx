/**
 * RhDelegadoMensualModal — `expediente` en el payload del RH (WU2b).
 *
 * Contrato de la capability `rh-mensual-browse-edit` (rework atómico):
 * - la grid de CANDIDATAS muestra el expediente de solo lectura;
 * - la grid de SELECCIONADAS lo muestra como campo editable;
 * - el expediente editado viaja DENTRO del payload del RH (creación y edición):
 *   el backend lo persiste en la MISMA transacción que la mutación del RH;
 * - el wizard NO emite ninguna escritura de expediente posterior al guardado
 *   (nada de `PATCH /liquidaciones/generales/{id}`);
 * - un 409 del guardado del RH (PAGADA) se muestra en el wizard, sin éxito
 *   falso, sin escritura extra y sin reintento automático; los borradores se
 *   conservan para que el usuario corrija y reintente.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la verificación
 * corre en la fase final de SDD (tarea 5.4).
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  cotizar: vi.fn(),
  crear: vi.fn(),
  actualizar: vi.fn(),
  refetch: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  notifyError: vi.fn(),
  notifySuccess: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
    post: mocks.apiPost,
    patch: mocks.apiPatch,
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("@/features/finanzas/hooks/useRHEditDelegadoDetalleRows", () => ({
  useRHEditDelegadoDetalleRows: () => ({
    rowsByDetalleId: new Map<string, unknown>(),
    isLoading: false,
  }),
}));

vi.mock("@/features/finanzas/hooks/useRHDelegadoMensual", () => ({
  useCotizarRHDelegado: () => ({ cotizar: mocks.cotizar, isPending: false }),
  useCrearRHDelegado: () => ({ crear: mocks.crear, isPending: false }),
  useActualizarRHDelegado: () => ({
    actualizar: mocks.actualizar,
    isPending: false,
  }),
}));

vi.mock("@/features/finanzas/hooks/useCandidatasDelegado", () => ({
  useCandidatasDelegado: () => {
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
        comprobante_activo: null,
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

// Se conserva el `handleApiError` real (parsea el envelope del backend) y sólo
// se espía el toast.
vi.mock("@/errors", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/errors")>();
  return {
    ...actual,
    notify: { error: mocks.notifyError, success: mocks.notifySuccess },
  };
});

import { RhDelegadoMensualModal } from "./RhDelegadoMensualModal";
import { useRHSelectionStore } from "@/features/finanzas/stores/rh-selection.store";

/** Cotización simulada (paso 3). */
const COTIZAR = {
  delegado: {
    id: "delegado-1",
    nombre_completo: "Delegado Uno",
    cip: "100001",
  },
  periodo: 2026,
  mes: 10,
  items: [
    {
      exp_liqui: "EXP-002",
      liquidacion_delegado_id: "asignacion-1",
      imp_bruto: 1000,
      renta_cip: 250,
      aporte_codemu: 50,
      fondo_comun: 100,
      neto_honorario: 600,
      total_liquidacion: 5900,
      sub_total_liquidacion: 5000,
    },
  ],
  totales: {
    sub_total: 1000,
    renta_cip: 250,
    aporte_codemu: 50,
    fondo_comun: 100,
    neto_honorario: 600,
  },
  variables_calculo: {
    tasa_renta_cip: 0.25,
    tasa_aporte_codemu: 0.05,
    tasa_fondo_comun: 0.1,
  },
};

/**
 * Error 409 del backend: liquidación PAGADA (no editable).
 *
 * El RH se guarda de forma ATÓMICA: si el expediente no se puede cambiar, no
 * se persiste NI el RH NI el expediente.
 */
function conflictoPagada(): unknown {
  return Object.assign(new Error("Request failed with status code 409"), {
    isAxiosError: true,
    response: {
      status: 409,
      data: {
        success: false,
        data: null,
        error: {
          code: "LIQUIDACION_PAGADA_NOT_EDITABLE",
          message:
            "No se puede editar una liquidación en estado PAGADA. Solo las liquidaciones PENDIENTE son editables.",
        },
      },
    },
  });
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

  await waitFor(() =>
    expect(document.getElementById("card-lg-2")).toBeInTheDocument(),
  );
}

/** Marca la candidata disponible del grid inferior. */
function marcarCandidata() {
  const checkbox = document.getElementById("card-lg-2");
  if (!checkbox) throw new Error("No se encontró la candidata disponible");
  fireEvent.click(checkbox);
}

/**
 * Selecciona la candidata, edita el expediente (si se indica) y llega al
 * paso 3 (confirmación). Devuelve el mock de `onOpenChange` para poder
 * comprobar que el wizard NO se cerró.
 */
async function irAlPasoConfirmacion(expediente?: string) {
  const onOpenChange = vi.fn();
  render(<RhDelegadoMensualModal open onOpenChange={onOpenChange} />);

  fireEvent.change(screen.getByLabelText("CIP del Delegado"), {
    target: { value: "100001" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Seleccionar operatividad" }),
  );
  fireEvent.click(screen.getByRole("button", { name: /Buscar Candidatas/ }));

  await waitFor(() =>
    expect(document.getElementById("card-lg-2")).toBeInTheDocument(),
  );

  marcarCandidata();
  await waitFor(() =>
    expect(document.getElementById("sel-expediente-lg-2")).toBeInTheDocument(),
  );
  if (expediente !== undefined) {
    fireEvent.change(document.getElementById("sel-expediente-lg-2")!, {
      target: { value: expediente },
    });
  }
  fireEvent.click(screen.getByRole("button", { name: /Cotizar/ }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /Crear RH/ })).toBeInTheDocument(),
  );

  return onOpenChange;
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.refetch.mockResolvedValue(undefined);
  mocks.cotizar.mockResolvedValue({ data: COTIZAR });
  mocks.crear.mockResolvedValue({ success: true, data: {} });
  mocks.actualizar.mockResolvedValue({ success: true, data: {} });
  useRHSelectionStore.setState({ selections: {} });
});

describe("RhDelegadoMensualModal — alcance del campo expediente", () => {
  it("la grid de CANDIDATAS muestra el expediente de solo lectura", async () => {
    await irAlPasoSeleccion();

    // El expediente aparece como texto, no como campo editable.
    expect(screen.getByText("EXP-002")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("EXP-002")).toBeNull();
    expect(document.getElementById("sel-expediente-lg-2")).toBeNull();
  });

  it("la grid de SELECCIONADAS muestra el expediente como campo editable", async () => {
    await irAlPasoSeleccion();
    marcarCandidata();

    await waitFor(() =>
      expect(document.getElementById("sel-expediente-lg-2")).toBeInTheDocument(),
    );

    expect(document.getElementById("sel-expediente-lg-2")).toHaveValue("EXP-002");
  });
});

describe("RhDelegadoMensualModal — el expediente viaja en el payload del RH", () => {
  it("incluye el expediente editado en el payload de creación", async () => {
    await irAlPasoConfirmacion("EXP-NUEVO");

    fireEvent.click(screen.getByRole("button", { name: /Crear RH/ }));

    await waitFor(() => expect(mocks.crear).toHaveBeenCalledTimes(1));

    const payload = mocks.crear.mock.calls[0][0];
    expect(payload.items).toHaveLength(1);
    expect(payload.items[0]).toMatchObject({
      liquidacion_general_id: "lg-2",
      expediente: "EXP-NUEVO",
    });
  });

  it("incluye el expediente persistido en las filas que el usuario no editó", async () => {
    await irAlPasoConfirmacion();

    fireEvent.click(screen.getByRole("button", { name: /Crear RH/ }));

    await waitFor(() => expect(mocks.crear).toHaveBeenCalledTimes(1));

    // Sin borrador se envía el valor persistido: el backend lo trata como
    // no-op (no escribe nada).
    const payload = mocks.crear.mock.calls[0][0];
    expect(payload.items[0].expediente).toBe("EXP-002");
  });

  it("envía el string vacío cuando el usuario limpia el expediente", async () => {
    await irAlPasoConfirmacion("");

    fireEvent.click(screen.getByRole("button", { name: /Crear RH/ }));

    await waitFor(() => expect(mocks.crear).toHaveBeenCalledTimes(1));

    const payload = mocks.crear.mock.calls[0][0];
    expect(payload.items[0].expediente).toBe("");
  });

  it("no emite ninguna escritura de expediente posterior al guardado", async () => {
    await irAlPasoConfirmacion("EXP-NUEVO");

    fireEvent.click(screen.getByRole("button", { name: /Crear RH/ }));

    await waitFor(() => expect(mocks.crear).toHaveBeenCalledTimes(1));

    // El único PATCH del contrato genérico de liquidaciones NO se invoca:
    // el expediente viaja en el payload del RH.
    expect(mocks.apiPatch).not.toHaveBeenCalled();
    expect(mocks.apiPost).not.toHaveBeenCalled();
    expect(mocks.actualizar).not.toHaveBeenCalled();
  });
});

describe("RhDelegadoMensualModal — 409 del guardado del RH", () => {
  it("muestra el error en el wizard sin éxito falso ni reintento automático", async () => {
    mocks.crear.mockRejectedValue(conflictoPagada());

    const onOpenChange = await irAlPasoConfirmacion("EXP-NUEVO");

    fireEvent.click(screen.getByRole("button", { name: /Crear RH/ }));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("PAGADA");

    // Un solo intento: no hay reintento automático.
    expect(mocks.crear).toHaveBeenCalledTimes(1);
    // Sin escritura extra de expediente.
    expect(mocks.apiPatch).not.toHaveBeenCalled();
    // El wizard sigue abierto: no se reporta un éxito falso.
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });

  it("conserva el borrador del expediente para que el usuario pueda corregirlo", async () => {
    mocks.crear.mockRejectedValue(conflictoPagada());

    await irAlPasoConfirmacion("EXP-NUEVO");

    fireEvent.click(screen.getByRole("button", { name: /Crear RH/ }));

    await screen.findByRole("alert");

    // Al volver al paso 2 el borrador sigue ahí: nada se perdió.
    fireEvent.click(screen.getByRole("button", { name: "Atrás" }));
    await waitFor(() =>
      expect(document.getElementById("sel-expediente-lg-2")).toBeInTheDocument(),
    );
    expect(document.getElementById("sel-expediente-lg-2")).toHaveValue("EXP-NUEVO");
  });
});
