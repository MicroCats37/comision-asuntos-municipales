/**
 * Cache de liquidaciones — Fase 5 (listas, caché y lenguaje de interfaz).
 *
 * Invariante central de esta fase:
 * una liquidación creada / revisada / relacionada se INSERTA o ACTUALIZA en las
 * listas visibles SIN eliminar NUNCA la previa seleccionada ni sus hermanos
 * (que pueden compartir el mismo número de revisión).
 *
 * Además se verifica que el namespace de cache "ultimas-revisiones" ya no
 * existe: el backend retiró `GET /liquidaciones/generales/ultimas-revisiones`
 * y `GET /liquidaciones/edificaciones/ultima-revision`.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase (regla del plan).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it } from "vitest";
import {
  GENERALES_TODAS_SUFFIX,
  type LiquidacionWrapper,
  type PaginatedCache,
  upsertItemInPaginatedCache,
  useLiquidacionesCacheUtils,
} from "./useLiquidacionesCacheUtils";

const TIPO_KEY = "edificaciones";
const TIPO_LIST_KEY = ["liquidaciones", TIPO_KEY, 1, 10] as const;
const GENERAL_LIST_KEY = [
  "liquidaciones",
  "generales",
  GENERALES_TODAS_SUFFIX,
  1,
  10,
] as const;

function wrapper(id: string, numeroRevision: number): LiquidacionWrapper {
  return {
    liquidacion_general: { id, numero_revision: numeroRevision },
    liquidacion_especifica: { id: `esp-${id}`, numero: 1 },
  };
}

function listCache(items: LiquidacionWrapper[], pageSize = 10): PaginatedCache {
  return {
    success: true,
    data: {
      items,
      total: items.length,
      total_pages: 1,
      page: 1,
      page_size: pageSize,
    },
  };
}

function readItems(cache: PaginatedCache | undefined): LiquidacionWrapper[] {
  return cache?.data?.items ?? [];
}

function readIds(cache: PaginatedCache | undefined): string[] {
  return readItems(cache).map((item) => String(item.liquidacion_general?.id));
}

describe("upsertItemInPaginatedCache — helper puro", () => {
  it("inserta al inicio y suma 1 al total cuando el id es nuevo", () => {
    const old = listCache([wrapper("prev", 1)]);
    const next = upsertItemInPaginatedCache(old, wrapper("nueva", 3));

    expect(readIds(next)).toEqual(["nueva", "prev"]);
    expect(next.data?.total).toBe(2);
  });

  it("actualiza EN SU LUGAR cuando el id ya existe (no duplica ni cambia el total)", () => {
    const old = listCache([wrapper("a", 1), wrapper("b", 3)]);
    const next = upsertItemInPaginatedCache(old, {
      ...wrapper("b", 5),
      liquidacion_general: { id: "b", numero_revision: 5 },
    });

    expect(readIds(next)).toEqual(["a", "b"]);
    expect(next.data?.total).toBe(2);
    expect(readItems(next)[1].liquidacion_general?.numero_revision).toBe(5);
  });

  it("NO elimina siblings ni la previa (incluso con el mismo número de revisión)", () => {
    const old = listCache([wrapper("previa", 3), wrapper("hermano", 3)]);
    const next = upsertItemInPaginatedCache(old, wrapper("nueva", 3));

    expect(readIds(next)).toEqual(["nueva", "previa", "hermano"]);
    expect(next.data?.total).toBe(3);
  });

  it("respeta el page_size (no agranda la página)", () => {
    const old = listCache([wrapper("a", 1), wrapper("b", 1)], 2);
    const next = upsertItemInPaginatedCache(old, wrapper("c", 1));

    expect(readItems(next)).toHaveLength(2);
    expect(readIds(next)).toEqual(["c", "a"]);
    expect(next.data?.total).toBe(3);
  });
});

describe("useLiquidacionesCacheUtils — insercIÓN/actualización sin borrados", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  const renderCacheUtils = () =>
    renderHook(() => useLiquidacionesCacheUtils(), {
      wrapper: ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      ),
    });

  it("inserta la liquidación nueva sin sacar la previa ni sus hermanos", () => {
    const previa = wrapper("previa", 3);
    const hermano = wrapper("hermano", 3);
    const nueva = wrapper("nueva", 5);

    queryClient.setQueryData(TIPO_LIST_KEY, listCache([previa, hermano]));
    queryClient.setQueryData(GENERAL_LIST_KEY, listCache([previa, hermano]));

    const { result } = renderCacheUtils();
    result.current.upsertCreatedItem(nueva, { tipoKey: TIPO_KEY });

    const tipoCache = queryClient.getQueryData<PaginatedCache>(TIPO_LIST_KEY);
    const generalCache =
      queryClient.getQueryData<PaginatedCache>(GENERAL_LIST_KEY);

    expect(readIds(tipoCache)).toEqual(["nueva", "previa", "hermano"]);
    expect(readIds(generalCache)).toEqual(["nueva", "previa", "hermano"]);
    expect(tipoCache?.data?.total).toBe(3);
    expect(generalCache?.data?.total).toBe(3);
  });

  it("actualiza en su lugar si la liquidación ya está en la página", () => {
    queryClient.setQueryData(
      TIPO_LIST_KEY,
      listCache([wrapper("a", 1), wrapper("b", 3)]),
    );

    const { result } = renderCacheUtils();
    result.current.upsertCreatedItem(
      {
        ...wrapper("b", 5),
        liquidacion_general: { id: "b", numero_revision: 5 },
      },
      { tipoKey: TIPO_KEY },
    );

    const tipoCache = queryClient.getQueryData<PaginatedCache>(TIPO_LIST_KEY);
    expect(readIds(tipoCache)).toEqual(["a", "b"]);
    expect(tipoCache?.data?.total).toBe(2);
    expect(readItems(tipoCache)[1].liquidacion_general?.numero_revision).toBe(
      5,
    );
  });

  it("siembra los detalles (tipo-específico y general) de la liquidación", () => {
    const nueva = wrapper("nueva", 3);

    const { result } = renderCacheUtils();
    result.current.upsertCreatedItem(nueva, { tipoKey: TIPO_KEY });

    expect(
      queryClient.getQueryData(["liquidaciones", TIPO_KEY, "nueva"]),
    ).toEqual(nueva);
    expect(
      queryClient.getQueryData(["liquidaciones", "generales", "nueva"]),
    ).toEqual(nueva);
  });

  it("no escribe ni consulta ningún namespace 'ultimas-revisiones'", () => {
    const nueva = wrapper("nueva", 3);

    const { result } = renderCacheUtils();
    result.current.upsertCreatedItem(nueva, { tipoKey: TIPO_KEY });
    result.current.removeVisibleItem("nueva");

    const keys = queryClient
      .getQueryCache()
      .findAll()
      .map((query) => query.queryKey.join("/"));

    expect(keys.length).toBeGreaterThan(0);
    expect(keys.some((key) => key.includes("ultimas-revisiones"))).toBe(false);
  });

  it("el soft-delete sí saca la liquidación de las listas", () => {
    queryClient.setQueryData(
      TIPO_LIST_KEY,
      listCache([wrapper("a", 1), wrapper("b", 3)]),
    );
    queryClient.setQueryData(
      GENERAL_LIST_KEY,
      listCache([wrapper("a", 1), wrapper("b", 3)]),
    );

    const { result } = renderCacheUtils();
    result.current.removeVisibleItem("b");

    const tipoCache = queryClient.getQueryData<PaginatedCache>(TIPO_LIST_KEY);
    const generalCache =
      queryClient.getQueryData<PaginatedCache>(GENERAL_LIST_KEY);

    expect(readIds(tipoCache)).toEqual(["a"]);
    expect(readIds(generalCache)).toEqual(["a"]);
  });
});
