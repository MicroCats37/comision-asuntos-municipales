/**
 * Tipos para Delegados — API contracts.
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

// ── Delegado ─────────────────────────────────────────────────────────────────

export interface DelegadoOut {
  id: string;
  perfil_ingeniero: PerfilIngenieroOut;
}

// ── List Response ────────────────────────────────────────────────────────────

export interface DelegadoListOut {
  items: DelegadoOut[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

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

const delegadoSchema = z.object({
  id: z.string().uuid(),
  perfil_ingeniero: perfilIngenieroSchema,
});

export const delegadosListPayloadSchema = z.object({
  items: z.array(delegadoSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});

export const delegadosListResponseSchema = apiResponseSchema(delegadosListPayloadSchema);

export type DelegadosListResponse = z.infer<typeof delegadosListPayloadSchema>;
