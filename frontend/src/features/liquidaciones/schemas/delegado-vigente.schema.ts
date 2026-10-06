import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";
import { EspecialidadBasicaDelegadoSchema } from "./liquidacion-base.schema";

export { EspecialidadBasicaDelegadoSchema } from "./liquidacion-base.schema";

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
