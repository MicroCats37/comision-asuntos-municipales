/**
 * Tipos para Inspectores — API contracts.
 */

import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

// ── Perfil Ingeniero ─────────────────────────────────────────────────────────

export interface PerfilIngenieroOut {
  id: string;
  cip: string;
  dni: string;
  nombres: string;
  apellido_paterno: string;
  apellido_materno: string;
  nombre_completo: string;
  correo_personal?: string;
  correo_institucional?: string;
}

// ── Inspector ─────────────────────────────────────────────────────────────────

export interface InspectorOut {
  id: string;
  tipo_liquidacion: string;
  numero_registro: string;
  telefono?: string;
  email?: string;
  perfil_ingeniero: PerfilIngenieroOut;
}

// ── List Response ────────────────────────────────────────────────────────────

export interface InspectorListOut {
  items: InspectorOut[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Inspector Vigente (for IO liquidaciones) ─────────────────────────────────

const especialidadBasicaInspectorSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

const inspectorVigentePayloadSchema = z.object({
  id: z.string(),
  nombre_completo: z.string(),
  cip: z.string(),
  especialidad: especialidadBasicaInspectorSchema,
  tipo_liquidacion: z.string(),
  categoria: z.number().nullable(),
  numero_registro: z.string(),
  vigencia: z.string(),
});

export type InspectorVigente = z.infer<typeof inspectorVigentePayloadSchema>;

// ── Zod Schemas ──────────────────────────────────────────────────────────────

const perfilIngenieroSchema = z.object({
  id: z.string().uuid(),
  cip: z.string(),
  dni: z.string(),
  nombres: z.string(),
  apellido_paterno: z.string(),
  apellido_materno: z.string(),
  nombre_completo: z.string(),
  correo_personal: z.string().optional(),
  correo_institucional: z.string().optional(),
});

const inspectorSchema = z.object({
  id: z.string().uuid(),
  tipo_liquidacion: z.string(),
  numero_registro: z.string(),
  telefono: z.string().optional(),
  email: z.string().optional(),
  perfil_ingeniero: perfilIngenieroSchema,
});

export const inspectoresListPayloadSchema = z.object({
  items: z.array(inspectorSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});

export const inspectoresListResponseSchema = apiResponseSchema(inspectoresListPayloadSchema);

export type InspectoresListResponse = z.infer<typeof inspectoresListPayloadSchema>;
