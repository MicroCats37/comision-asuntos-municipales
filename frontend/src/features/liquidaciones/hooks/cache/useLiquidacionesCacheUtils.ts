/**
 * useLiquidacionesCacheUtils
 *
 * Helper para actualizar el cache de React Query de forma reactiva cuando se crean,
 * eliminan (soft-delete) o actualizan liquidaciones.
 *
 * Los items de liquidación son wrappers: { liquidacion_general: { id, ... }, liquidacion_tipo, liquidacion_especifica }.
 * El id canónico es siempre item.liquidacion_general.id.
 *
 * Esta utilidad opera sobre:
 * - Listas tipo-específicas: ["liquidaciones", "<tipo>"]
 * - Listas generales: ["liquidaciones", "generales", "todas"]
 * - Detalle: ["liquidaciones", "<tipo>", id] y ["liquidaciones", "generales", id]
 *
 * NO existe una cache de "última revisión": el backend ya no expone
 * `GET /liquidaciones/generales/ultimas-revisiones` ni
 * `GET /liquidaciones/edificaciones/ultima-revision`, y el modelo de datos no
 * tiene una revisión canónica por proyecto (el número de revisión es una
 * ETIQUETA editable y puede repetirse entre hermanos).
 *
 * Política de escritura (invariante central de esta fase):
 * una liquidación creada, revisada o relacionada se INSERTA o ACTUALIZA en las
 * listas SIN eliminar nunca la previa seleccionada ni sus hermanos. Solo el
 * soft-delete (`removeVisibleItem`) saca un item de las listas.
 */

import { useQueryClient } from "@tanstack/react-query";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Wrapper de liquidación tal como viene del backend.
 * Todos los campos son opcionales para tolerate schemas que pueden variar.
 */
export interface LiquidacionWrapper {
  liquidacion_general?: {
    id?: string | number;
    eliminado?: boolean;
    numero_revision?: number;
    tipo_liquidacion?: {
      codigo?: string;
      nombre?: string;
    };
    // otros campos de LiquidacionGeneralOutputSchema
    [key: string]: unknown;
  };
  liquidacion_especifica?: unknown;
  liquidacion_tipo?: unknown;
  [key: string]: unknown;
}

/**
 * Shape cacheado por useApiQuery: envelope ApiResponse envolviendo la respuesta
 * paginada. `data` puede ser null en respuestas sin payload, y los items viven
 * dentro de `old.data.items` (no en `old.items` directamente). Los updaters
 * deben respetar esta estructura al escribir.
 */
export interface PaginatedCache {
  success?: boolean;
  data: {
    items: LiquidacionWrapper[];
    total: number;
    total_pages?: number;
    page_size?: number;
    page?: number;
  } | null;
  error?: unknown;
  message?: string | null;
  [key: string]: unknown;
}

/** Posición de inserción en una lista paginada. */
export type InsertPosition = "start" | "end";

// ---------------------------------------------------------------------------
// Helpers internos
// ---------------------------------------------------------------------------

/** Extrae el id del wrapper (nunca devuelve undefined para wrappers válidos). */
function extractWrapperId(item: LiquidacionWrapper): string {
  const id = item.liquidacion_general?.id;
  if (id == null) {
    throw new Error(
      "useLiquidacionesCacheUtils: item.liquidacion_general.id es undefined. " +
        "No se puede operar sobre un wrapper sin id.",
    );
  }
  return String(id);
}

/**
 * Rebuild de una cache paginada con un item INSERTADO o ACTUALIZADO.
 *
 * Reglas (invariantes de paginación):
 * - Si el id ya existe en la página → se ACTUALIZA EN SU LUGAR: se conserva la
 *   posición y el `total` NO cambia. Nunca se duplica.
 * - Si el id no existe → se inserta (prepend por defecto) y el `total` crece
 *   en 1.
 * - La longitud de la página se respeta (`page_size`).
 * - NUNCA se elimina ningún otro item: ni la previa seleccionada ni sus
 *   hermanos con el mismo número de revisión.
 *
 * Respeta el envelope ApiResponse ({ success, data: { items, total, ... } }).
 */
export function upsertItemInPaginatedCache(
  old: PaginatedCache | undefined,
  newItem: LiquidacionWrapper,
  position: InsertPosition = "start",
): PaginatedCache {
  if (!old || !old.data || !Array.isArray(old.data.items)) {
    return old as PaginatedCache;
  }
  const items = old.data.items as LiquidacionWrapper[];
  const newId = String(newItem.liquidacion_general?.id);

  const existingIdx = items.findIndex(
    (item) => String(item.liquidacion_general?.id) === newId,
  );

  // Actualización en el lugar — conserva posición y total.
  if (existingIdx !== -1) {
    const updatedItems = [...items];
    updatedItems[existingIdx] = newItem;
    return {
      ...old,
      data: {
        ...old.data,
        items: updatedItems as LiquidacionWrapper[],
      },
    };
  }

  const nextItems =
    position === "start" ? [newItem, ...items] : [...items, newItem];
  // Recortar al page_size si existe para no agrandar la página
  const pageSize = old.data.page_size;
  const trimmedItems = pageSize ? nextItems.slice(0, pageSize) : nextItems;
  return {
    ...old,
    data: {
      ...old.data,
      items: trimmedItems as LiquidacionWrapper[],
      total: (old.data.total ?? 0) + 1,
    },
  };
}

/** Rebuild paginated cache con item removido por id. Retorna null si no se encontró. Respeta el envelope ApiResponse. */
function removeItemById(
  old: PaginatedCache | undefined,
  id: string,
): PaginatedCache | null {
  if (!old || !old.data || !Array.isArray(old.data.items)) {
    return old as PaginatedCache;
  }
  const idx = old.data.items.findIndex(
    (item) => String(item.liquidacion_general?.id) === id,
  );
  if (idx === -1) return null;
  const items = old.data.items.filter(
    (_, i) => i !== idx,
  ) as LiquidacionWrapper[];
  return {
    ...old,
    data: {
      ...old.data,
      items,
      total: Math.max((old.data.total ?? 1) - 1, 0),
    },
  };
}

/** Actualiza el campo liquidacion_general.eliminado = true en el detail cache. */
function markDetailDeleted(
  old: LiquidacionWrapper | unknown,
  id: string,
): LiquidacionWrapper | unknown {
  if (!old || typeof old !== "object") return old;
  const w = old as LiquidacionWrapper;
  if (String(w.liquidacion_general?.id) !== id) return old;
  return {
    ...w,
    liquidacion_general: {
      ...w.liquidacion_general,
      eliminado: true,
    },
  };
}

// ---------------------------------------------------------------------------
// Query key prefixes por tipo
// ---------------------------------------------------------------------------

/** Prefijos de query key para listas tipo-específicas. */
export const TIPO_KEY_PREFIXES = [
  ["liquidaciones", "edificaciones"],
  ["liquidaciones", "habilitacion-urbana"],
  ["liquidaciones", "mecanica-suelos"],
  ["liquidaciones", "taludes"],
  ["liquidaciones", "impacto-vial"],
  ["liquidaciones", "inspeccion-obra"],
] as const;

/** Query key prefix para listas generales. */
export const GENERALES_KEY_PREFIX = ["liquidaciones", "generales"] as const;

/**
 * "todas" suffix del listado general completo.
 *
 * Se conserva (y no se elimina) porque separa el LISTADO
 * `["liquidaciones", "generales", "todas", ...]` de los DETALLES
 * `["liquidaciones", "generales", id]`: sin este segmento, cualquier
 * `setQueriesData` por prefijo general pisaría también los detalles.
 *
 * Ya NO existe el modo "ultimas-revisiones": el backend retiró ese endpoint
 * y el modelo no tiene revisión canónica.
 */
export const GENERALES_TODAS_SUFFIX = "todas" as const;

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useLiquidacionesCacheUtils() {
  const queryClient = useQueryClient();

  return {
    /**
     * Extrae el id canónico de un wrapper.
     * @throws si el wrapper no tiene liquidacion_general.id
     */
    getWrapperId(item: LiquidacionWrapper): string {
      return extractWrapperId(item);
    },

    /**
     * INSERTA o ACTUALIZA un item en las caches de lista visibles.
     *
     * Política (invariante central de la Fase 5):
     * - NUNCA se elimina ningún registro existente: ni la previa seleccionada
     *   ni sus hermanos con el mismo número de revisión.
     * - Si el id ya está en la página, se actualiza EN SU LUGAR (no se duplica
     *   y el `total` no cambia).
     * - Solo escribe en página 1 (query keys con page === 1 o page implícito).
     *
     * Caches actualizadas:
     * 1. Lista tipo-específica (tipoKey debe ser uno de "edificaciones", "habilitacion-urbana", etc.)
     * 2. Lista general "todas"
     * 3. Seed del detalle tipo-específico y general
     */
    upsertCreatedItem(
      item: LiquidacionWrapper,
      options: { tipoKey: string; position?: InsertPosition },
    ): void {
      const wrapperId = extractWrapperId(item);

      // 1) Lista tipo-específica
      // Las listas tipo-específicas usan useLiquidacionList que anexa [page, pageSize, filtros, params]
      // Cacheado como ApiResponse envelope: { success, data: { items, total, page, ... } }.
      const tipoPrefijo = ["liquidaciones", options.tipoKey] as const;
      queryClient.setQueriesData<PaginatedCache>(
        { queryKey: tipoPrefijo },
        (old) => {
          if (!old?.data || !Array.isArray(old.data.items)) {
            return old as PaginatedCache;
          }
          // Solo escribir si estamos en página 1 (page === 1 o page no definido = 1 implícito)
          const page = old.data.page ?? 1;
          if (page !== 1) return old as PaginatedCache;
          return upsertItemInPaginatedCache(old, item, options.position);
        },
      );

      // 2) Lista general "todas"
      // Query keys: ["liquidaciones", "generales", "todas", page, pageSize, tipo, documento, razonSocial, propietario, numero, params]
      // Cacheado como ApiResponse envelope. Escribir solo en página 1
      const generalesPrefijo = [
        ...GENERALES_KEY_PREFIX,
        GENERALES_TODAS_SUFFIX,
      ] as const;
      queryClient.setQueriesData<PaginatedCache>(
        { queryKey: generalesPrefijo },
        (old) => {
          if (!old?.data || !Array.isArray(old.data.items)) {
            return old as PaginatedCache;
          }
          const page = old.data.page ?? 1;
          if (page !== 1) return old as PaginatedCache;
          return upsertItemInPaginatedCache(old, item, options.position);
        },
      );

      // 3) Seed detail cache tipo-específico
      // Detail key: ["liquidaciones", tipoKey, id]
      queryClient.setQueryData([...tipoPrefijo, wrapperId], item);

      // 4) Seed detail cache general (generales usa el id directo)
      queryClient.setQueryData([...GENERALES_KEY_PREFIX, wrapperId], item);
    },

    /**
     * Remueve un item de todas las caches de lista visibles (soft-delete).
     *
     * Caches actualizadas:
     * - Todas las listas tipo-específicas
     * - Lista general "todas"
     *
     * Si el item no está en una cache particular (no se encontró por id), se ignora.
     */
    removeVisibleItem(id: string): void {
      // 1) Todas las listas tipo-específicas
      for (const tipoPrefijo of TIPO_KEY_PREFIXES) {
        queryClient.setQueriesData<PaginatedCache>(
          { queryKey: tipoPrefijo },
          (old) => {
            if (!old?.data || !Array.isArray(old.data.items)) {
              return old as PaginatedCache;
            }
            const result = removeItemById(old, id);
            return result ?? (old as PaginatedCache);
          },
        );
      }

      // 2) Lista general "todas"
      const generalesTodaskPrefijo = [
        ...GENERALES_KEY_PREFIX,
        GENERALES_TODAS_SUFFIX,
      ] as const;
      queryClient.setQueriesData<PaginatedCache>(
        { queryKey: generalesTodaskPrefijo },
        (old) => {
          if (!old?.data || !Array.isArray(old.data.items)) {
            return old as PaginatedCache;
          }
          const result = removeItemById(old, id);
          return result ?? (old as PaginatedCache);
        },
      );

      // 3) Lista ultimas-revisiones: RETIRADA (endpoint y modelo canónico
      // eliminados en la Fase 3). Ya no existe una cache de "última revisión".
    },

    /**
     * Marca el detalle cacheado como eliminado (liquidacion_general.eliminado = true).
     * Solo opera si el item en cache tiene el mismo id.
     *
     * Caches actualizadas:
     * - Detail tipo-específico: ["liquidaciones", tipoKey, id]
     * - Detail general: ["liquidaciones", "generales", id]
     */
    markDetailDeleted(id: string, tipoKey?: string): void {
      if (tipoKey) {
        // Detail tipo-específico
        queryClient.setQueryData(["liquidaciones", tipoKey, id], (old) =>
          markDetailDeleted(old, id),
        );
      }
      // Detail general
      queryClient.setQueryData([...GENERALES_KEY_PREFIX, id], (old) =>
        markDetailDeleted(old, id),
      );
    },

    /*
     * `replaceLatestRevision` fue RETIRADO en la Fase 5.
     *
     * Antes: sacaba la revisión PREVIA de la cache de "últimas revisiones" y
     * metía la nueva. Ese modelo de "revisión canónica" ya no existe: el
     * backend retiró `GET /liquidaciones/generales/ultimas-revisiones` y
     * `GET /liquidaciones/edificaciones/ultima-revision`, y el número de
     * revisión es una etiqueta editable que puede repetirse entre hermanos.
     *
     * Hoy la operación correcta es `upsertCreatedItem`: la liquidación nueva
     * (o revisada) se inserta/actualiza SIN eliminar la previa seleccionada ni
     * sus hermanos.
     */
  };
}
