/**
 * GestionarDelegadosModal — acción "Quitar delegado".
 *
 * Fase 2 (PR 2) de `liquidacion-delegado-safe-removal`. Estos tests se
 * ESCRIBEN pero NO se ejecutan en esta fase: la verificación corre en la
 * fase final de SDD (tarea 3.2).
 *
 * Contrato que fijan:
 * - la acción se renderiza SOLO en el bloque de solo lectura "Delegados
 *   Asignados"; el modo de selección del formulario de creación NO la muestra;
 * - cada fila emite EXACTAMENTE un PATCH /liquidaciones/{id}/delegados con un
 *   array `delete` de un único elemento;
 * - un 409 se muestra EN la fila y la fila NO desaparece (nunca se oculta un
 *   fallo como éxito);
 * - un éxito invalida el detalle y las listas visibles de liquidaciones;
 * - el delegado quitado no reaparece al reabrir el modal.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DelegadoVigente } from "../schemas/delegado-vigente.schema";
import type {
  LiquidacionDelegadoEnGeneralOutput,
  LiquidacionGeneralOutput,
} from "../schemas/liquidacion-base.schema";
import { DelegadosSection } from "./DelegadosSection";
import { GestionarDelegadosModal } from "./GestionarDelegadosModal";

const mocks = vi.hoisted(() => ({
  apiRequest: vi.fn(),
  notifyError: vi.fn(),
  notifySuccess: vi.fn(),
}));

// Réplica del layout real de `AppFormModal`: el body (children) se renderiza
// con los métodos del formulario. Se replica porque el modal real usa Radix
// Dialog + ScrollArea, que dependen de APIs de navegador no disponibles en
// jsdom (ResizeObserver).
vi.mock("@/components-app/forms/AppFormModal", async () => {
  const { FormProvider, useForm } = await import("react-hook-form");
  return {
    AppFormModal: ({
      title,
      description,
      children,
      initialData,
    }: {
      title?: string;
      description?: string;
      children: (props: { methods: unknown }) => ReactNode;
      initialData?: Record<string, unknown>;
    }) => {
      const methods = useForm({ defaultValues: initialData });
      return (
        <FormProvider {...methods}>
          <h2>{title}</h2>
          <p>{description}</p>
          {children({ methods })}
        </FormProvider>
      );
    },
  };
});

// Capa HTTP: el PATCH del batch es la única llamada que emite la acción.
vi.mock("@/lib/api", () => ({
  default: { request: mocks.apiRequest },
}));

// El bloque "Delegados Vigentes" no participa de esta acción.
vi.mock("../hooks/useDelegadosVigentes", () => ({
  useDelegadosVigentes: () => ({ data: [], isLoading: false }),
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

const DELEGADO_UNO: LiquidacionDelegadoEnGeneralOutput = {
  datos: {
    periodo: 2024,
    mes: 6,
    dictamen_revision: "CONFORME",
    fecha_presentacion: null,
    fecha_revision: null,
  },
  delegado: {
    id: "delegado-1",
    nombre_completo: "Delegado Uno",
    cip: "100001",
    tipo: "TITULAR",
    especialidad: { id: "esp-1", nombre: "Arquitectura" },
  },
};

const DELEGADO_DOS: LiquidacionDelegadoEnGeneralOutput = {
  datos: {
    periodo: null,
    mes: null,
    dictamen_revision: null,
    fecha_presentacion: null,
    fecha_revision: null,
  },
  delegado: {
    id: "delegado-2",
    nombre_completo: "Delegado Dos",
    cip: "100002",
    tipo: "ALTERNO",
    especialidad: { id: "esp-1", nombre: "Arquitectura" },
  },
};

const VIGENTE: DelegadoVigente = {
  id: "delegado-1",
  nombre_completo: "Delegado Uno",
  cip: "100001",
  tipo: "TITULAR",
  especialidad: { id: "esp-1", nombre: "Arquitectura" },
};

function makeLiquidacion(
  delegados: LiquidacionDelegadoEnGeneralOutput[] = [
    DELEGADO_UNO,
    DELEGADO_DOS,
  ],
): LiquidacionGeneralOutput {
  return {
    id: LIQUIDACION_ID,
    fecha_registro: "2026-02-01",
    municipalidad: { id: "mun-1", nombre: "Municipalidad Uno" },
    tipo_liquidacion: {
      id: "tipo-1",
      codigo: "EDIFICACION",
      nombre: "Edificación",
    },
    delegados,
  } as unknown as LiquidacionGeneralOutput;
}

function successEnvelope(deleted: string[]) {
  return {
    data: {
      success: true,
      data: { created: [], updated: [], deleted },
      error: null,
      message: "Delegados actualizados correctamente.",
    },
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
    defaultOptions: { queries: { retry: false } },
  });

  const view = render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );

  return {
    queryClient,
    ...view,
    rerenderWithClient: (next: ReactNode) =>
      view.rerender(
        <QueryClientProvider client={queryClient}>{next}</QueryClientProvider>,
      ),
  };
}

function renderModal(delegados?: LiquidacionDelegadoEnGeneralOutput[]) {
  return renderWithQueryClient(
    <GestionarDelegadosModal
      open
      onOpenChange={vi.fn()}
      liquidacionGeneral={makeLiquidacion(delegados)}
    />,
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("GestionarDelegadosModal — Quitar delegado", () => {
  beforeEach(() => {
    mocks.apiRequest.mockReset();
    mocks.notifyError.mockReset();
    mocks.notifySuccess.mockReset();
  });

  it("renderiza la acción en el bloque de solo lectura y NO en el modo de selección", () => {
    const { unmount } = renderWithQueryClient(
      <DelegadosSection
        vigentes={[]}
        asignados={[DELEGADO_UNO]}
        hasMunicipalidad
        onQuitarDelegado={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("button", { name: "Quitar delegado: Delegado Uno" }),
    ).toBeInTheDocument();

    unmount();

    // Modo de selección del formulario de creación: sin acción de quitar.
    renderWithQueryClient(
      <DelegadosSection
        vigentes={[VIGENTE]}
        selectedIds={[]}
        onToggleDelegado={vi.fn()}
        hasMunicipalidad
      />,
    );

    expect(
      screen.queryByRole("button", { name: /Quitar delegado/i }),
    ).not.toBeInTheDocument();
  });

  it("el modal ya no se declara como vista de solo lectura", () => {
    renderModal();

    expect(
      screen.queryByText(/vista de solo lectura/i),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/quitar un delegado que no tenga registros/i),
    ).toBeInTheDocument();
  });

  it("emite exactamente un PATCH con un array delete de un solo elemento", async () => {
    mocks.apiRequest.mockResolvedValue(successEnvelope(["delegado-1"]));

    renderModal();

    fireEvent.click(
      screen.getByRole("button", { name: "Quitar delegado: Delegado Uno" }),
    );

    await waitFor(() => expect(mocks.apiRequest).toHaveBeenCalledTimes(1));

    const [config] = mocks.apiRequest.mock.calls[0];
    expect(config.method).toBe("PATCH");
    expect(config.url).toBe(`/liquidaciones/${LIQUIDACION_ID}/delegados`);
    expect(config.data).toEqual({ delete: [{ delegado_id: "delegado-1" }] });
  });

  it("muestra el 409 en la fila y conserva la fila rechazada", async () => {
    mocks.apiRequest.mockRejectedValue(
      conflictEnvelope(
        "El delegado está asociado a un recibo de honorario mensual.",
      ),
    );

    renderModal();

    fireEvent.click(
      screen.getByRole("button", { name: "Quitar delegado: Delegado Uno" }),
    );

    await waitFor(() =>
      expect(
        screen.getByText(/recibo de honorario mensual/i),
      ).toBeInTheDocument(),
    );

    // La fila rechazada NO desaparece y el resto de filas no se ven afectadas.
    expect(screen.getByText("Delegado Uno")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Quitar delegado: Delegado Uno" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Delegado Dos")).toBeInTheDocument();
  });

  it("invalida el detalle y las listas visibles de liquidaciones tras el éxito", async () => {
    mocks.apiRequest.mockResolvedValue(successEnvelope(["delegado-1"]));

    const { queryClient } = renderModal();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    fireEvent.click(
      screen.getByRole("button", { name: "Quitar delegado: Delegado Uno" }),
    );

    await waitFor(() => expect(mocks.apiRequest).toHaveBeenCalledTimes(1));

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["liquidaciones", "generales", "detalle", LIQUIDACION_ID],
      });
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["liquidaciones", "generales", "todas"],
      });
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["liquidaciones", "edificaciones"],
      });
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["liquidaciones", "taludes"],
      });
    });
  });

  it("elimina la fila tras el éxito y el delegado no reaparece al reabrir", async () => {
    mocks.apiRequest.mockResolvedValue(successEnvelope(["delegado-1"]));

    const { rerenderWithClient } = renderModal();

    fireEvent.click(
      screen.getByRole("button", { name: "Quitar delegado: Delegado Uno" }),
    );

    await waitFor(() =>
      expect(screen.queryByText("Delegado Uno")).not.toBeInTheDocument(),
    );
    expect(screen.getByText("Delegado Dos")).toBeInTheDocument();

    // Reapertura con el snapshot ya refrescado (el backend no lo devuelve).
    rerenderWithClient(
      <GestionarDelegadosModal
        open
        onOpenChange={vi.fn()}
        liquidacionGeneral={makeLiquidacion([DELEGADO_DOS])}
      />,
    );

    expect(screen.queryByText("Delegado Uno")).not.toBeInTheDocument();
    expect(screen.getByText("Delegado Dos")).toBeInTheDocument();
  });
});
