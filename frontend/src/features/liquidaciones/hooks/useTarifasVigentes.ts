/**
 * Hook unificado de tarifas vigentes.
 *
 * Endpoint: GET /liquidaciones/{tipo}/tarifas/vigentes
 * QueryKey ESTABLE y ÚNICA: ["liquidaciones", tipo, "tarifas-vigentes"].
 * Todos los consumidores (smart fields + form modals) comparten la misma
 * entrada de cache: no duplicar otra key.
 *
 * El shape de la respuesta varía por motor de liquidación:
 * - "porcentaje" (edificaciones, taludes, impacto-vial):
 *   { tarifas: [{ id, porcentaje_liquidacion }], especialidades_disponibles: [{ id, codigo, nombre }] }
 * - "m2" (habilitacion-urbana, mecanica-suelos):
 *   { tarifa_vigente: { datos: { id, costo_por_m2 } }, derecho_vigente: { datos: { id, derecho_minimo, derecho_maximo } } }
 * - "visitas" (inspeccion-obra):
 *   { tarifas: [{ id, costo_por_visita, categoria }] }
 *
 * Un único useApiQuery interno (useTarifasVigentesFetch) + 3 wrappers tipados
 * por motor, de modo que el fetch no se duplica por consumidor.
 */
import type { z } from "zod";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import {
  TarifasVigentesM2Schema,
  TarifasVigentesPorcentajeSchema,
  TarifasVigentesVisitasSchema,
} from "../schemas/tarifas-vigentes.schema";

// ── Fetch interno único ──────────────────────────────────────────────────────

type Envelope<T> = { success: boolean; data: T | null };

interface UseTarifasVigentesProps {
  /** Deshabilita la query (e.g. mientras no hay tipo disponible). */
  enabled?: boolean;
  /** Tiempo de revalidación. Default 5 min (catálogo, rara vez cambia). */
  staleTime?: number;
}

const STALE_TIME_CATALOGO = 1000 * 60 * 5;

function useTarifasVigentesFetch<TShape>({
  tipo,
  schema,
  fallback,
  enabled = true,
  staleTime = STALE_TIME_CATALOGO,
}: {
  tipo: string;
  schema: z.ZodType<TShape>;
  fallback: TShape;
  enabled?: boolean;
  staleTime?: number;
}) {
  return useApiQuery<Envelope<TShape>, TShape>({
    queryKey: ["liquidaciones", tipo, "tarifas-vigentes"],
    url: `/liquidaciones/${tipo}/tarifas/vigentes`,
    schema: apiResponseSchema(schema) as unknown as z.ZodType<Envelope<TShape>>,
    queryOptions: {
      enabled,
      staleTime,
      select: (envelope) => envelope.data ?? fallback,
    },
  });
}

// ── Wrappers por motor ───────────────────────────────────────────────────────

/** Motor porcentaje (PorcentajeObra: edificaciones, taludes, impacto-vial). */
export function useTarifasVigentesPorcentaje(
  tipo: string,
  props: UseTarifasVigentesProps = {},
) {
  return useTarifasVigentesFetch({
    tipo,
    schema: TarifasVigentesPorcentajeSchema,
    fallback: { tarifas: [], especialidades_disponibles: [] },
    ...props,
  });
}

/** Motor m2 (Habilitación Urbana, Mecánica de Suelos). */
export function useTarifasVigentesM2(
  tipo: "habilitacion-urbana" | "mecanica-suelos",
  props: UseTarifasVigentesProps = {},
) {
  return useTarifasVigentesFetch({
    tipo,
    schema: TarifasVigentesM2Schema,
    fallback: { tarifa_vigente: null, derecho_vigente: null },
    ...props,
  });
}

/** Motor visitas (Inspección de Obra). */
export function useTarifasVigentesVisitas(
  tipo: string = "inspeccion-obra",
  props: UseTarifasVigentesProps = {},
) {
  return useTarifasVigentesFetch({
    tipo,
    schema: TarifasVigentesVisitasSchema,
    fallback: { tarifas: [] },
    ...props,
  });
}
