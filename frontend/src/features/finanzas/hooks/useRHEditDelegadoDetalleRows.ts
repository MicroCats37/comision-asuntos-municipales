/**
 * Resolución de identidades para la edición de un RH mensual de Delegado.
 *
 * El PATCH (PATCH /finanzas/recibos-delegados/{rh_id}) sincroniza el conjunto
 * final de detalles. Para CONSERVAR una fila persistida necesita los mismos
 * identificadores con los que se creó:
 *
 *   - liquidacion_general_id   → LiquidacionGeneral del detalle
 *   - especialidad_revision_id → EspecialidadRevision de la asignación
 *
 * Esos identificadores NO viajan en el listado de RH mensuales (que solo
 * expone `detalle_id`), pero SÍ viajan en el listado flat de detalle
 * (GET /finanzas/recibos-delegados/detalle), indexado por `detalle_id`
 * (el id del DetalleHonorarioDelegado).
 *
 * Ese endpoint exige `tipo_liquidacion_codigo`. Cuando la operatividad del
 * recibo define un tipo se consulta solo ese; si la operatividad es wildcard
 * (sin tipo asignado) se consultan los tipos de delegado en paralelo y se
 * combinan por `detalle_id`.
 */
import { useMemo } from "react";
import { paginatedResponseSchema } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { DetalleDelegadoRow } from "../schemas/recibo-honorario.schema";
import { detalleDelegadoRowSchema } from "../schemas/recibo-honorario.schema";

const paginatedSchema = apiResponseSchema(
  paginatedResponseSchema(detalleDelegadoRowSchema),
);

/**
 * Tipos de liquidación con detalle de delegado. INSPECCION_OBRA queda fuera:
 * ese flujo es exclusivo de inspectores.
 */
export const DELEGADO_TIPO_CODIGOS = [
  "EDIFICACION",
  "HABILITACION_URBANA",
  "MECANICA_SUELOS",
  "IMPACTO_VIAL",
  "TALUDES",
] as const;

interface DetalleRowsParams {
  cip: string | null | undefined;
  periodo?: number | null;
  mes?: number | null;
}

interface UseRHEditDelegadoDetalleRowsProps extends DetalleRowsParams {
  /** Tipo de liquidación de la operatividad; null = operatividad wildcard. */
  tipoLiquidacionCodigo?: string | null;
  enabled?: boolean;
}

function useDetalleRowsQuery(
  params: DetalleRowsParams,
  tipoCodigo: string,
  enabled: boolean,
) {
  return useApiQuery({
    queryKey: [
      "finanzas",
      "recibos-delegados",
      "detalle",
      "edicion",
      tipoCodigo,
      params.cip,
      params.periodo ?? null,
      params.mes ?? null,
    ],
    url: "/finanzas/recibos-delegados/detalle",
    schema: paginatedSchema,
    params: {
      page: 1,
      page_size: 100,
      delegado_cip: params.cip ?? undefined,
      periodo: params.periodo ?? undefined,
      mes: params.mes ?? undefined,
      tipo_liquidacion_codigo: tipoCodigo,
    },
    queryOptions: {
      enabled,
      select: (data) =>
        data?.data ?? {
          items: [] as DetalleDelegadoRow[],
          total: 0,
          page: 1,
          page_size: 100,
          total_pages: 1,
        },
    },
  });
}

/**
 * Devuelve las filas flat de detalle del delegado que corresponden al RH que se
 * está editando, indexadas por `detalle_id` (id del DetalleHonorarioDelegado).
 */
export function useRHEditDelegadoDetalleRows({
  cip,
  periodo,
  mes,
  tipoLiquidacionCodigo,
  enabled = false,
}: UseRHEditDelegadoDetalleRowsProps) {
  const active = enabled && Boolean(cip);
  const params: DetalleRowsParams = { cip: cip ?? "", periodo, mes };
  const matches = (codigo: string) =>
    active && (!tipoLiquidacionCodigo || tipoLiquidacionCodigo === codigo);

  const q0 = useDetalleRowsQuery(params, "EDIFICACION", matches("EDIFICACION"));
  const q1 = useDetalleRowsQuery(
    params,
    "HABILITACION_URBANA",
    matches("HABILITACION_URBANA"),
  );
  const q2 = useDetalleRowsQuery(
    params,
    "MECANICA_SUELOS",
    matches("MECANICA_SUELOS"),
  );
  const q3 = useDetalleRowsQuery(
    params,
    "IMPACTO_VIAL",
    matches("IMPACTO_VIAL"),
  );
  const q4 = useDetalleRowsQuery(params, "TALUDES", matches("TALUDES"));

  /** Filas combinadas por `detalle_id` — la clave que usa el PATCH. */
  const rowsByDetalleId = useMemo(() => {
    const map = new Map<string, DetalleDelegadoRow>();
    const items = [
      ...(q0.data?.items ?? []),
      ...(q1.data?.items ?? []),
      ...(q2.data?.items ?? []),
      ...(q3.data?.items ?? []),
      ...(q4.data?.items ?? []),
    ];
    for (const row of items) {
      map.set(row.id, row);
    }
    return map;
  }, [q0.data, q1.data, q2.data, q3.data, q4.data]);

  return {
    rowsByDetalleId,
    isLoading: active && [q0, q1, q2, q3, q4].some((q) => q.isLoading),
    isError: active && [q0, q1, q2, q3, q4].some((q) => q.isError),
  };
}
