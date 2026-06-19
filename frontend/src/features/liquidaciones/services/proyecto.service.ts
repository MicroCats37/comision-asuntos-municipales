/**
 * Servicio para proyectos de liquidaciones.
 */
import api from "@/lib/api";
import { z } from "zod";
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
const proyectoPayloadSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  denominacion: z.string(),
  direccion: z.string().nullable(),
  distrito: z.string().nullable(),  // Nombre del distrito (para display)
  distrito_id: z.string().nullable(), // ID del distrito (para envío)
  entidad: entidadSimpleSchema.nullable(),
});

/** Full envelope schema using shared helper */
export const proyectoResponseSchema = apiResponseSchema(proyectoPayloadSchema);

export type ProyectoResponse = z.infer<typeof proyectoResponseSchema>;

const proyectoInputSchema = z.object({
  denominacion: z.string().min(1),
  direccion: z.string().optional(),
  distrito_id: z.string().optional(),
  entidad_id: z.string().optional(),
});

export type ProyectoInput = z.infer<typeof proyectoInputSchema>;

// ── Service Functions ───────────────────────────────────────────────────────

export async function crearProyecto(data: ProyectoInput): Promise<ProyectoResponse> {
  const response = await api.post("/proyectos/", data);
  return proyectoResponseSchema.parse(response.data);
}

export async function buscarProyecto(publicId: string): Promise<ProyectoResponse> {
  const response = await api.get(`/proyectos/buscar/${publicId}`);
  return proyectoResponseSchema.parse(response.data);
}
