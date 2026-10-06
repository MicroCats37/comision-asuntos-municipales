/**
 * Hook para tarifas GENERALES (todas, sin filtrar por tipo).
 * Endpoint: GET /liquidaciones/tarifas
 *
 * - vigentes=false (default): devuelve todas las tarifas, opcionalmente filtradas por rango.
 * - vigentes=true: devuelve tarifas VIGENTES de todos los tipos, unpaginado.
 * - fecha_ref: fecha de referencia para filtro vigentes (default: hoy).
 */

import { z } from "zod";
import { useApiQuery } from "@/hooks";
import {
  tarifaGeneralItemSchema,
  type TarifaGeneralItem,
} from "../types/finanzas.types";
import { apiResponseSchema } from "@/types/api.types";

interface UseTarifasGeneralesProps {
  vigentes?: boolean;
  fechaRef?: string;
  fechaDesde?: string;
  fechaHasta?: string;
}

export function useTarifasGenerales({
  vigentes = false,
  fechaRef,
  fechaDesde,
  fechaHasta,
}: UseTarifasGeneralesProps = {}) {
  // Build query params
  const params: Record<string, string | number | boolean> = {
    vigentes,
  };
  if (fechaRef) {
    params.fecha_ref = fechaRef;
  }
  if (fechaDesde) {
    params.fecha_desde = fechaDesde;
  }
  if (fechaHasta) {
    params.fecha_hasta = fechaHasta;
  }

  const query = useApiQuery({
    queryKey: [
      "liquidaciones",
      "tarifas",
      "generales",
      vigentes,
      fechaRef,
      fechaDesde,
      fechaHasta,
    ],
    url: "/liquidaciones/tarifas",
    schema: apiResponseSchema(z.array(tarifaGeneralItemSchema)),
    params,
    queryOptions: {
      enabled: true,
      select: (data) => {
        if (!data?.data) {
          return [] as TarifaGeneralItem[];
        }
        return data.data as TarifaGeneralItem[];
      },
    },
  });

  return {
    ...query,
    items: query.data ?? ([] as TarifaGeneralItem[]),
  };
}
