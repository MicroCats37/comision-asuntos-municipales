/**
 * Listado general de liquidaciones — Fase 5.
 *
 * El backend retiró (Fase 3) los endpoints de "última revisión":
 *   - GET /liquidaciones/generales/ultimas-revisiones
 *   - GET /liquidaciones/edificaciones/ultima-revision
 *
 * El frontend NO debe volver a llamarlos: el único listado general es el
 * paginado completo (`GET /liquidaciones/generales/`), que devuelve TODAS las
 * revisiones (el número de revisión es una etiqueta editable y puede
 * repetirse entre hermanos).
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase.
 */
import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const captured: { url?: string; queryKey?: readonly unknown[] } = {};

// El hook real de TanStack Query se sustituye para poder inspeccionar la
// URL y la queryKey que se habrían pedido.
vi.mock("@/hooks", () => ({
  useApiQuery: (options: { url?: string; queryKey?: readonly unknown[] }) => {
    captured.url = options.url;
    captured.queryKey = options.queryKey;
    return {
      data: undefined,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    };
  },
}));

// La paginación por URL usa `useSearchParams` de Next (requiere App Router).
vi.mock("@/hooks/system/useUrlPagination", () => ({
  useUrlPagination: () => ({
    page: 1,
    pageSize: 10,
    setPage: vi.fn(),
    setPageSize: vi.fn(),
    resetPagination: vi.fn(),
  }),
}));

import { useLiquidacionesGenerales } from "./useLiquidacionesGenerales";

describe("useLiquidacionesGenerales — sin endpoint de última revisión", () => {
  it("consulta únicamente el listado general paginado", () => {
    renderHook(() => useLiquidacionesGenerales());

    expect(captured.url).toBe("/liquidaciones/generales/");
  });

  it("nunca pide los endpoints retirados", () => {
    renderHook(() => useLiquidacionesGenerales());

    expect(captured.url).not.toContain("ultimas-revisiones");
    expect(captured.url).not.toContain("ultima-revision");
  });

  it("no registra ningún modo 'ultimas-revisiones' en la queryKey", () => {
    renderHook(() => useLiquidacionesGenerales());

    expect(captured.queryKey).toBeDefined();
    expect(captured.queryKey).not.toContain("ultimas-revisiones");
    // El listado general completo conserva su namespace "todas" (separa el
    // listado de los detalles `["liquidaciones", "generales", id]`).
    expect(captured.queryKey?.[0]).toBe("liquidaciones");
    expect(captured.queryKey?.[1]).toBe("generales");
    expect(captured.queryKey?.[2]).toBe("todas");
  });
});
