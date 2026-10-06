/**
 * Tipos para Delegados — API contracts (nueva estructura).
 * GET /delegados/ devuelve por item:
 *   id, perfil_ingeniero { id, cip, dni, nombres, apellido_paterno, apellido_materno,
 *     especialidad { id, codigo, nombre }, capitulo { id, registro_id, abreviacion, nombre } },
 *   municipalidades [{ id, municipalidad { id, codigo, nombre }, tipo, categoria, periodo_inicio, periodo_fin, es_vigente }],
 *   estado: "vigente" | "sin_vigencia" | "sin_asignaciones"
 */

import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

// ── Perfil Ingeniero ─────────────────────────────────────────────────────────

export const especialidadSchema = z.object({
  id: z.string(),
  codigo: z.string().nullish(),
  nombre: z.string().nullish(),
});
export type Especialidad = z.infer<typeof especialidadSchema>;

export const capituloSchema = z.object({
  id: z.string(),
  registro_id: z.string().nullish(),
  abreviacion: z.string().nullish(),
  nombre: z.string().nullish(),
});
export type Capitulo = z.infer<typeof capituloSchema>;

export const perfilIngenieroSchema = z.object({
  id: z.string(),
  cip: z.string(),
  dni: z.string().nullish(),
  nombres: z.string().nullish(),
  apellido_paterno: z.string().nullish(),
  apellido_materno: z.string().nullish(),
  nombre_completo: z.string(),
  correo_personal: z.string().nullish(),
  correo_institucional: z.string().nullish(),
  especialidad: especialidadSchema.nullish(),
  capitulo: capituloSchema.nullish(),
});
export type PerfilIngenieroOut = z.infer<typeof perfilIngenieroSchema>;

// ── Municipalidad asignada ───────────────────────────────────────────────────

export const municipalidadAsignadaSchema = z.object({
  id: z.string(),
  municipalidad: z
    .object({
      id: z.string(),
      codigo: z.string().nullish(),
      nombre: z.string(),
    })
    .nullish(),
  tipo: z.string().nullish(),
  categoria: z.string().nullish(),
  periodo_inicio: z.string().nullish(),
  periodo_fin: z.string().nullish(),
  es_vigente: z.boolean().optional(),
});
export type MunicipalidadAsignada = z.infer<typeof municipalidadAsignadaSchema>;

// ── Delegado ─────────────────────────────────────────────────────────────────

export const delegadoSchema = z.object({
  id: z.string(),
  perfil_ingeniero: perfilIngenieroSchema,
  municipalidades: z.array(municipalidadAsignadaSchema).optional(),
  estado: z.string().nullish(),
});
export type DelegadoOut = z.infer<typeof delegadoSchema>;

// ── List Response ────────────────────────────────────────────────────────────

export const delegadosListPayloadSchema = z.object({
  items: z.array(delegadoSchema),
  total: z.coerce.number(),
  page: z.coerce.number(),
  page_size: z.coerce.number(),
  total_pages: z.coerce.number(),
});
export type DelegadoListOut = z.infer<typeof delegadosListPayloadSchema>;

export const delegadosListResponseSchema = apiResponseSchema(
  delegadosListPayloadSchema,
);

export type DelegadosListResponse = z.infer<typeof delegadosListPayloadSchema>;

// ── Filtros ──────────────────────────────────────────────────────────────────

export const delegadoEstadoSchema = z.enum([
  "vigente",
  "sin_vigencia",
  "sin_asignaciones",
]);
export type DelegadoEstado = z.infer<typeof delegadoEstadoSchema>;

export interface DelegadoFiltros {
  cip?: string;
  municipalidad_id?: string;
  capitulo_id?: string;
  especialidad_id?: string;
  estado?: DelegadoEstado;
}
