/**
 * Servicio para consulta externa SUNAT/RENIEC unificado.
 *
 * Endpoint único: GET /entidades/consulta/{documento}
 * - 8 dígitos → DNI (RENIEC)
 * - 11 dígitos → RUC (SUNAT)
 *
 * Respuesta minimal: { tipo_documento, numero_documento, razon_social }
 */

import { z } from "zod";
import api from "@/lib/api";
import { apiResponseSchema } from "@/types/api.types";

// ── Unified Schema ─────────────────────────────────────────────────────────────

export const documentoConsultaResponseSchema = apiResponseSchema(
  z.object({
    tipo_documento: z.string(),
    numero_documento: z.string(),
    razon_social: z.string(),
  }),
);

export type DocumentoConsultaResponse = z.infer<
  typeof documentoConsultaResponseSchema
>;

// ── Service Functions ───────────────────────────────────────────────────────────

/**
 * Consulta datos de documento por número (DNI o RUC).
 * Auto-detecta: 8 dígitos → DNI, 11 dígitos → RUC.
 */
export async function consultarDocumento(
  documento: string,
): Promise<DocumentoConsultaResponse["data"] | null> {
  const response = await api.get(`/entidades/consulta/${documento}`);
  const parsed = documentoConsultaResponseSchema.parse(response.data);
  return parsed.data;
}
