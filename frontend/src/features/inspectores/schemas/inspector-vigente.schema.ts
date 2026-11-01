import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

export const EspecialidadBasicaInspectorSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});
export type EspecialidadBasicaInspector = z.infer<
  typeof EspecialidadBasicaInspectorSchema
>;

/** Operatividad de inspector para el selector Legacy IO. */
export const InspectorOperacionSchema = z.object({
  id: z.string(),
  nombre_completo: z.string(),
  cip: z.string(),
  especialidad: EspecialidadBasicaInspectorSchema,
  tipo_liquidacion: z.string(),
  categoria: z.string().nullable(),
  numero_registro: z.string(),
  vigencia: z.string().nullable(),
  periodo_inicio: z.string().nullable(),
  periodo_fin: z.string().nullable(),
  es_vigente: z.boolean(),
  inspector_operacion_id: z.string(),
});
export type InspectorOperacionData = z.infer<typeof InspectorOperacionSchema>;
export type InspectorOperacion = InspectorOperacionData;

// Kept for existing IO selector consumers; its response now also includes
// the explicit operation period and current-status fields above.
export const InspectorVigenteSchema = InspectorOperacionSchema;
export type InspectorVigenteData = InspectorOperacionData;
export type InspectorVigente = InspectorOperacion;

/** Envelope del selector Legacy IO. */
export const InspectorOperatividadesResponseSchema = apiResponseSchema(
  z.object({
    inspectores: z.array(InspectorOperacionSchema),
  }),
);
export type InspectorOperatividadesResponse = z.infer<
  typeof InspectorOperatividadesResponseSchema
>;

export const InspectoresVigentesResponseSchema =
  InspectorOperatividadesResponseSchema;
export type InspectoresVigentesResponse = InspectorOperatividadesResponse;
