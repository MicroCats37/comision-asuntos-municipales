/**
 * useComprobanteCacheSync — política de caché HÍBRIDA del comprobante.
 *
 * Decisión `architecture/comprobante-cache-strategy`:
 * - Las LISTAS de Liquidaciones y el DETALLE tienen shape estable → se
 *   PARCHEAN en caché con la `LiquidacionGeneral` que devuelve el backend.
 * - El BROWSE RH compone filtros y tipos heterogéneos → hace `refetch()`
 *   explícito: su clave `["rh-browse", …]` queda fuera del prefijo
 *   `["liquidaciones"]`, así que este helper no lo toca.
 *
 * `useApiQuery` cachea el ENVELOPE parseado `{ success, data, error }` (el
 * `select` se aplica en la LECTURA). Por eso:
 * - el DETALLE se MERGEa dentro de `data.liquidacion_general` (no se replaces
 *   la entrada) y conserva `liquidacion_especifica` y `liquidacion_tipo`;
 * - el item de las LISTAS es un WRAPPER `{ liquidacion_general,
 *   liquidacion_especifica, liquidacion_tipo }` y la API devuelve la entidad
 *   PLANA → se MERGEa dentro de `items[i].liquidacion_general`.
 *
 * Clave REAL del detalle: `["liquidaciones", "generales", "detalle", <id>]`.
 * La clave "detail" NO existe en el registro de caché.
 */
import { type QueryClient, useQueryClient } from "@tanstack/react-query";
import type { LiquidacionGeneralOutput } from "../../schemas/liquidacion-base.schema";

/** Prefijo REAL de la clave de detalle de una liquidación. */
export const DETALLE_COMPROBANTE_KEY = [
  "liquidaciones",
  "generales",
  "detalle",
] as const;

/** Prefijo REAL de las claves de listado de liquidaciones. */
export const LISTAS_COMPROBANTE_KEY_PREFIX = ["liquidaciones"] as const;

/** Item de un listado: wrapper con la entidad en `liquidacion_general`. */
interface ItemListadoLiquidacion {
  liquidacion_general?: Record<string, unknown>;
  [key: string]: unknown;
}

/** Envelope cacheado por `useApiQuery` para un listado de liquidaciones. */
interface ListasComprobanteCache {
  success?: boolean;
  data: {
    items?: ItemListadoLiquidacion[];
    total?: number;
    [key: string]: unknown;
  } | null;
  error?: unknown;
  message?: string | null;
  [key: string]: unknown;
}

/** Envelope cacheado por `useApiQuery` para el detalle (3 wrappers). */
interface DetalleComprobanteCache {
  success?: boolean;
  data: {
    liquidacion_general?: Record<string, unknown>;
    liquidacion_especifica?: unknown;
    liquidacion_tipo?: unknown;
    [key: string]: unknown;
  } | null;
  error?: unknown;
  message?: string | null;
  [key: string]: unknown;
}

/** Merge (NO replace) del `liquidacion_general` cacheado con el del backend. */
function mergeLiquidacionGeneral(
  cached: Record<string, unknown> | undefined,
  updated: LiquidacionGeneralOutput,
): Record<string, unknown> {
  return { ...(cached ?? {}), ...updated };
}

/** Id canónico de un item de listado (`null` si el wrapper no trae id). */
function readItemId(item: ItemListadoLiquidacion): string | null {
  const raw = item.liquidacion_general?.id;
  if (typeof raw !== "string" && typeof raw !== "number") return null;
  return String(raw);
}

/**
 * Parchea la caché del DETALLE con la `LiquidacionGeneral` devuelta.
 *
 * - Usa la clave REAL `["liquidaciones", "generales", "detalle", <id>]`.
 * - Sólo parchea una entrada EXISTENTE: no se crean claves de detalle nuevas.
 * - Conserva el envelope y los hermanos `liquidacion_especifica` /
 *   `liquidacion_tipo` que el `select` del hook de detalle espera.
 */
export function patchDetalleComprobanteCache(
  queryClient: QueryClient,
  liquidacionId: string,
  updated: LiquidacionGeneralOutput,
): void {
  const queryKey = [...DETALLE_COMPROBANTE_KEY, liquidacionId];

  const current = queryClient.getQueryData<DetalleComprobanteCache>(queryKey);
  if (!current?.data?.liquidacion_general) return;

  queryClient.setQueryData<DetalleComprobanteCache>(queryKey, (old) => {
    const data = old?.data;
    if (!data?.liquidacion_general) return old;
    return {
      ...old,
      data: {
        ...data,
        liquidacion_general: mergeLiquidacionGeneral(
          data.liquidacion_general,
          updated,
        ),
      },
    };
  });
}

/**
 * Parchea las LISTAS que contengan la liquidación afectada.
 *
 * - Prefijo `["liquidaciones"]` + guarda de shape (`Array.isArray(data.items)`):
 *   cubre las listas por tipo y la general sin enumerarlas y deja intactas las
 *   cachés de detalle, filtros y catálogos.
 * - NO inserta, duplica ni elimina items; NO altera `total` ni la posición.
 * - NO toca el browse RH (`["rh-browse", …]`): ese hace `refetch()` explícito.
 */
export function patchListasComprobanteCache(
  queryClient: QueryClient,
  updated: LiquidacionGeneralOutput,
): void {
  const updatedId = String(updated.id);

  queryClient.setQueriesData<ListasComprobanteCache>(
    { queryKey: [...LISTAS_COMPROBANTE_KEY_PREFIX] },
    (old) => {
      const data = old?.data;
      if (!data || !Array.isArray(data.items)) return old;

      let changed = false;
      const items = data.items.map((item) => {
        if (readItemId(item) !== updatedId) return item;
        changed = true;
        return {
          ...item,
          liquidacion_general: mergeLiquidacionGeneral(
            item.liquidacion_general,
            updated,
          ),
        };
      });

      if (!changed) return old;
      return { ...old, data: { ...data, items } };
    },
  );
}

/**
 * Hook que expone la política de caché del comprobante sobre el `QueryClient`
 * del provider. Lo usan los hooks de mutación (`useCrearComprobante` /
 * `useEditarComprobante`) para que el POST y el PATCH dejen EXACTAMENTE la
 * misma forma en caché.
 */
export function useComprobanteCacheSync() {
  const queryClient = useQueryClient();

  return {
    /** Parchea sólo el detalle de la liquidación. */
    patchDetalle(
      liquidacionId: string,
      updated: LiquidacionGeneralOutput,
    ): void {
      patchDetalleComprobanteCache(queryClient, liquidacionId, updated);
    },
    /** Parchea sólo las listas de liquidaciones. */
    patchListas(updated: LiquidacionGeneralOutput): void {
      patchListasComprobanteCache(queryClient, updated);
    },
    /** Parchea detalle + listas (operación completa tras una mutación). */
    syncComprobante(
      liquidacionId: string,
      updated: LiquidacionGeneralOutput,
    ): void {
      patchDetalleComprobanteCache(queryClient, liquidacionId, updated);
      patchListasComprobanteCache(queryClient, updated);
    },
  };
}
