/**
 * Servicio para proyectos de liquidaciones.
 */

import { z } from "zod";
import api from "@/lib/api";
import { apiResponseSchema } from "@/types/api.types";

// ── Schema ─────────────────────────────────────────────────────────────────

/** Nested simple data schemas - matches backend ProyectoSerializer */
export const entidadSimpleSchema = z.object({
  id: z.string().nullable(),
  tipo: z.string().nullable(),
  nombre: z.string().nullable(),
});

export type EntidadSimple = z.infer<typeof entidadSimpleSchema>;

/** Data payload schema */
export const proyectoPayloadSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  denominacion: z.string(),
  direccion: z.string().nullable(),
  distrito: z.string().nullable(), // Nombre del distrito (para display)
  distrito_id: z.string().nullable(), // ID del distrito (para envío)
  entidad: entidadSimpleSchema.nullable(),
});

/** Full envelope schema using shared helper */
export const proyectoResponseSchema = apiResponseSchema(proyectoPayloadSchema);

export type ProyectoResponse = z.infer<typeof proyectoResponseSchema>;

/**
 * Normalizes a raw API response to extract the proyecto object.
 * Handles both:
 *   - Wrapped:  { success, data: {...proyecto}, error }
 *   - Direct:    {...proyecto} (no envelope)
 *
 * Returns null if no valid proyecto can be extracted.
 */
export function normalizeProyectoResponse(
  raw: unknown,
): z.infer<typeof proyectoPayloadSchema> | null {
  if (!raw || typeof raw !== "object") return null;

  // Case 1: Full envelope { success, data: {...}, error? }
  if (
    "success" in (raw as Record<string, unknown>) &&
    "data" in (raw as Record<string, unknown>)
  ) {
    const envelope = raw as {
      success: boolean;
      data: unknown;
      error?: unknown;
    };
    if (
      envelope.success &&
      envelope.data &&
      typeof envelope.data === "object"
    ) {
      const result = proyectoPayloadSchema.safeParse(envelope.data);
      if (result.success) return result.data;
    }
  }

  // Case 2: Direct project object (no envelope)
  const direct = proyectoPayloadSchema.safeParse(raw);
  if (direct.success) return direct.data;

  return null;
}

const proyectoInputSchema = z.object({
  denominacion: z.string().min(1),
  direccion: z.string().optional(),
  distrito_id: z.string().optional(),
  entidad_id: z.string().optional(),
});

export type ProyectoInput = z.infer<typeof proyectoInputSchema>;

// ── Service Functions ───────────────────────────────────────────────────────

export async function crearProyecto(
  data: ProyectoInput,
): Promise<ProyectoResponse> {
  const response = await api.post("/proyectos/", data);
  return proyectoResponseSchema.parse(response.data);
}

export async function buscarProyecto(
  publicId: string,
): Promise<ProyectoResponse> {
  const response = await api.get(`/proyectos/buscar/${publicId}`);
  return proyectoResponseSchema.parse(response.data);
}

// ── List Projects (for filter dropdown) ───────────────────────────────────

/** Schema for paginated proyectos list response */
const proyectoListPayloadSchema = z.object({
  items: z.array(
    z.object({
      id: z.string(),
      public_id: z.string(),
      denominacion: z.string(),
      direccion: z.string().nullable(),
      distrito: z.string().nullable(),
      entidad: z
        .object({
          id: z.string().nullable(),
          tipo_documento: z.string().nullable(),
          numero_documento: z.string().nullable(),
          nombre: z.string().nullable(),
        })
        .nullable(),
    }),
  ),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});

export const proyectoListResponseSchema = apiResponseSchema(proyectoListPayloadSchema);

export type ProyectoListItem = {
  id: string;
  public_id: string;
  denominacion: string;
  direccion: string | null;
  distrito: string | null;
  entidad: {
    id: string | null;
    tipo_documento: string | null;
    numero_documento: string | null;
    nombre: string | null;
  } | null;
};

export type PaginatedProyectos = {
  items: ProyectoListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export async function listProyectos(
  page: number = 1,
  pageSize: number = 100,
): Promise<PaginatedProyectos> {
  const response = await api.get("/proyectos/", {
    params: { page, page_size: pageSize },
  });
  const parsed = proyectoListResponseSchema.parse(response.data);
  return parsed.data ?? {
    items: [],
    total: 0,
    page: 1,
    page_size: pageSize,
    total_pages: 1,
  };
}
