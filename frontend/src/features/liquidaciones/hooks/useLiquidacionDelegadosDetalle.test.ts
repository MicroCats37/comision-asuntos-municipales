/**
 * useLiquidacionDelegadosDetalle — lectura anidada de asignaciones.
 *
 * Slice S3 de `liquidacion-delegado-detail-modal-apply-readiness`.
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la verificación
 * corre en el módulo de verificación final.
 *
 * Contrato que fijan:
 * - la consulta va al endpoint ANIDADO
 *   `GET /liquidaciones/{id}/delegados-asignaciones` (nunca al plano);
 * - cada asignación expone su propio id (pk de `LiquidacionDelegado`), que es
 *   el objetivo estable de la edición;
 * - con el modal cerrado (`enabled: false`) no se pide nada.
 *
 * Se usa `createElement` (y no JSX) porque el contrato de este slice fija el
 * nombre del fichero con extensión `.ts`.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  notifyError: vi.fn(),
  notifySuccess: vi.fn(),
}));

// Capa HTTP: única llamada que puede emitir la lectura.
vi.mock("@/lib/api", () => ({
  default: { get: mocks.apiGet },
}));

// Se conserva el resto de `@/errors` (parseo del envelope) y sólo se espía el toast.
vi.mock("@/errors", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/errors")>();
  return {
    ...actual,
    notify: { error: mocks.notifyError, success: mocks.notifySuccess },
  };
});

import { useLiquidacionDelegadosDetalle } from "./useLiquidacionDelegadosDetalle";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const LIQUIDACION_ID = "11111111-1111-4111-8111-111111111111";

/** Asignación con detalle RH y RH mensual enlazado. */
function makeAsignacion(overrides: Record<string, unknown> = {}) {
  return {
    id: "asignacion-1",
    liquidacion_id: LIQUIDACION_ID,
    delegado_id: "delegado-1",
    especialidad_revision: { id: "esp-1", nombre: "Arquitectura" },
    liquidacion: null,
    delegado: null,
    periodo: 2024,
    mes: 6,
    dictamen_revision: "CONFORME",
    fecha_presentacion: null,
    fecha_revision: null,
    tipo: "TITULAR",
    numero_rh: "RH-0001",
    creado_por_rh: true,
    detalle_rh: [
      {
        id: "detalle-1",
        imp_bruto: 1000,
        sub_total: 850,
        renta_cip: 85,
        aporte_codemu: 42.5,
        fondo_comun: 42.5,
        neto_honorario: 680,
        recibo_mensual: {
          id: "recibo-1",
          numero: 12,
          periodo: 2024,
          mes: 6,
          fecha_registro: "2024-06-30T00:00:00",
          sub_total: 850,
          renta_cip: 85,
          aporte_codemu: 42.5,
          fondo_comun: 42.5,
          neto_honorario: 680,
        },
      },
    ],
    ...overrides,
  };
}

/** Envelope `ApiResponse[LiquidacionDelegadoDetalleResponseOut]`. */
function makeEnvelope(asignaciones: unknown[]) {
  return {
    data: {
      success: true,
      data: { liquidacion_id: LIQUIDACION_ID, asignaciones },
      error: null,
      message: "Detalle de asignaciones obtenido.",
    },
  };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function setup() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);

  return { queryClient, wrapper };
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("useLiquidacionDelegadosDetalle", () => {
  beforeEach(() => {
    mocks.apiGet.mockReset();
    mocks.notifyError.mockReset();
    mocks.notifySuccess.mockReset();
  });

  it("consulta el endpoint anidado con el liquidacion_id", async () => {
    mocks.apiGet.mockResolvedValue(makeEnvelope([makeAsignacion()]));

    const { wrapper } = setup();
    renderHook(() => useLiquidacionDelegadosDetalle(LIQUIDACION_ID), {
      wrapper,
    });

    await waitFor(() => expect(mocks.apiGet).toHaveBeenCalledTimes(1));

    const [url] = mocks.apiGet.mock.calls[0];
    expect(url).toBe(`/liquidaciones/${LIQUIDACION_ID}/delegados-asignaciones`);
    // Nunca el endpoint plano de listado.
    expect(url).not.toBe("/liquidaciones/delegados-asignaciones");
  });

  it("expone el id de asignacion de cada asignacion", async () => {
    mocks.apiGet.mockResolvedValue(
      makeEnvelope([
        makeAsignacion({ id: "asignacion-1" }),
        makeAsignacion({ id: "asignacion-2", delegado_id: "delegado-2" }),
      ]),
    );

    const { wrapper } = setup();
    const { result } = renderHook(
      () => useLiquidacionDelegadosDetalle(LIQUIDACION_ID),
      { wrapper },
    );

    await waitFor(() =>
      expect(result.current.data?.asignaciones).toHaveLength(2),
    );

    const asignaciones = result.current.data?.asignaciones ?? [];
    // Cada fila es una ASIGNACIÓN: id propio y distinguible.
    expect(asignaciones[0].id).toBe("asignacion-1");
    expect(asignaciones[1].id).toBe("asignacion-2");
    expect(asignaciones[0].id).not.toBe(asignaciones[1].id);
  });

  it("no consulta cuando el modal esta cerrado", async () => {
    mocks.apiGet.mockResolvedValue(makeEnvelope([]));

    const { wrapper } = setup();
    renderHook(
      () => useLiquidacionDelegadosDetalle(LIQUIDACION_ID, { enabled: false }),
      { wrapper },
    );

    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(mocks.apiGet).not.toHaveBeenCalled();
  });
});
