/**
 * Servicio para consulta externa SUNAT/RENIEC.
 */
import api from "@/lib/api";
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";
import type { InstitucionSunatResponse, PersonaReniecResponse } from "../types/entidad";

// ── Schemas ─────────────────────────────────────────────────────────────────────

export const institucionSunatResponseSchema = apiResponseSchema(
  z.object({
    ruc: z.string(),
    razon_social: z.string(),
    nombre_comercial: z.string().nullable(),
    estado: z.string(),
    tipo_contribuyente: z.string().nullable(),
    direccion: z.string().nullable(),
    departamento: z.string().nullable(),
    provincia: z.string().nullable(),
    distrito: z.string().nullable(),
  })
);

export const personaReniecResponseSchema = apiResponseSchema(
  z.object({
    dni: z.string(),
    nombres: z.string(),
    apellidos: z.string(),
    nombre_completo: z.string(),
    genero: z.string().nullable(),
    fecha_nacimiento: z.string().nullable(),
    direccion: z.string().nullable(),
    ubigeo: z.string().nullable(),
  })
);

export type InstitucionSunatApiResponse = z.infer<typeof institucionSunatResponseSchema>;
export type PersonaReniecApiResponse = z.infer<typeof personaReniecResponseSchema>;

// ── Service Functions ───────────────────────────────────────────────────────────

export async function consultarSunat(
  ruc: string
): Promise<InstitucionSunatResponse | null> {
  const response = await api.get(`/entidades/consulta-sunat/${ruc}`);
  const parsed = institucionSunatResponseSchema.parse(response.data);
  return parsed.data as InstitucionSunatResponse | null;
}

export async function consultarReniec(
  dni: string
): Promise<PersonaReniecResponse | null> {
  const response = await api.get(`/entidades/consulta-reniec/${dni}`);
  const parsed = personaReniecResponseSchema.parse(response.data);
  return parsed.data as PersonaReniecResponse | null;
}
