/**
 * Servicio para consultar un ingeniero habilitado por CIP.
 *
 * Endpoint: GET /ingenieros/habilitados/{cip}
 * Respuesta minimal: { cip, nombres, apellidos, habilitado, capitulo }
 *
 * Sigue el contrato estándar del frontend (igual que consulta-externa.service.ts):
 * devuelve `data | null` y propaga el error (Axios) para que el error-handler
 * central (handleApiError/getErrorMessage) lo normalice — red caída, 404, 503, etc.
 */

import { z } from "zod";
import api from "@/lib/api";
import { apiResponseSchema } from "@/types/api.types";

// ── Schema de respuesta ────────────────────────────────────────────────────────

export const ingenieroHabilitadoSchema = z.object({
  cip: z.string(),
  nombres: z.string(),
  apellidos: z.string(),
  habilitado: z.boolean(),
  capitulo: z.string().nullish(),
});

export const ingenieroHabilitadoResponseSchema = apiResponseSchema(
  ingenieroHabilitadoSchema,
);

export type IngenieroHabilitado = z.infer<typeof ingenieroHabilitadoSchema>;

// ── Service Function ───────────────────────────────────────────────────────────

/**
 * Consulta un ingeniero habilitado por su número de CIP (6 dígitos).
 * Devuelve los datos o null; ante error HTTP/red lanza para el error-handler.
 */
export async function consultarIngeniero(
  cip: string,
): Promise<IngenieroHabilitado | null> {
  const response = await api.get(`/ingenieros/habilitados/${cip}`);
  const parsed = ingenieroHabilitadoResponseSchema.parse(response.data);
  return parsed.data;
}
