import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

export const EspecialidadBasicaInspectorSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});
export type EspecialidadBasicaInspector = z.infer<
  typeof EspecialidadBasicaInspectorSchema
>;

/** Inspector vigente/elegible — GET /liquidaciones/inspectores/seleccionables */
export const InspectorVigenteSchema = z.object({
  id: z.string(),
  nombre_completo: z.string(),
  cip: z.string(),
  especialidad: EspecialidadBasicaInspectorSchema,
  tipo_liquidacion: z.string(),
  categoria: z.string().nullable(),
  numero_registro: z.string(),
  vigencia: z.string().nullable(),
});
export type InspectorVigenteData = z.infer<typeof InspectorVigenteSchema>;
export type InspectorVigente = InspectorVigenteData;

/** Envelope — GET /liquidaciones/inspectores/seleccionables */
export const InspectoresVigentesResponseSchema = apiResponseSchema(
  z.object({
    inspectores: z.array(InspectorVigenteSchema),
  }),
);
export type InspectoresVigentesResponse = z.infer<
  typeof InspectoresVigentesResponseSchema
>;
