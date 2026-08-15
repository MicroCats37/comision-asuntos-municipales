import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

/** Entidad data payload — GET /entidades/buscar */
export const EntidadDataPayloadSchema = z.object({
  id: z.string(),
  tipo_documento: z.string(),
  numero_documento: z.string(),
  razon_social: z.string().nullable(),
  nombres: z.string().nullable(),
  apellidos: z.string().nullable(),
  nombre_completo: z.string(),
  direccion: z.string().nullable(),
  distrito_id: z.string().nullable(),
  activo: z.boolean(),
});
export type EntidadDataPayload = z.infer<typeof EntidadDataPayloadSchema>;

/** Entidad upsert response (incluye 'creado'). */
export const EntidadUpsertPayloadSchema = EntidadDataPayloadSchema.extend({
  creado: z.boolean(),
});
export type EntidadUpsertPayload = z.infer<typeof EntidadUpsertPayloadSchema>;

export const EntidadResponseSchema = apiResponseSchema(
  EntidadUpsertPayloadSchema,
);
export const EntidadBuscarResponseSchema = apiResponseSchema(
  EntidadDataPayloadSchema,
);
