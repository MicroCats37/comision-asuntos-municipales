/**
 * RhInspectorMensualModal — `expediente` en el payload del RH (WU2b).
 *
 * Contrato de la capability `rh-mensual-browse-edit` (rework atómico):
 * - la grid de CANDIDATAS muestra el expediente de solo lectura;
 * - la grid de SELECCIONADAS lo muestra como campo editable;
 * - el expediente editado viaja DENTRO del payload del RH (creación y edición):
 *   el backend lo persiste en la MISMA transacción que la mutación del RH;
 * - `exp_liqui` sigue siendo SIEMPRE el valor PERSISTIDO (identifica la
 *   liquidación): el valor editado viaja en `expediente`;
 * - el wizard NO emite ninguna escritura de expediente posterior al guardado
 *   (nada de `PATCH /liquidaciones/generales/{id}`);
 * - un 409 del guardado del RH (PAGADA) se muestra en el wizard, sin éxito
 *   falso, sin escritura extra y sin reintento automático.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la verificación
 * corre en la fase final de SDD (tarea 5.4).
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReciboHonorarioInspectorMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";

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

vi.mock("@/features/finanzas/hooks/useCandidatasInspector", () => ({
  useCandidatasInspector: () => {
    const items = [
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
        liquidacion_especifica_numero: 77,
        comprobante_activo: null,
      },
    ];

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

/** Cotización simulada (paso 3). */
const COTIZAR = {
  inspector: {
    id: "insp-1",
    nombre_completo: "Inspector Uno",
    cip: "100001",
    dni: "100001",
  },
  periodo: 2026,
  mes: 10,
  items: [
    {
      exp_liqui: "EXP-001",
      liquidacion_inspector_id: "li-1",
      liquidacion_categoria_visitas_id: "lcv-1",
      nombre_propietario: "Propietario Uno",
      importe_bruto: 2000,
      inspecciones_programadas: 4,
      inspecciones_liquidadas: 2,
      inspecciones_pagadas_hasta_mes_anterior: 1,
      costo_por_inspeccion: 500,
      monto_contribuido: 2000,
      saldo_restante: 2,
      sub_total: 2000,
      descuento: 0,
      honorarios: 2000,
      liquidacion_especifica_numero: 77,
      comprobante_activo: null,
    },
  ],
  totales: {
    sub_total: 2000,
    descuento: 0,
    honorarios: 2000,
    tasa_descuento_aplicada: 0,
  },
  escala_descripcion_id: "escala-1",
  variables_calculo: {
    escala_id: "escala-1",
    escala_nombre: "Escala Uno",
    rango_aplicado: {
      monto_minimo: 0,
      monto_maximo: 10000,
      porcentaje_descuento: 0,
    },
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

/** RH persistido (modo edición). */
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
    inspecciones_programadas: 4,
    inspecciones_liquidadas: 2,
    inspecciones_pagadas_hasta_mes_anterior: 1,
    saldo_restante: 2,
    sub_total: 2000,
    descuento: 0,
    honorarios: 2000,
    tasa_descuento_aplicada: 0,
  },
  detalles: [
    {
      detalle_id: "detalle-1",
      expediente: "EXP-001",
      nombre_propietario: "Propietario Uno",
      importe_bruto: 2000,
      inspecciones_programadas: 4,
      inspecciones_liquidadas: 2,
      inspecciones_pagadas_hasta_mes_anterior: 1,
      costo_por_inspeccion: 500,
      monto_contribuido: 2000,
      saldo_restante: 2,
      sub_total: 2000,
      descuento: 0,
      honorarios: 2000,
      liquidacion_especifica_numero: 77,
      numero_revision: 1,
    },
  ],
} as unknown as ReciboHonorarioInspectorMensual;

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

  await waitFor(() =>
    expect(document.getElementById("row-lcv-1")).toBeInTheDocument(),
  );
}

/** Marca la candidata disponible del grid inferior. */
function marcarCandidata() {
  const checkbox = document.getElementById("row-lcv-1");
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
  render(<RhInspectorMensualModal open onOpenChange={onOpenChange} />);

  fireEvent.change(screen.getByLabelText("CIP del Inspector"), {
    target: { value: "100001" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Seleccionar operatividad" }),
  );
  fireEvent.click(screen.getByRole("button", { name: /Buscar Candidatas/ }));

  await waitFor(() =>
    expect(document.getElementById("row-lcv-1")).toBeInTheDocument(),
  );

  marcarCandidata();
  await waitFor(() =>
    expect(document.getElementById("sel-expediente-lcv-1")).toBeInTheDocument(),
  );
  if (expediente !== undefined) {
    fireEvent.change(document.getElementById("sel-expediente-lcv-1")!, {
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

describe("RhInspectorMensualModal — alcance del campo expediente", () => {
  it("la grid de CANDIDATAS muestra el expediente de solo lectura", async () => {
    await irAlPasoSeleccion();

    // El expediente aparece como texto, no como campo editable.
    expect(screen.getByText("EXP-001")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("EXP-001")).toBeNull();
    expect(document.getElementById("sel-expediente-lcv-1")).toBeNull();
  });

  it("la grid de SELECCIONADAS muestra el expediente como campo editable", async () => {
    await irAlPasoSeleccion();
    marcarCandidata();

    await waitFor(() =>
      expect(document.getElementById("sel-expediente-lcv-1")).toBeInTheDocument(),
    );

    expect(document.getElementById("sel-expediente-lcv-1")).toHaveValue("EXP-001");
  });
});

describe("RhInspectorMensualModal — el expediente viaja en el payload del RH", () => {
  it("incluye el expediente editado en el payload de creación", async () => {
    await irAlPasoConfirmacion("EXP-NUEVO");

    fireEvent.click(screen.getByRole("button", { name: /Crear RH/ }));

    await waitFor(() => expect(mocks.crear).toHaveBeenCalledTimes(1));

    const payload = mocks.crear.mock.calls[0][0];
    expect(payload.items).toHaveLength(1);
    expect(payload.items[0]).toMatchObject({
      liquidacion_categoria_visitas_id: "lcv-1",
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
    expect(payload.items[0].expediente).toBe("EXP-001");
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

describe("RhInspectorMensualModal — modo edición", () => {
  it("envía el expediente editado y conserva el exp_liqui persistido", async () => {
    render(
      <RhInspectorMensualModal
        open
        onOpenChange={vi.fn()}
        editContext={{ rh }}
      />,
    );

    const input = await screen.findByLabelText(
      "Expediente de la liquidación seleccionada",
    );
    fireEvent.change(input, { target: { value: "EXP-NUEVO" } });

    fireEvent.click(screen.getByRole("button", { name: /Cotizar \(1\)/ }));
    await waitFor(() => expect(mocks.cotizar).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(mocks.actualizar).toHaveBeenCalledTimes(1));

    const payload = mocks.actualizar.mock.calls[0][0];
    expect(payload.items).toHaveLength(1);
    // `exp_liqui` sigue siendo el valor PERSISTIDO (identifica la liquidación).
    expect(payload.items[0]).toMatchObject({
      exp_liqui: "EXP-001",
      detalle_id: "detalle-1",
      expediente: "EXP-NUEVO",
    });
  });

  it("no emite ninguna escritura de expediente en el modo edición", async () => {
    render(
      <RhInspectorMensualModal
        open
        onOpenChange={vi.fn()}
        editContext={{ rh }}
      />,
    );

    await screen.findByLabelText(
      "Expediente de la liquidación seleccionada",
    );

    fireEvent.click(screen.getByRole("button", { name: /Cotizar \(1\)/ }));
    await waitFor(() => expect(mocks.cotizar).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(mocks.actualizar).toHaveBeenCalledTimes(1));

    expect(mocks.apiPatch).not.toHaveBeenCalled();
    expect(mocks.apiPost).not.toHaveBeenCalled();
  });
});

describe("RhInspectorMensualModal — 409 del guardado del RH", () => {
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
});
