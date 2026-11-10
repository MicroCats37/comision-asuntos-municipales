/**
 * LiquidacionDelegadoDetailModal — detalle de SOLO LECTURA de las
 * asignaciones de delegado + remoción CONFIRMADA por delegado.
 *
 * Slice S7 de `liquidacion-delegado-detail-modal-apply-readiness`
 * (corrección de UX solicitada por el usuario: el modal deja de ser un
 * editor de tarjetas y pasa a ser una tabla de solo lectura con una única
 * acción "Quitar delegado" por delegado, protegida por confirmación).
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la verificación
 * corre en el módulo de verificación final (tarea "Módulo de verificación
 * final" de `tasks.md`).
 *
 * Contrato que fijan:
 * - el cuerpo es una TABLA con una fila por ASIGNACIÓN, en solo lectura
 *   (sin inputs, sin selects, sin campos de fecha, sin acción de guardar);
 * - cada fila muestra la metadata de la asignación, el resumen del detalle
 *   RH y el estado/número del RH mensual enlazado;
 * - hay EXACTAMENTE UNA acción "Quitar delegado" por DELEGADO (no por
 *   asignación);
 * - la remoción pide CONFIRMACIÓN antes de emitir la petición: cancelar no
 *   lanza nada; confirmar lanza el PATCH de la rama `delete` del batch
 *   EXISTENTE;
 * - un 409 en la remoción se muestra INLINE y el delegado PERMANECE visible
 *   (nunca se oculta un fallo como éxito).
 *
 * Estilo de mocking: el de `GestionarDelegadosModal.quitar.test.tsx` (mock de
 * `@/lib/api`, `QueryClientProvider` con `retry: false`).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { LiquidacionGeneralOutput } from "../schemas/liquidacion-base.schema";
import { LiquidacionDelegadoDetailModal } from "./LiquidacionDelegadoDetailModal";

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiRequest: vi.fn(),
  notifyError: vi.fn(),
  notifySuccess: vi.fn(),
}));

// Réplica del layout real de `ModalShell`: el body (children) se renderiza
// tal cual. Se replica porque el modal real usa Radix Dialog + ScrollArea,
// que dependen de APIs de navegador no disponibles en jsdom (ResizeObserver).
//
// La CONFIRMACIÓN sí usa el componente real (`useConfirmationDialog` +
// `ConfirmationDialog`): es la primitiva compartida que hay que reutilizar.
vi.mock("@/components-app/forms/ModalShell", () => ({
  ModalShell: ({
    title,
    description,
    children,
  }: {
    title?: string;
    description?: string;
    children: ReactNode;
  }) => (
    <div>
      <h2>{title}</h2>
      <p>{description}</p>
      {children}
    </div>
  ),
}));

// Capa HTTP: el GET del detalle y el PATCH del batch.
vi.mock("@/lib/api", () => ({
  default: { get: mocks.apiGet, request: mocks.apiRequest },
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

// ── Fixtures ─────────────────────────────────────────────────────────────────

const LIQUIDACION_ID = "11111111-1111-4111-8111-111111111111";

const DELEGADO_UNO = {
  id: "delegado-1",
  cip: "100001",
  dni: "70000001",
  nombre_completo: "Delegado Uno",
};

const DELEGADO_DOS = {
  id: "delegado-2",
  cip: "100002",
  dni: "70000002",
  nombre_completo: "Delegado Dos",
};

/**
 * Asignación con detalle RH y RH mensual enlazado.
 *
 * Los importes del detalle y los del RH mensual son DISTINTOS a propósito:
 * así cada texto de la UI es inequívoco y las aserciones no dependen del
 * orden de render.
 */
const ASIGNACION_UNO = {
  id: "asignacion-1",
  liquidacion_id: LIQUIDACION_ID,
  delegado_id: "delegado-1",
  especialidad_revision: { id: "esp-1", nombre: "Arquitectura" },
  liquidacion: null,
  delegado: DELEGADO_UNO,
  periodo: 2026,
  mes: 7,
  dictamen_revision: "CONFORME",
  fecha_presentacion: "2026-07-01",
  fecha_revision: "2026-07-05",
  tipo: "TITULAR",
  numero_rh: "RH-000123",
  creado_por_rh: true,
  detalle_rh: [
    {
      id: "detalle-1",
      imp_bruto: 1000,
      sub_total: 900,
      renta_cip: 250,
      aporte_codemu: 50,
      fondo_comun: 100,
      neto_honorario: 500,
      recibo_mensual: {
        id: "recibo-1",
        numero: 42,
        periodo: 2026,
        mes: 7,
        fecha_registro: "2026-08-01T10:00:00Z",
        sub_total: 1800,
        renta_cip: 450,
        aporte_codemu: 90,
        fondo_comun: 180,
        neto_honorario: 1080,
      },
    },
  ],
};

/** Segunda asignación del MISMO delegado (otra `especialidad_revision`). */
const ASIGNACION_UNO_B = {
  ...ASIGNACION_UNO,
  id: "asignacion-1b",
  especialidad_revision: { id: "esp-2", nombre: "Ingeniería Civil" },
  detalle_rh: [],
};

/** Asignación de OTRO delegado (sin detalle RH y sin RH mensual). */
const ASIGNACION_DOS = {
  id: "asignacion-2",
  liquidacion_id: LIQUIDACION_ID,
  delegado_id: "delegado-2",
  especialidad_revision: { id: "esp-3", nombre: "Topografía" },
  liquidacion: null,
  delegado: DELEGADO_DOS,
  periodo: 2026,
  mes: 5,
  dictamen_revision: "PENDIENTE",
  fecha_presentacion: null,
  fecha_revision: null,
  tipo: "ALTERNO",
  numero_rh: null,
  creado_por_rh: false,
  detalle_rh: [],
};

function makeLiquidacion(): LiquidacionGeneralOutput {
  return {
    id: LIQUIDACION_ID,
    estado: "PENDIENTE",
    municipalidad: {
      id: "mun-1",
      codigo: "MUN01",
      nombre: "Municipalidad Uno",
    },
    usuario_creador: null,
    fecha_registro: "2026-08-01",
    expediente: "EXP-2026-0001",
    observacion: null,
    numero_revision: 1,
    sub_total: 4000,
    total: 4321.99,
    igv: null,
    uit: null,
    proyecto: {
      id: "proyecto-1",
      nombre_propietario: "Propietario Uno",
      direccion: "Av. Principal 123",
      urbanizacion: null,
      distrito: {
        id: "distrito-1",
        nombre: "Distrito Uno",
        ubigeo: null,
        provincia: null,
        departamento: null,
      },
      entidad: null,
    },
    denominacion_de_proyecto: "Edificio Central",
    contacto: null,
    tipo_liquidacion: { codigo: "EDIFICACION", nombre: "Edificación" },
    delegados: [],
    comprobantes: [],
  } as unknown as LiquidacionGeneralOutput;
}

/** Envelope `ApiResponse[LiquidacionDelegadoDetalleResponseOut]`. */
function detalleEnvelope(asignaciones: unknown[]) {
  return {
    success: true,
    data: { liquidacion_id: LIQUIDACION_ID, asignaciones },
    error: null,
    message: "Detalle de asignaciones.",
  };
}

/** Envelope `ApiResponse[LiquidacionDelegadoBatchOut]`. */
function successEnvelope(deleted: string[] = []) {
  return {
    success: true,
    data: { created: [], updated: [], deleted },
    error: null,
    message: "Delegados actualizados correctamente.",
  };
}

function conflictEnvelope(message: string) {
  return {
    response: {
      status: 409,
      data: {
        success: false,
        data: null,
        error: { code: "CONFLICT", message, details: null },
      },
    },
  };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function renderWithQueryClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return {
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
    ),
  };
}

function renderModal(asignaciones: unknown[] = [ASIGNACION_UNO, ASIGNACION_DOS]) {
  mocks.apiGet.mockResolvedValue({ data: detalleEnvelope(asignaciones) });
  return renderWithQueryClient(
    <LiquidacionDelegadoDetailModal
      open
      onOpenChange={vi.fn()}
      liquidacionGeneral={makeLiquidacion()}
      publicId="EDIF-2026-000001"
    />,
  );
}

/**
 * Filas de la tabla.
 *
 * La primera es la cabecera (`thead`); las siguientes son las asignaciones,
 * en el mismo orden en que llegan del endpoint.
 */
function filas(): HTMLElement[] {
  return within(screen.getByRole("table")).getAllByRole("row");
}

/** Fila de una asignación concreta (por su posición en la tabla). */
function filaDeAsignacion(indice: number) {
  return within(filas()[indice + 1]);
}

/** Botón de remoción de un delegado (nombre accesible exacto). */
function botonQuitar(nombre: string) {
  return screen.getByRole("button", { name: `Quitar delegado: ${nombre}` });
}

/** Botón de confirmación del diálogo compartido. */
function botonConfirmar() {
  return screen.getByRole("button", { name: "Quitar delegado" });
}

/** Botón de cancelación del diálogo compartido. */
function botonCancelar() {
  return screen.getByRole("button", { name: "Cancelar" });
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("LiquidacionDelegadoDetailModal", () => {
  beforeEach(() => {
    mocks.apiGet.mockReset();
    mocks.apiRequest.mockReset();
    mocks.notifyError.mockReset();
    mocks.notifySuccess.mockReset();
  });

  it("muestra una fila por asignacion contra el endpoint anidado", async () => {
    renderModal([ASIGNACION_UNO, ASIGNACION_UNO_B, ASIGNACION_DOS]);

    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());

    // 1 fila de cabecera + 1 fila por asignación.
    expect(filas()).toHaveLength(4);

    // La lectura va contra el endpoint anidado de la liquidación.
    expect(mocks.apiGet).toHaveBeenCalledWith(
      `/liquidaciones/${LIQUIDACION_ID}/delegados-asignaciones`,
      expect.anything(),
    );
  });

  it("la presentacion es de solo lectura: sin campos editables ni accion de guardar", async () => {
    renderModal([ASIGNACION_UNO]);

    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());

    // Ningún control editable en toda la vista.
    expect(document.querySelectorAll("input")).toHaveLength(0);
    expect(document.querySelectorAll("select")).toHaveLength(0);
    expect(document.querySelectorAll("textarea")).toHaveLength(0);

    // Y ninguna acción de guardado.
    expect(
      screen.queryByRole("button", { name: /guardar/i }),
    ).not.toBeInTheDocument();
  });

  it("muestra la metadata de la asignacion", async () => {
    renderModal([ASIGNACION_UNO]);

    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());

    const fila = filaDeAsignacion(0);
    expect(fila.getByText("Arquitectura")).toBeInTheDocument();
    expect(fila.getByText("TITULAR")).toBeInTheDocument();
    expect(fila.getByText("Creado por RH")).toBeInTheDocument();
    expect(fila.getByText("2026")).toBeInTheDocument();
    expect(fila.getByText("7")).toBeInTheDocument();
    expect(fila.getByText("Conforme")).toBeInTheDocument();
    expect(fila.getByText("RH-000123")).toBeInTheDocument();
    expect(fila.getByText("2026-07-01")).toBeInTheDocument();
    expect(fila.getByText("2026-07-05")).toBeInTheDocument();
  });

  it("muestra el resumen del detalle rh", async () => {
    renderModal([ASIGNACION_UNO]);

    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());

    const fila = filaDeAsignacion(0);
    expect(fila.getByText("Importe bruto")).toBeInTheDocument();
    expect(fila.getByText("S/ 1,000.00")).toBeInTheDocument();
    expect(fila.getByText("Neto del honorario")).toBeInTheDocument();
    expect(fila.getByText("S/ 500.00")).toBeInTheDocument();
    expect(fila.getByText("Renta CIP")).toBeInTheDocument();
    expect(fila.getByText("Aporte CODEMU")).toBeInTheDocument();
    expect(fila.getByText("Fondo común")).toBeInTheDocument();
  });

  it("muestra el estado y el numero del rh mensual enlazado", async () => {
    renderModal([ASIGNACION_UNO]);

    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());

    const fila = filaDeAsignacion(0);
    expect(fila.getByText("Enlazado")).toBeInTheDocument();
    expect(fila.getByText("N.º de RH mensual")).toBeInTheDocument();
    expect(fila.getByText("42")).toBeInTheDocument();

    // D4: el número de RH de la ASIGNACIÓN y el del RH MENSUAL no se mezclan.
    expect(fila.getByText("N.º RH (asignación)")).toBeInTheDocument();
    expect(fila.getByText("RH-000123")).toBeInTheDocument();
  });

  it("marca como sin rh mensual las asignaciones que no lo tienen", async () => {
    renderModal([ASIGNACION_UNO, ASIGNACION_DOS]);

    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());

    const fila = filaDeAsignacion(1);
    expect(fila.getByText("Sin RH mensual")).toBeInTheDocument();
    expect(fila.getByText("Sin detalle de honorario")).toBeInTheDocument();
  });

  it("un delegado con dos asignaciones muestra un solo boton de quitar", async () => {
    renderModal([ASIGNACION_UNO, ASIGNACION_UNO_B, ASIGNACION_DOS]);

    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());

    // Dos filas de ASIGNACIÓN para el mismo delegado...
    expect(filaDeAsignacion(0).getByText("Arquitectura")).toBeInTheDocument();
    expect(filaDeAsignacion(1).getByText("Ingeniería Civil")).toBeInTheDocument();

    // ...pero UNA sola acción de remoción por DELEGADO (no por asignación).
    expect(screen.getAllByRole("button", { name: /Quitar delegado/ })).toHaveLength(
      2,
    );
    expect(botonQuitar("Delegado Uno")).toBeInTheDocument();
    expect(botonQuitar("Delegado Dos")).toBeInTheDocument();
  });

  it("la remocion pide confirmacion antes de lanzar la peticion", async () => {
    renderModal([ASIGNACION_UNO]);

    await waitFor(() => expect(botonQuitar("Delegado Uno")).toBeInTheDocument());

    fireEvent.click(botonQuitar("Delegado Uno"));

    // Aparece el diálogo de confirmación compartido...
    await waitFor(() =>
      expect(
        screen.getByText("Quitar delegado de la liquidación"),
      ).toBeInTheDocument(),
    );
    expect(botonConfirmar()).toBeInTheDocument();
    expect(botonCancelar()).toBeInTheDocument();

    // ...pero TODAVÍA no se ha emitido ninguna petición.
    expect(mocks.apiRequest).not.toHaveBeenCalled();
  });

  it("cancelar la confirmacion no lanza ninguna peticion ni quita al delegado", async () => {
    renderModal([ASIGNACION_UNO]);

    await waitFor(() => expect(botonQuitar("Delegado Uno")).toBeInTheDocument());

    fireEvent.click(botonQuitar("Delegado Uno"));
    await waitFor(() => expect(botonConfirmar()).toBeInTheDocument());

    fireEvent.click(botonCancelar());

    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Quitar delegado" })).toBeNull(),
    );

    // Cancelar NO cambia nada: no hay petición y el delegado sigue listado.
    expect(mocks.apiRequest).not.toHaveBeenCalled();
    expect(screen.getByText("Delegado Uno")).toBeInTheDocument();
    expect(botonQuitar("Delegado Uno")).toBeInTheDocument();
  });

  it("confirmar la confirmacion lanza el patch de borrado del delegado", async () => {
    mocks.apiRequest.mockResolvedValue({
      data: successEnvelope(["delegado-1"]),
    });

    renderModal([ASIGNACION_UNO]);

    await waitFor(() => expect(botonQuitar("Delegado Uno")).toBeInTheDocument());

    fireEvent.click(botonQuitar("Delegado Uno"));
    await waitFor(() => expect(botonConfirmar()).toBeInTheDocument());

    fireEvent.click(botonConfirmar());

    await waitFor(() => expect(mocks.apiRequest).toHaveBeenCalledTimes(1));

    // El PATCH emitido usa la rama `delete` del batch EXISTENTE.
    const [config] = mocks.apiRequest.mock.calls[0];
    expect(config.method).toBe("PATCH");
    expect(config.url).toBe(`/liquidaciones/${LIQUIDACION_ID}/delegados`);
    expect(config.data).toEqual({ delete: [{ delegado_id: "delegado-1" }] });
  });

  it("la remocion exitosa actualiza el listado", async () => {
    mocks.apiRequest.mockResolvedValue({
      data: successEnvelope(["delegado-1"]),
    });

    renderModal([ASIGNACION_UNO, ASIGNACION_DOS]);

    await waitFor(() => expect(botonQuitar("Delegado Uno")).toBeInTheDocument());

    fireEvent.click(botonQuitar("Delegado Uno"));
    await waitFor(() => expect(botonConfirmar()).toBeInTheDocument());
    fireEvent.click(botonConfirmar());

    await waitFor(() =>
      expect(screen.queryByText("Delegado Uno")).not.toBeInTheDocument(),
    );

    // El resto del listado NO se ve afectado.
    expect(screen.getByText("Delegado Dos")).toBeInTheDocument();
  });

  it("el 409 de remocion se muestra inline y el delegado permanece", async () => {
    mocks.apiRequest.mockRejectedValue(
      conflictEnvelope(
        "No se puede quitar el delegado 'Delegado Uno' porque tiene detalles de honorario vinculados a un recibo de honorario mensual. Elimina primero el recibo mensual.",
      ),
    );

    renderModal([ASIGNACION_UNO, ASIGNACION_DOS]);

    await waitFor(() => expect(botonQuitar("Delegado Uno")).toBeInTheDocument());

    fireEvent.click(botonQuitar("Delegado Uno"));
    await waitFor(() => expect(botonConfirmar()).toBeInTheDocument());
    fireEvent.click(botonConfirmar());

    // El motivo del rechazo se muestra INLINE (role="alert").
    const mensaje = await screen.findByText(/recibo de honorario mensual/i);
    expect(mensaje.closest('[role="alert"]')).not.toBeNull();

    // El rechazo NO quita nada: el delegado y sus filas siguen visibles.
    expect(screen.getByText("Delegado Uno")).toBeInTheDocument();
    expect(botonQuitar("Delegado Uno")).toBeInTheDocument();
    expect(filaDeAsignacion(0).getByText("Arquitectura")).toBeInTheDocument();
  });
});
