/**
 * Hooks para Liquidaciones No Edificación.
 * Usa useApiCreate genérico del proyecto.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { z } from "zod";
import { useApiCreate, useApiQuery } from "@/hooks";
import {
  cotizacionM2ResponseSchema,
  cotizacionIOResponseSchema,
  crearLiquidacionNoEdificacionResponseSchema,
  liquidacionesNoEdificacionResponseSchema,
} from "../schemas/liquidacion-no-edificacion.schema";
import type {
  CotizarInspeccionObraPrimeraRevisionIn,
  CotizarM2PrimeraRevisionIn,
  CotizacionM2Response,
  CotizacionIOResponse,
  CrearLiquidacionInspeccionObraIn,
  LiquidacionKind,
  LiquidacionM2BaseIn,
  LiquidacionM2Kind,
  LiquidacionesNoEdificacionPaginated,
} from "../types/liquidacion-no-edificacion.types";

// ── Hooks ──────────────────────────────────────────────────────────────────

/**
 * Hook para crear primera revisión de liquidación M2-based.
 * Válido para: Habilitación Urbana, Mecánica de Suelos, Impacto Vial, Taludes.
 */
export function useCrearNoEdificacionM2(kind: LiquidacionM2Kind) {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    z.infer<typeof crearLiquidacionNoEdificacionResponseSchema>,
    { liquidacion: LiquidacionM2BaseIn }
  >({
    url: `/liquidaciones/${kind}/primera-revision`,
    schema: crearLiquidacionNoEdificacionResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
      },
    },
  });

  // Wrapper que formatea payload como { liquidacion: ... } para la API
  const crearMutation = {
    ...mutation,
    mutate: (payload: LiquidacionM2BaseIn) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (payload: LiquidacionM2BaseIn) => {
      return mutation.mutateAsync({ liquidacion: payload });
    },
  };

  return crearMutation;
}

/**
 * Hook para crear primera revisión de Inspección de Obra.
 */
export function useCrearNoEdificacionInspeccionObra() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    z.infer<typeof crearLiquidacionNoEdificacionResponseSchema>,
    { liquidacion: CrearLiquidacionInspeccionObraIn }
  >({
    url: `/liquidaciones/inspeccion-obra/primera-revision`,
    schema: crearLiquidacionNoEdificacionResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
      },
    },
  });

  const crearMutation = {
    ...mutation,
    mutate: (payload: CrearLiquidacionInspeccionObraIn) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (payload: CrearLiquidacionInspeccionObraIn) => {
      return mutation.mutateAsync({ liquidacion: payload });
    },
  };

  return crearMutation;
}

/**
 * Hook polimórfico para crear primera revisión según kind.
 */
export function useCrearNoEdificacion(kind: LiquidacionKind) {
  if (kind === "inspeccion-obra") {
    return useCrearNoEdificacionInspeccionObra();
  }
  return useCrearNoEdificacionM2(kind as LiquidacionM2Kind);
}

/**
 * Hook para cotizar primera revisión M2-based.
 */
export function useCotizarNoEdificacionM2(kind: LiquidacionM2Kind) {
  const mutation = useApiCreate<
    z.infer<typeof cotizacionM2ResponseSchema>,
    { liquidacion: CotizarM2PrimeraRevisionIn }
  >({
    url: `/liquidaciones/${kind}/cotizar/primera-revision`,
    schema: cotizacionM2ResponseSchema,
    options: {},
  });

  // Wrapper que extrae data.data del resultado ApiResponse
  const cotizacionMutation = {
    ...mutation,
    mutate: (payload: CotizarM2PrimeraRevisionIn) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (
      payload: CotizarM2PrimeraRevisionIn,
    ): Promise<CotizacionM2Response> => {
      const result = await mutation.mutateAsync({ liquidacion: payload });
      return result.data as CotizacionM2Response;
    },
  };

  return cotizacionMutation;
}

/**
 * Hook para cotizar primera revisión Inspección de Obra.
 */
export function useCotizarNoEdificacionInspeccionObra() {
  const mutation = useApiCreate<
    z.infer<typeof cotizacionIOResponseSchema>,
    { liquidacion: CotizarInspeccionObraPrimeraRevisionIn }
  >({
    url: `/liquidaciones/inspeccion-obra/cotizar/primera-revision`,
    schema: cotizacionIOResponseSchema,
    options: {},
  });

  const cotizacionMutation = {
    ...mutation,
    mutate: (payload: CotizarInspeccionObraPrimeraRevisionIn) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (
      payload: CotizarInspeccionObraPrimeraRevisionIn,
    ): Promise<CotizacionIOResponse> => {
      const result = await mutation.mutateAsync({ liquidacion: payload });
      return result.data as CotizacionIOResponse;
    },
  };

  return cotizacionMutation;
}

/**
 * Hook polimórfico para cotizar primera revisión según kind.
 */
export function useCotizarNoEdificacion(kind: LiquidacionKind) {
  if (kind === "inspeccion-obra") {
    return useCotizarNoEdificacionInspeccionObra();
  }
  return useCotizarNoEdificacionM2(kind as LiquidacionM2Kind);
}

// ── List Hooks ────────────────────────────────────────────────────────────────

/**
 * Hook para lista de liquidaciones no-edificación con paginación.
 * Endpoint: GET /liquidaciones/{kind}
 */
interface UseLiquidacionesNoEdificacionProps {
  kind: LiquidacionKind;
  page?: number;
  pageSize?: number;
}

export function useLiquidacionesNoEdificacion({
  kind,
  page = 1,
  pageSize = 10,
}: UseLiquidacionesNoEdificacionProps) {
  const [currentPage, setCurrentPage] = useState(page);
  const [currentPageSize, setCurrentPageSize] = useState(pageSize);

  const params: Record<string, string | number> = {
    page: currentPage,
    page_size: currentPageSize,
  };

  const query = useApiQuery({
    queryKey: [
      "liquidaciones",
      "no-edificacion",
      kind,
      currentPage,
      currentPageSize,
    ],
    url: `/liquidaciones/${kind}`,
    schema: liquidacionesNoEdificacionResponseSchema,
    params,
    queryOptions: {
      select: (data): LiquidacionesNoEdificacionPaginated => {
        if (!data.data) {
          return {
            items: [],
            total: 0,
            page: currentPage,
            page_size: currentPageSize,
            total_pages: 1,
          };
        }
        return data.data;
      },
    },
  });

  return {
    ...query,
    data: query.data,
    items: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    page: query.data?.page ?? currentPage,
    pageSize: query.data?.page_size ?? currentPageSize,
    totalPages: query.data?.total_pages ?? 1,
    setPage: setCurrentPage,
    setPageSize: setCurrentPageSize,
  };
}
