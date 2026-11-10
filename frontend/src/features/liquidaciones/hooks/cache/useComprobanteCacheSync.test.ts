/**
 * Política de caché híbrida del comprobante (`useComprobanteCacheSync`).
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en este slice (regla del
 * change): la ejecución ocurre en `sdd-verify`.
 *
 * Invariantes: el detalle se parchea en la clave REAL `["liquidaciones",
 * "generales", "detalle", <id>]` (nunca en "detail") y sólo si la entrada
 * EXISTE; el parche conserva el envelope y los hermanos del wrapper; el parche
 * de listas actualiza SOLO el item coincidente y NO altera `total`, la
 * posición ni los demás items; las cachés sin `data.items` y las que están
 * fuera del prefijo `["liquidaciones"]` (browse RH) quedan intactas.
 */
import { QueryClient } from "@tanstack/react-query";
import { beforeEach, describe, expect, it } from "vitest";
import type { LiquidacionGeneralOutput } from "../../schemas/liquidacion-base.schema";
import {
  DETALLE_COMPROBANTE_KEY,
  patchDetalleComprobanteCache,
  patchListasComprobanteCache,
} from "./useComprobanteCacheSync";

const ID = "11111111-1111-4111-8111-111111111111";
const OTRO = "22222222-2222-4222-8222-222222222222";
const TERCERO = "33333333-3333-4333-8333-333333333333";

const DETALLE_KEY = [...DETALLE_COMPROBANTE_KEY, ID];
const CLAVE_DETALLE_OLD = ["liquidaciones", "generales", "detail", ID];
const LISTA_TIPO_KEY = ["liquidaciones", "edificaciones", 1, 10];
const LISTA_GENERAL_KEY = ["liquidaciones", "generales", "todas", 1, 10];
const CACHE_SIN_ITEMS_KEY = ["liquidaciones", "filtros", "catalogo"];
const BROWSE_RH_KEY = ["rh-browse", "liquidaciones", "candidatas"];

/** Wrapper de un item de listado (la entidad vive en `liquidacion_general`). */
type Item = {
  liquidacion_general: LiquidacionGeneralOutput;
  liquidacion_especifica: { id: string; numero: number };
  liquidacion_tipo: { motor: string };
};

/** Envelope ApiResponse cacheado por `useApiQuery`. */
type Envelope<T> = {
  success: boolean;
  data: T | null;
  error: null;
  message: null;
};

/** Envelope cacheado del detalle (3 wrappers). */
type Detalle = Envelope<{
  liquidacion_general: LiquidacionGeneralOutput;
  liquidacion_especifica: { id: string; numero: number };
  liquidacion_tipo: { motor: string };
}>;

/** Envelope cacheado de un listado paginado. */
type Lista = Envelope<{
  items: Item[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}>;

// ── Fixtures ─────────────────────────────────────────────────────────────────

function liquidacion(
  id: string,
  comprobantes: LiquidacionGeneralOutput["comprobantes"] = [],
): LiquidacionGeneralOutput {
  return {
    id,
    fecha_registro: "2026-01-01T00:00:00Z",
    numero_revision: 1,
    sub_total: 100,
    total: 118,
    proyecto: {
      id: `proj-${id}`,
      nombre_propietario: "Propietario",
      direccion: "Av. Siempre Viva 742",
      entidad: null,
    },
    delegados: [],
    comprobantes,
  };
}

function comprobante(
  id: string,
): LiquidacionGeneralOutput["comprobantes"][number] {
  return {
    id,
    tipo_comprobante: "FACTURA",
    serie: "F001",
    numero: "123",
    fecha_emision: "2026-01-02",
    monto: 118,
    activo: true,
    motivo_reemplazo: null,
  };
}

function detalle(id: string = ID): Detalle {
  return {
    success: true,
    data: {
      liquidacion_general: liquidacion(id),
      liquidacion_especifica: { id: `esp-${id}`, numero: 7 },
      liquidacion_tipo: { motor: "PORCENTAJE_OBRA" },
    },
    error: null,
    message: null,
  };
}

function item(id: string): Item {
  return {
    liquidacion_general: liquidacion(id),
    liquidacion_especifica: { id: `esp-${id}`, numero: 3 },
    liquidacion_tipo: { motor: "M2" },
  };
}

function lista(items: Item[]): Lista {
  return {
    success: true,
    data: {
      items,
      total: items.length,
      page: 1,
      page_size: 10,
      total_pages: 1,
    },
    error: null,
    message: null,
  };
}

/** Parchea el detalle con un comprobante nuevo. */
function parcharDetalle(queryClient: QueryClient, id: string = ID): void {
  patchDetalleComprobanteCache(
    queryClient,
    id,
    liquidacion(id, [comprobante("cmp-1")]),
  );
}

/** Parchea las listas con un comprobante nuevo. */
function parcharListas(queryClient: QueryClient, id: string = ID): void {
  patchListasComprobanteCache(
    queryClient,
    liquidacion(id, [comprobante("cmp-1")]),
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("patchDetalleComprobanteCache — detalle", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient();
  });

  it("parchea la entrada existente en la clave real 'detalle'", () => {
    queryClient.setQueryData(DETALLE_KEY, detalle());

    parcharDetalle(queryClient);

    const cache = queryClient.getQueryData<Detalle>(DETALLE_KEY);
    expect(cache?.data?.liquidacion_general.comprobantes).toHaveLength(1);
    expect(cache?.data?.liquidacion_general.comprobantes[0]?.id).toBe("cmp-1");
  });

  it("conserva el envelope y los hermanos del wrapper", () => {
    queryClient.setQueryData(DETALLE_KEY, detalle());

    parcharDetalle(queryClient);

    const cache = queryClient.getQueryData<Detalle>(DETALLE_KEY);
    expect(cache?.success).toBe(true);
    expect(cache?.error).toBeNull();
    expect(cache?.message).toBeNull();
    expect(cache?.data?.liquidacion_especifica).toEqual({
      id: `esp-${ID}`,
      numero: 7,
    });
    expect(cache?.data?.liquidacion_tipo).toEqual({
      motor: "PORCENTAJE_OBRA",
    });
  });

  it("NO crea entradas bajo claves de detalle inexistentes", () => {
    parcharDetalle(queryClient);

    expect(queryClient.getQueryData(DETALLE_KEY)).toBeUndefined();
    expect(queryClient.getQueryData(CLAVE_DETALLE_OLD)).toBeUndefined();
  });
});

describe("patchListasComprobanteCache — listas", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient();
  });

  it("actualiza el item coincidente y conserva los hermanos del wrapper", () => {
    queryClient.setQueryData(LISTA_TIPO_KEY, lista([item(OTRO), item(ID)]));

    parcharListas(queryClient);

    const cache = queryClient.getQueryData<Lista>(LISTA_TIPO_KEY);
    const coincidence = cache?.data?.items[1];
    expect(coincidence?.liquidacion_general.comprobantes).toHaveLength(1);
    expect(coincidence?.liquidacion_general.comprobantes[0]?.id).toBe("cmp-1");
    expect(coincidence?.liquidacion_especifica).toEqual({
      id: `esp-${ID}`,
      numero: 3,
    });
    expect(coincidence?.liquidacion_tipo).toEqual({ motor: "M2" });
  });

  it("no altera total, la posición ni los demás items", () => {
    queryClient.setQueryData(
      LISTA_GENERAL_KEY,
      lista([item(OTRO), item(ID), item(TERCERO)]),
    );

    parcharListas(queryClient);

    const cache = queryClient.getQueryData<Lista>(LISTA_GENERAL_KEY);
    expect(cache?.data?.total).toBe(3);
    expect(cache?.data?.items).toHaveLength(3);
    expect(cache?.data?.items[0]?.liquidacion_general.id).toBe(OTRO);
    expect(cache?.data?.items[2]?.liquidacion_general.id).toBe(TERCERO);
    expect(
      cache?.data?.items[0]?.liquidacion_general.comprobantes,
    ).toHaveLength(0);
    expect(
      cache?.data?.items[2]?.liquidacion_general.comprobantes,
    ).toHaveLength(0);
  });

  it("no toca cachés sin data.items", () => {
    const cacheSinItems = {
      success: true,
      data: { valores: ["a", "b"] },
      error: null,
      message: null,
    };
    queryClient.setQueryData(CACHE_SIN_ITEMS_KEY, cacheSinItems);

    const detalleCache = detalle();
    queryClient.setQueryData(DETALLE_KEY, detalleCache);

    parcharListas(queryClient);

    expect(queryClient.getQueryData(CACHE_SIN_ITEMS_KEY)).toBe(cacheSinItems);
    expect(queryClient.getQueryData(DETALLE_KEY)).toBe(detalleCache);
  });

  it("no toca el browse RH (fuera del prefijo ['liquidaciones'])", () => {
    const browse = lista([item(ID)]);
    queryClient.setQueryData(BROWSE_RH_KEY, browse);

    parcharListas(queryClient);

    expect(queryClient.getQueryData(BROWSE_RH_KEY)).toBe(browse);
  });

  it("no crea entradas nuevas bajo el prefijo de liquidaciones", () => {
    parcharListas(queryClient);

    expect(queryClient.getQueryData(LISTA_TIPO_KEY)).toBeUndefined();
    expect(queryClient.getQueryData(LISTA_GENERAL_KEY)).toBeUndefined();
  });
});
