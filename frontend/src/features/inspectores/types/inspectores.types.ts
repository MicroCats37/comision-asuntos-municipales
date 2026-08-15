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

export type {
  EspecialidadBasicaInspector,
  InspectorVigente,
  InspectorVigenteData,
} from "../schemas/inspector-vigente.schema";

// ── Zod Schemas ──────────────────────────────────────────────────────────────

const perfilIngenieroSchema = z.object({
  id: z.string(),
  cip: z.string(),
  dni: z.string(),
  nombres: z.string().nullish(),
  apellido_paterno: z.string().nullish(),
  apellido_materno: z.string().nullish(),
  nombre_completo: z.string(),
  correo_personal: z.string().nullish(),
  correo_institucional: z.string().nullish(),
});

const inspectorSchema = z.object({
  id: z.string(),
  tipo_liquidacion: z.string().nullish(),
  numero_registro: z.string().nullish(),
  telefono: z.string().nullish(),
  email: z.string().nullish(),
  perfil_ingeniero: perfilIngenieroSchema,
});

export const inspectoresListPayloadSchema = z.object({
  items: z.array(inspectorSchema),
  total: z.coerce.number(),
  page: z.coerce.number(),
  page_size: z.coerce.number(),
  total_pages: z.coerce.number(),
});

export type InspectorListItem = z.infer<typeof inspectorSchema>;

export const inspectoresListResponseSchema = apiResponseSchema(
  inspectoresListPayloadSchema,
);

export type InspectoresListResponse = z.infer<
  typeof inspectoresListPayloadSchema
>;
