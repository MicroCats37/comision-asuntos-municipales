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
 * - Últimas revisiones: ["liquidaciones", "generales", "ultimas-revisiones"]
 * - Detalle: ["liquidaciones", "<tipo>", id]
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
interface PaginatedCache {
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

/** Rebuild paginated cache con item insertado en posición 0 (prepend). Respeta el envelope ApiResponse. */
function insertItemAtStart(
  old: PaginatedCache | undefined,
  newItem: LiquidacionWrapper,
): PaginatedCache {
  if (!old || !old.data || !Array.isArray(old.data.items)) {
    return old as PaginatedCache;
  }
  const items = [newItem, ...old.data.items];
  // Recortar al page_size si existe para no agrandar la página
  const pageSize = old.data.page_size;
  const trimmedItems = pageSize ? items.slice(0, pageSize) : items;
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

/** "todas" suffix para lista general sin ultimas-revisiones. */
export const GENERALES_TODAS_SUFFIX = "todas" as const;

/** "ultimas-revisiones" suffix. */
export const ULTIMAS_REVISIONES_SUFFIX = "ultimas-revisiones" as const;

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
     * Inserta un item creado en las caches de lista visibles.
     *
     * Política conservadora:
     * - Solo inserta en página 1 (query keys que terminan en page=1 o sin page implícito).
     * - No inserta si hay filtros activos no evaluables (razonSocial, documento, etc. distintos de undefined).
     *
     * Caches actualizadas:
     * 1. Lista tipo-específica (tipoKey debe ser uno de "edificaciones", "habilitacion-urbana", etc.)
     * 2. Lista general "todas"
     */
    insertCreatedItem(
      item: LiquidacionWrapper,
      options: { tipoKey: string },
    ): void {
      const wrapperId = extractWrapperId(item);

      // 1) Lista tipo-específica
      // Las listas tipo-específicas usan useLiquidacionList que anexa [page, pageSize, filtros, params]
      // Cacheado como ApiResponse envelope: { success, data: { items, total, page, ... } }.
      // Solamente insetar en caches de página 1 sin filtros complejos
      const tipoPrefijo = ["liquidaciones", options.tipoKey] as const;
      queryClient.setQueriesData<PaginatedCache>(
        { queryKey: tipoPrefijo },
        (old) => {
          if (!old?.data || !Array.isArray(old.data.items)) {
            return old as PaginatedCache;
          }
          // Solo insetar si estamos en página 1 (page === 1 o page no definido = 1 implícito)
          const page = old.data.page ?? 1;
          if (page !== 1) return old as PaginatedCache;
          return insertItemAtStart(old, item);
        },
      );

      // 2) Lista general "todas"
      // Query keys: ["liquidaciones", "generales", "todas", page, pageSize, tipo, documento, razonSocial, propietario, numero, params]
      // Cacheado como ApiResponse envelope. Insetar solo en página 1 sin filtros
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
          return insertItemAtStart(old, item);
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
     * - Lista "ultimas-revisiones"
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

      // 3) Lista ultimas-revisiones
      const ultimasPrefijo = [
        ...GENERALES_KEY_PREFIX,
        ULTIMAS_REVISIONES_SUFFIX,
      ] as const;
      queryClient.setQueriesData<PaginatedCache>(
        { queryKey: ultimasPrefijo },
        (old) => {
          if (!old?.data || !Array.isArray(old.data.items)) {
            return old as PaginatedCache;
          }
          const result = removeItemById(old, id);
          return result ?? (old as PaginatedCache);
        },
      );
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

    /**
     * Reemplaza un item en las caches de últimas revisiones.
     * Para nueva-revision: la revisión previa debe salir y la nueva debe entrar.
     *
     * Política:
     * - Si previousId existe, remover previousId e insertar el nuevo item.
     * - Si no hay previousId, remover cualquier item con mismo wrapper id e insetar.
     */
    replaceLatestRevision(
      item: LiquidacionWrapper,
      options: { tipoKey: string; previousId?: string },
    ): void {
      const wrapperId = extractWrapperId(item);
      const previousId = options.previousId;

      const ultimasPrefijo = [
        ...GENERALES_KEY_PREFIX,
        ULTIMAS_REVISIONES_SUFFIX,
      ] as const;

      queryClient.setQueriesData<PaginatedCache>(
        { queryKey: ultimasPrefijo },
        (old) => {
          if (!old?.data || !Array.isArray(old.data.items)) {
            return old as PaginatedCache;
          }
          let items = old.data.items as LiquidacionWrapper[];

          // Remover previousId si existe
          if (previousId) {
            items = items.filter(
              (it) => String(it.liquidacion_general?.id) !== String(previousId),
            );
          }

          // Remover el item con mismo wrapper id (revisión previa con mismo id si no hay previousId)
          items = items.filter(
            (it) => String(it.liquidacion_general?.id) !== wrapperId,
          );

          // Insetar la nueva revisión al inicio
          const page = old.data.page ?? 1;
          if (page !== 1) {
            return {
              ...old,
              data: { ...old.data, items },
            } as PaginatedCache;
          }

          const pageSize = old.data.page_size;
          const newItems = [item, ...items];
          const trimmedItems = pageSize
            ? newItems.slice(0, pageSize)
            : newItems;

          return {
            ...old,
            data: {
              ...old.data,
              items: trimmedItems as LiquidacionWrapper[],
              total: previousId
                ? old.data.total
                : Math.min((old.data.total ?? 0) + 1, old.data.total ?? 0),
            },
          };
        },
      );
    },

    /**
     * Actualiza las caches de lista general "todas" con un item.
     * Útil para nueva-revision y relacionada cuando se quiere mantener sincronizada
     * la lista general.
     */
    insertInGenerales(item: LiquidacionWrapper): void {
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
          return insertItemAtStart(old, item);
        },
      );
    },
  };
}
