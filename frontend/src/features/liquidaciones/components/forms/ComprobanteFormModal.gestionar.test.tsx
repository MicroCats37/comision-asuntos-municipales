/**
 * ComprobanteFormModal — flujo ÚNICO de gestión del comprobante.
 *
 * Refinamiento de `rh-browse-cards-delegados-comprobante-edit`: el modal de
 * comprobante deja de exponer diálogos separados de alta y de edición. Ahora
 * hay UN SOLO modal (SIN prop `modo`) con tres vistas encadenadas:
 *
 *   · SIN comprobante vigente → formulario de ALTA (POST).
 *   · CON comprobante vigente  → RESUMEN de sólo lectura (vigente + historial)
 *     con la acción "Editar comprobante"; al pulsarla, el CONTENIDO del MISMO
 *     modal se sustituye por el formulario de EDICIÓN (PATCH). Nunca se abre
 *     un segundo diálogo.
 *
 * Contrato que fijan:
 * - un único modal: el resumen y el formulario nunca coexisten;
 * - la vista inicial se DERIVA del estado real del comprobante vigente;
 * - la edición sólo es alcanzable con comprobante vigente (edición del activo);
 * - el guardado de la edición emite EXACTAMENTE un `PATCH` al recurso del
 *   comprobante (`/liquidaciones/generales/{id}/comprobante/{comprobante_id}`)
 *   y NINGÚN `POST`; el cuerpo NO incluye `monto` NI `motivo_reemplazo`;
 * - el alta y el reemplazo siguen usando el endpoint de CREACIÓN (POST);
 * - el monto y el historial no se modifican al editar.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la verificación
 * corre en la fase final de SDD (`sdd-verify`).
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

import type { LiquidacionGeneralOutput } from "../../schemas/liquidacion-base.schema";
import { ComprobanteFormModal } from "./ComprobanteFormModal";

const mocks = vi.hoisted(() => ({
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  notifyError: vi.fn(),
  notifySuccess: vi.fn(),
}));

// Capa HTTP: el PATCH (edición) y el POST (alta/reemplazo) son las dos únicas
// escrituras que emite este componente.
vi.mock("@/lib/api", () => ({
  default: {
    patch: mocks.apiPatch,
    post: mocks.apiPost,
    get: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

// Se conserva el `handleApiError` real (parsea el envelope del backend) y sólo
// se espía el toast.
vi.mock("@/errors", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/errors")>();
  return {
    ...actual,
    notify: {
      ...actual.notify,
      error: mocks.notifyError,
      success: mocks.notifySuccess,
    },
  };
});

/**
 * El modal real (`GenericModal`) usa Radix Dialog + ScrollArea, que dependen de
 * APIs de navegador no disponibles en jsdom (ResizeObserver). Se stubbea el
 * CONTENEDOR (no el contenido): el test verifica que hay UN SOLO modal y que
 * su contenido se sustituye, no la implementación del diálogo.
 */
vi.mock("@/components/genericModal/GenericModal", () => {
  const Contenedor = ({ children }: { children?: ReactNode }) => (
    <div>{children}</div>
  );
  const Raiz = ({
    open,
    children,
  }: {
    open: boolean;
    children?: ReactNode;
  }) => (open ? <div data-testid="comprobante-modal">{children}</div> : null);

  return {
    GenericModal: Object.assign(Raiz, {
      Content: Contenedor,
      Header: Contenedor,
      Body: Contenedor,
      Footer: Contenedor,
      CloseX: () => null,
    }),
  };
});

/**
 * El hook de estado de tarjeta arrastra la barra de formularios de las 6 vistas
 * por tipo y el generador de PDF. Este test no los necesita: se stubbea para
 * que la importación del barrel de hooks no cargue componentes ajenos.
 */
vi.mock("@/features/liquidaciones/hooks/useLiquidacionCardState", () => ({
  useLiquidacionCardState: () => ({ shellProps: {}, modals: null }),
}));

// ── Fixtures ─────────────────────────────────────────────────────────────────

const LIQUIDACION_ID = "11111111-1111-4111-8111-111111111111";
const COMPROBANTE_ACTIVO_ID = "22222222-2222-4222-8222-222222222222";
const COMPROBANTE_HISTORICO_ID = "33333333-3333-4333-8333-333333333333";

/** Liquidación CON comprobante vigente (activo) y uno histórico. */
const LIQUIDACION = {
  id: LIQUIDACION_ID,
  estado: "PENDIENTE",
  municipalidad: { id: "mun-1", codigo: "001", nombre: "Municipalidad Uno" },
  usuario_creador: null,
  fecha_registro: "2026-01-15",
  expediente: "EXP-001",
  observacion: null,
  numero_revision: 1,
  sub_total: 100,
  total: 118,
  legacy: false,
  codigo_cta: null,
  igv: null,
  uit: null,
  proyecto: {
    id: "p-1",
    nombre_propietario: "ACME S.A.",
    direccion: "Av. Siempre Viva 742",
    urbanizacion: null,
    distrito: null,
    entidad: null,
  },
  denominacion_de_proyecto: null,
  contacto: null,
  tipo_liquidacion: { codigo: "EDIFICACION", nombre: "Edificación" },
  delegados: [],
  comprobantes: [
    {
      id: COMPROBANTE_ACTIVO_ID,
      tipo_comprobante: "FACTURA",
      serie: "F001",
      numero: "55",
      fecha_emision: "2026-01-20",
      monto: 118,
      activo: true,
      motivo_reemplazo: null,
    },
    {
      id: COMPROBANTE_HISTORICO_ID,
      tipo_comprobante: "BOLETA",
      serie: "B001",
      numero: "10",
      fecha_emision: "2025-12-01",
      monto: 100,
      activo: false,
      motivo_reemplazo: "Comprobante anterior anulado",
    },
  ],
} as unknown as LiquidacionGeneralOutput;

/** Liquidación SIN comprobante: el flujo arranca en el formulario de ALTA. */
const LIQUIDACION_SIN_COMPROBANTE = {
  ...LIQUIDACION,
  comprobantes: [],
} as unknown as LiquidacionGeneralOutput;

/** Respuesta del backend tras un PATCH/POST correcto. */
const LIQUIDACION_ACTUALIZADA = {
  ...LIQUIDACION,
  comprobantes: [
    {
      ...LIQUIDACION.comprobantes[0],
      serie: "F002",
      numero: "55",
    },
    LIQUIDACION.comprobantes[1],
  ],
} as unknown as LiquidacionGeneralOutput;

function envelope(data: unknown) {
  return { data: { success: true, data, error: null } };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function renderModal(
  liquidacionGeneral: LiquidacionGeneralOutput = LIQUIDACION,
  onOpenChange: (open: boolean) => void = vi.fn(),
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  // Se siembran las cachés que los hooks parchean: detalle + lista paginada.
  queryClient.setQueryData(
    ["liquidaciones", "generales", "detail", LIQUIDACION_ID],
    liquidacionGeneral,
  );
  queryClient.setQueryData(["liquidaciones", "generales", "todas", 1, 10], {
    items: [liquidacionGeneral],
    total: 1,
    page: 1,
    page_size: 10,
    total_pages: 1,
  });

  const view = render(
    <QueryClientProvider client={queryClient}>
      <ComprobanteFormModal
        open
        onOpenChange={onOpenChange}
        liquidacionGeneral={liquidacionGeneral}
      />
    </QueryClientProvider>,
  );

  return { queryClient, onOpenChange, ...view };
}

/** Pulsa "Editar comprobante" en el resumen (cambia el contenido del modal). */
function irAEditar() {
  fireEvent.click(screen.getByRole("button", { name: "Editar comprobante" }));
}

// ── Tests ────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  mocks.apiPatch.mockResolvedValue(envelope(LIQUIDACION_ACTUALIZADA));
  mocks.apiPost.mockResolvedValue(envelope(LIQUIDACION_ACTUALIZADA));
});

describe("ComprobanteFormModal — un SOLO modal de gestión", () => {
  it("sin comprobante vigente muestra el formulario de ALTA", () => {
    renderModal(LIQUIDACION_SIN_COMPROBANTE);

    expect(
      screen.getByRole("heading", { name: "Agregar comprobante" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("comprobante-formulario")).toBeInTheDocument();
    // Sin comprobante vigente NO hay resumen que mostrar.
    expect(screen.queryByTestId("comprobante-resumen")).not.toBeInTheDocument();
    // Y no se pide el motivo de reemplazo: no hay nada que reemplazar.
    expect(
      screen.queryByLabelText(/motivo de reemplazo/i),
    ).not.toBeInTheDocument();
  });

  it("con comprobante vigente muestra PRIMERO el resumen de sólo lectura", () => {
    renderModal();

    // El TÍTULO del modal (h2) es el de la vista "resumen". Se acota por nivel
    // porque la tarjeta de resumen repite el rótulo en su propio h3.
    expect(
      screen.getByRole("heading", { level: 2, name: "Comprobante vigente" }),
    ).toBeInTheDocument();

    const resumen = screen.getByTestId("comprobante-resumen");
    // El vigente se muestra con sus datos (sólo lectura).
    expect(within(resumen).getByText("FACTURA")).toBeInTheDocument();
    expect(within(resumen).getByText("F001-55")).toBeInTheDocument();
    expect(within(resumen).getByText("S/ 118.00")).toBeInTheDocument();
    // El historial está a la vista.
    expect(screen.getByText("Historial de comprobantes")).toBeInTheDocument();
    // Y el formulario todavía NO: primero se resume, luego se actúa.
    expect(screen.queryByTestId("comprobante-formulario")).not.toBeInTheDocument();
  });

  it("«Editar comprobante» sustituye el CONTENIDO del MISMO modal (sin segundo diálogo)", () => {
    renderModal();

    irAEditar();

    // UN SOLO modal: el resumen se sustituye, no se apila.
    expect(screen.getAllByTestId("comprobante-modal")).toHaveLength(1);
    expect(screen.queryByTestId("comprobante-resumen")).not.toBeInTheDocument();
    expect(screen.getByTestId("comprobante-formulario")).toBeInTheDocument();

    // El formulario de EDICIÓN viene prefilled con el comprobante vigente.
    expect(
      screen.getByRole("heading", { name: "Editar comprobante" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Serie")).toHaveValue("F001");
    expect(screen.getByLabelText("Número")).toHaveValue("55");
  });

  it("el guardado de la EDICIÓN emite UN PATCH y NINGÚN POST, sin `monto`", async () => {
    renderModal();

    irAEditar();

    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(mocks.apiPatch).toHaveBeenCalledTimes(1));
    expect(mocks.apiPost).not.toHaveBeenCalled();

    const [url, body] = mocks.apiPatch.mock.calls[0];
    expect(url).toBe(
      `/liquidaciones/generales/${LIQUIDACION_ID}/comprobante/${COMPROBANTE_ACTIVO_ID}`,
    );
    // El monto NUNCA viaja: lo preserva el backend.
    expect(body).not.toHaveProperty("monto");
    // La EDICIÓN no es un reemplazo: `motivo_reemplazo` tampoco viaja.
    expect(body).not.toHaveProperty("motivo_reemplazo");
    expect(body).toMatchObject({
      tipo_comprobante: "FACTURA",
      serie: "F001",
      numero: "55",
      fecha_emision: "2026-01-20",
    });
  });

  it("tras el guardado el modal se cierra (mismo comportamiento que el alta)", async () => {
    const onOpenChange = vi.fn();
    renderModal(LIQUIDACION, onOpenChange);

    irAEditar();
    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(mocks.apiPatch).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });

  it("el ALTA sin comprobante vigente usa el endpoint de CREACIÓN (POST)", async () => {
    renderModal(LIQUIDACION_SIN_COMPROBANTE);

    fireEvent.change(screen.getByLabelText("Serie"), {
      target: { value: "F002" },
    });
    await waitFor(() =>
      expect(screen.getByLabelText("Serie")).toHaveValue("F002"),
    );

    fireEvent.click(screen.getByRole("button", { name: "Agregar" }));

    await waitFor(() => expect(mocks.apiPost).toHaveBeenCalledTimes(1));
    expect(mocks.apiPatch).not.toHaveBeenCalled();

    const [url, body] = mocks.apiPost.mock.calls[0];
    expect(url).toBe(`/liquidaciones/generales/${LIQUIDACION_ID}/comprobante`);
    expect(body).toMatchObject({ tipo_comprobante: "FACTURA", serie: "F002" });
    // El monto NUNCA viaja.
    expect(body).not.toHaveProperty("monto");
  });

  it("el REEMPLAZO vuelve al endpoint de CREACIÓN y exige el motivo de reemplazo", async () => {
    renderModal();

    // Desde el resumen se entra al formulario de reemplazo (mismo modal).
    fireEvent.click(
      screen.getByRole("button", { name: "Reemplazar comprobante" }),
    );

    expect(screen.getByTestId("comprobante-formulario")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Reemplazar comprobante" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/motivo de reemplazo/i)).toBeInTheDocument();

    // Sin motivo de reemplazo NO se emite nada (el motivo es obligatorio).
    fireEvent.change(screen.getByLabelText("Serie"), {
      target: { value: "F002" },
    });
    await waitFor(() =>
      expect(screen.getByLabelText("Serie")).toHaveValue("F002"),
    );
    fireEvent.click(screen.getByRole("button", { name: "Reemplazar" }));

    // Con el motivo, el reemplazo viaja por el endpoint de CREACIÓN: si el
    // intento anterior hubiera emitido algo, aquí habría DOS llamadas.
    fireEvent.change(screen.getByLabelText(/motivo de reemplazo/i), {
      target: { value: "Comprobante incorrecto" },
    });
    await waitFor(() =>
      expect(screen.getByLabelText(/motivo de reemplazo/i)).toHaveValue(
        "Comprobante incorrecto",
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Reemplazar" }));

    await waitFor(() => expect(mocks.apiPost).toHaveBeenCalledTimes(1));
    expect(mocks.apiPatch).not.toHaveBeenCalled();
    const [url, body] = mocks.apiPost.mock.calls[0];
    expect(url).toBe(`/liquidaciones/generales/${LIQUIDACION_ID}/comprobante`);
    expect(body).toMatchObject({
      serie: "F002",
      motivo_reemplazo: "Comprobante incorrecto",
    });
  });

  it("«Volver» desde la edición vuelve al resumen del MISMO modal", () => {
    renderModal();

    irAEditar();
    expect(screen.queryByTestId("comprobante-resumen")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Volver" }));

    expect(screen.getByTestId("comprobante-resumen")).toBeInTheDocument();
    expect(screen.getAllByTestId("comprobante-modal")).toHaveLength(1);
  });
});

/**
 * Guardas de la DERIVACIÓN DE LA VISTA: el modal no recibe ningún modo por
 * props — la vista inicial se deduce del ESTADO REAL del comprobante vigente.
 */
describe("ComprobanteFormModal — la vista inicial se deriva del vigente real", () => {
  it("sin vigente abre en la vista de ALTA (crear) y no pide motivo de reemplazo", () => {
    renderModal(LIQUIDACION_SIN_COMPROBANTE);

    // Vista "crear": el formulario de alta.
    expect(screen.getByTestId("comprobante-formulario")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Agregar comprobante" }),
    ).toBeInTheDocument();
    // No hay resumen (no hay vigente que resumir).
    expect(screen.queryByTestId("comprobante-resumen")).not.toBeInTheDocument();
    // Sin vigente NO hay nada que reemplazar: el motivo no se pide.
    expect(
      screen.queryByLabelText(/motivo de reemplazo/i),
    ).not.toBeInTheDocument();
    // Y el pie ofrece "Cancelar" (sin vigente no hay resumen al que volver).
    expect(screen.getByRole("button", { name: "Cancelar" })).toBeInTheDocument();
  });

  it("con vigente abre en la vista de RESUMEN y ofrece editar y reemplazar", () => {
    renderModal();

    // Vista "resumen": sólo lectura del vigente + historial.
    const resumen = screen.getByTestId("comprobante-resumen");
    expect(
      within(resumen).getByRole("heading", { name: "Comprobante vigente" }),
    ).toBeInTheDocument();
    // El formulario todavía NO: primero se resume, luego se actúa.
    expect(screen.queryByTestId("comprobante-formulario")).not.toBeInTheDocument();
    // Desde el resumen se ofrece editar y reemplazar el vigente.
    expect(
      screen.getByRole("button", { name: "Editar comprobante" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Reemplazar comprobante" }),
    ).toBeInTheDocument();
  });
});
