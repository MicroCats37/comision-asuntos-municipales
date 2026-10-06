/**
 * Zod schema para RELACIONADA de Edificaciones.
 *
 * Misma forma que nueva-revision (singular `liquidacion_previa_id`): se reusa
 * el schema de nueva-revision para evitar duplicación. La única diferencia
 * operativa es el endpoint POST /liquidaciones/edificaciones/relacion y el
 * badge "RELACIONADA" en el header del form.
 *
 * Si en el futuro las reglas de validación divergen, este archivo es el lugar
 * para especializar sin tocar `liquidacion-nueva-revision-form.schema.ts`.
 */
export {
  type NuevaRevisionEdificacionesFormData as RelacionEdificacionesFormData,
  nuevaRevisionEdificacionesFormSchema as relacionEdificacionesFormSchema,
} from "./liquidacion-nueva-revision-form.schema";
