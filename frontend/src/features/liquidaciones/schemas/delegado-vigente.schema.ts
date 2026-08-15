import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

export const EspecialidadBasicaDelegadoSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});
export type EspecialidadBasicaDelegado = z.infer<
  typeof EspecialidadBasicaDelegadoSchema
>;

/** Delegado vigente — GET /liquidaciones/delegados/vigentes */
export const DelegadoVigenteSchema = z.object({
  id: z.string(),
  nombre_completo: z.string(),
  cip: z.string(),
  especialidad: EspecialidadBasicaDelegadoSchema,
  tipo: z.string(),
});
export type DelegadoVigenteData = z.infer<typeof DelegadoVigenteSchema>;
export type DelegadoVigente = DelegadoVigenteData;

export const DelegadosVigentesResponseSchema = apiResponseSchema(
  z.object({
    delegados: z.array(DelegadoVigenteSchema),
  }),
);
export type DelegadosVigentesResponse = z.infer<
  typeof DelegadosVigentesResponseSchema
>;
