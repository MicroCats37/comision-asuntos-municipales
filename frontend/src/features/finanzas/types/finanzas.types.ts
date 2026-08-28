/**
 * Tipos para Finanzas — API contracts.
 * Backend endpoints:
 * - GET /liquidaciones/{tipo}/tarifas/historicas
 * - GET /liquidaciones/derechos/historicos
 */

import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

// ── Tipo Liquidación (tipo paths) ─────────────────────────────────────────────

/**
 * Tipos de liquidacion que aparecen en el path de tarifas historicas.
 * Coincide con las rutas REALES del backend:
 * edificaciones, habilitacion-urbana, mecanica-suelos, impacto-vial, taludes, inspeccion-obra
 */
export const tipoTarifaSchema = z.enum([
  "edificaciones",
  "habilitacion-urbana",
  "mecanica-suelos",
  "impacto-vial",
  "taludes",
  "inspeccion-obra",
]);
export type TipoTarifa = z.infer<typeof tipoTarifaSchema>;

// ── Tarifas Porcentaje ────────────────────────────────────────────────────────

export const tarifaPorcentajeSchema = z.object({
  id: z.string(),
  especialidad_id: z.string(),
  especialidad_nombre: z.string(),
  porcentaje_liquidacion: z.coerce.number(),
});
export type TarifaPorcentaje = z.infer<typeof tarifaPorcentajeSchema>;

// ── Tarifa M2 ────────────────────────────────────────────────────────────────

export const tarifaM2Schema = z.object({
  id: z.string(),
  costo_por_m2: z.coerce.number(),
});
export type TarifaM2 = z.infer<typeof tarifaM2Schema>;

// ── Tarifas Visitas ───────────────────────────────────────────────────────────

export const tarifaVisitaSchema = z.object({
  id: z.string(),
  categoria: z.string(),
  porcentaje_uit: z.coerce.number(),
});
export type TarifaVisita = z.infer<typeof tarifaVisitaSchema>;

// ── Tarifa Historica Periodo ──────────────────────────────────────────────────

/**
 * Matches TarifaHistoricaPeriodoSchema from backend.
 * Representa un periodo tarifario con sus tarifas asociadas.
 */
export const tarifaHistoricaPeriodoSchema = z.object({
  id: z.string(),
  tipo_liquidacion: z.string(),
  periodo_inicio: z.string(), // date ISO
  periodo_fin: z.string().nullable(), // date ISO | null
  tarifas_porcentaje: z.array(tarifaPorcentajeSchema),
  tarifa_m2: tarifaM2Schema.nullable().optional(),
  tarifas_visitas: z.array(tarifaVisitaSchema),
});
export type TarifaHistoricaPeriodo = z.infer<
  typeof tarifaHistoricaPeriodoSchema
>;

// ── Derechos Historicos ───────────────────────────────────────────────────────

/**
 * Matches DerechoHistoricoSchema from backend.
 */
export const derechoHistoricoSchema = z.object({
  id: z.string(),
  derecho_minimo: z.coerce.number().nullable().optional(),
  derecho_maximo: z.coerce.number().nullable().optional(),
  porcentaje_minimo_uit: z.coerce.number().nullable().optional(),
  periodo_inicio: z.string(), // date ISO
  periodo_fin: z.string().nullable(), // date ISO | null
});
export type DerechoHistorico = z.infer<typeof derechoHistoricoSchema>;

// ── Response Wrappers ────────────────────────────────────────────────────────

// Paginación para tarifas históricas (usa page/page_size como query params)
export const paginatedTarifaHistoricaPayloadSchema = z.object({
  items: z.array(tarifaHistoricaPeriodoSchema),
  total: z.coerce.number(),
  page: z.coerce.number(),
  page_size: z.coerce.number(),
  total_pages: z.coerce.number(),
});

export const paginatedTarifaHistoricaResponseSchema = apiResponseSchema(
  paginatedTarifaHistoricaPayloadSchema,
);

// Derechos históricos (sin paginación)
export const derechosHistoricosPayloadSchema = z.object({
  derechos: z.array(derechoHistoricoSchema),
});

export const derechosHistoricosResponseSchema = apiResponseSchema(
  derechosHistoricosPayloadSchema,
);

// ── UI State Types ────────────────────────────────────────────────────────────

export interface TarifasFiltros {
  tipo?: TipoTarifa;
  fechaDesde?: string; // YYYY-MM-DD
  fechaHasta?: string; // YYYY-MM-DD
}

export interface UseTarifasHistoricasProps {
  tipo: TipoTarifa;
  fechaDesde?: string; // YYYY-MM-DD
  fechaHasta?: string; // YYYY-MM-DD
  page?: number;
  pageSize?: number;
}

export interface UseTarifasHistoricasReturn {
  items: TarifaHistoricaPeriodo[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
}
