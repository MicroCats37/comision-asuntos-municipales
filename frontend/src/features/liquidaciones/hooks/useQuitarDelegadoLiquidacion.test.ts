/**
 * useQuitarDelegadoLiquidacion — remoción de UN delegado de una liquidación.
 *
 * Slice S5 de `liquidacion-delegado-detail-modal-apply-readiness`.
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la verificación
 * corre en el módulo de verificación final.
 *
 * Contrato que fijan:
 * - la remoción sigue pasando por el batch EXISTENTE
 *   `PATCH /liquidaciones/{id}/delegados` con la rama `delete` y UN único
 *   item (no se añade ningún endpoint, payload ni camino de remoción);
 * - tras el éxito se invalidan el detalle de ASIGNACIONES (la fila quitada no
 *   debe reaparecer al reabrir el modal dedicado), el detalle de la
 *   liquidación, las listas visibles, el listado del browse de RH y las
 *   CANDIDATAS de RH mensual (la liquidación desasignada vuelve a ser
 *   elegible en el wizard);
 * - el rechazo 409 (RH mensual enlazado) NO invalida nada: el backend no
 *   cambia el estado y la UI lo muestra inline.
 *
 * Se usa `createElement` (y no JSX) para mantener el fichero en `.ts`.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  apiRequest: vi.fn(),
  notifyError: vi.fn(),
  notifySuccess: vi.fn(),
}));

// Capa HTTP: el PATCH del batch es la única llamada que emite la remoción.
vi.mock("@/lib/api", () => ({
  default: { request: mocks.apiRequest },
}));

// Se conserva el resto de `@/errors` (parseo del envelope) y sólo se espía el toast.
vi.mock("@/errors", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/errors")>();
  return {
    ...actual,
    notify: { error: mocks.notifyError, success: mocks.notifySuccess },
  };
});

import { useQuitarDelegadoLiquidacion } from "./useQuitarDelegadoLiquidacion";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const LIQUIDACION_ID = "11111111-1111-4111-8111-111111111111";
const RH_BROWSE_ENDPOINT = "/liquidaciones/generales/";

/** Envelope `ApiResponse[LiquidacionDelegadoBatchOut]`. */
function successEnvelope(deleted: string[] = ["delegado-1"]) {
  return {
    data: {
      success: true,
      data: { created: [], updated: [], deleted },
      error: null,
      message: "Delegados actualizados correctamente.",
    },
  };
}

/** Envelope de rechazo 409 (el delegado tiene un RH mensual enlazado). */
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

function setup(rhBrowseEndpoint: string | null = RH_BROWSE_ENDPOINT) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);

  const view = renderHook(
    () => useQuitarDelegadoLiquidacion(LIQUIDACION_ID, { rhBrowseEndpoint }),
    { wrapper },
  );

  return { queryClient, ...view };
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("useQuitarDelegadoLiquidacion", () => {
  beforeEach(() => {
    mocks.apiRequest.mockReset();
    mocks.notifyError.mockReset();
    mocks.notifySuccess.mockReset();
    mocks.apiRequest.mockResolvedValue(successEnvelope());
  });

  it("emite un solo PATCH con la rama delete y el id del delegado", async () => {
    const { result } = setup();

    await result.current.quitar({ delegado_id: "delegado-1" });

    expect(mocks.apiRequest).toHaveBeenCalledTimes(1);

    const [config] = mocks.apiRequest.mock.calls[0];
    // El MISMO endpoint y la MISMA rama `delete`: no hay segundo camino.
    expect(config.method).toBe("PATCH");
    expect(config.url).toBe(`/liquidaciones/${LIQUIDACION_ID}/delegados`);
    // UN item en `delete` (un PATCH por fila).
    expect(config.data).toEqual({ delete: [{ delegado_id: "delegado-1" }] });
  });

  it("invalida el detalle de asignaciones de la liquidación", async () => {
    const { result, queryClient } = setup();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    await result.current.quitar({ delegado_id: "delegado-1" });

    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["liquidaciones", "delegados-asignaciones", LIQUIDACION_ID],
      }),
    );
  });

  it("invalida el detalle, las listas visibles y el listado del browse", async () => {
    const { result, queryClient } = setup();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    await result.current.quitar({ delegado_id: "delegado-1" });

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
        queryKey: ["rh-browse", "liquidaciones", RH_BROWSE_ENDPOINT],
      });
    });
  });

  it("NO invalida el listado del browse cuando no se conoce su endpoint", async () => {
    const { result, queryClient } = setup(null);
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    await result.current.quitar({ delegado_id: "delegado-1" });

    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["liquidaciones", "generales", "detalle", LIQUIDACION_ID],
      }),
    );
    expect(invalidateSpy).not.toHaveBeenCalledWith({
      queryKey: ["rh-browse", "liquidaciones", RH_BROWSE_ENDPOINT],
    });
  });

  it("invalida las CANDIDATAS de RH: la liquidación vuelve a ser elegible", async () => {
    const { result, queryClient } = setup();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    await result.current.quitar({ delegado_id: "delegado-1" });

    // Sin esto, la liquidación desasignada seguiría apareciendo como
    // candidata en el wizard de RH mensual.
    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["delegados", "candidatas"],
      }),
    );
  });

  it("el rechazo 409 no invalida nada: el estado del servidor no cambió", async () => {
    mocks.apiRequest.mockRejectedValue(
      conflictEnvelope(
        "El delegado está asociado a un recibo de honorario mensual.",
      ),
    );

    const { result, queryClient } = setup();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    await expect(
      result.current.quitar({ delegado_id: "delegado-1" }),
    ).rejects.toBeTruthy();

    // El guardián 409 aborta la remoción: nada se invalida y nada se borra.
    expect(invalidateSpy).not.toHaveBeenCalled();
  });

  it("el rechazo 409 NO invalida las candidatas: la asignación sigue vigente", async () => {
    mocks.apiRequest.mockRejectedValue(
      conflictEnvelope(
        "El delegado está asociado a un recibo de honorario mensual.",
      ),
    );

    const { result, queryClient } = setup();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    await expect(
      result.current.quitar({ delegado_id: "delegado-1" }),
    ).rejects.toBeTruthy();

    // La liquidación SIGUE asignada: no hay nada que re-elegir.
    expect(invalidateSpy).not.toHaveBeenCalledWith({
      queryKey: ["delegados", "candidatas"],
    });
  });
});
