/**
 * Zod schemas para Proyectos.
 *
 * Matches backend schemas from:
 * backend/modules/liquidaciones/presentation/schemas/proyecto_schemas.py
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

// ── Inner Schemas (data fields only) ────────────────────────────────────────

export const entidadWithNumeroDocumentoSchema = z.object({
  id: z.string().uuid().nullable().optional(),
  tipo_documento: z.string().nullable().optional(),
  numero_documento: z.string().nullable().optional(),
  nombre: z.string().nullable().optional(),
});

export const edificacionListItemSchema = z.object({
  id: z.string().uuid(),
  public_id: z.string(),
  numero_revision: z.number(),
  estado: z.string(),
  fecha_registro: z.string(),
  total: z.number(),
  tipo_tramite: z.string(),
  tramite_accion: z.string(),
});

export const liquidacionesInlineSchema = z.object({
  edificaciones: z.array(edificacionListItemSchema).default([]),
});

export const proyectoListItemSchema = z.object({
  id: z.string().uuid(),
  public_id: z.string(),
  denominacion: z.string(),
  direccion: z.string().nullable().optional(),
  distrito: z.string().nullable().optional(),
  entidad: entidadWithNumeroDocumentoSchema.nullable().optional(),
  liquidaciones: liquidacionesInlineSchema,
});

// ── Paginated Response Schema ────────────────────────────────────────────────

const paginatedProyectosPayloadSchema = z.object({
  items: z.array(proyectoListItemSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});

/** Wrapper schema for paginated proyectos list response */
export const paginatedProyectosResponseSchema = apiResponseSchema(
  paginatedProyectosPayloadSchema,
);
